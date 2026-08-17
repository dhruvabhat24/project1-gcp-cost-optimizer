"""
Safe execution layer for Kubernetes optimization recommendations.

The default behaviour is dry-run. This prevents accidental changes to
developer clusters while still demonstrating the commands that would
be executed.
"""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ActionExecutor:
    """Execute or simulate Kubernetes optimization actions."""

    PROTECTED_NAMESPACES = {
        "kube-system",
        "kube-public",
        "kube-node-lease",
    }

    def __init__(self, dry_run: bool = True) -> None:
        """Initialize the executor.

        Args:
            dry_run: If True, commands are displayed but not executed.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.dry_run = dry_run
        self.action_log: List[Dict[str, Any]] = []

    def auto_scale_pod(
        self,
        namespace: str,
        deployment: str,
        replicas: int,
    ) -> bool:
        """Scale a Kubernetes deployment."""
        if replicas < 1:
            raise ValueError("Replica count must be at least 1")

        if namespace in self.PROTECTED_NAMESPACES:
            self.logger.warning(
                "Refusing to scale protected namespace: %s",
                namespace,
            )
            return False

        command = [
            "kubectl",
            "scale",
            "deployment",
            deployment,
            f"--replicas={replicas}",
            "-n",
            namespace,
        ]

        return self._run_action(
            command=command,
            namespace=namespace,
            resource=deployment,
            action="scale",
            new_value=replicas,
        )

    def update_resource_limits(
        self,
        namespace: str,
        deployment: str,
        cpu: str,
        memory: str,
    ) -> bool:
        """Patch a deployment's CPU and memory resources."""
        if namespace in self.PROTECTED_NAMESPACES:
            self.logger.warning(
                "Refusing to modify protected namespace: %s",
                namespace,
            )
            return False

        patch = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": deployment,
                                "resources": {
                                    "requests": {
                                        "cpu": cpu,
                                        "memory": memory,
                                    },
                                    "limits": {
                                        "cpu": cpu,
                                        "memory": memory,
                                    },
                                },
                            }
                        ]
                    }
                }
            }
        }

        command = [
            "kubectl",
            "patch",
            "deployment",
            deployment,
            "-n",
            namespace,
            "--type=strategic",
            "-p",
            json.dumps(patch),
        ]

        return self._run_action(
            command=command,
            namespace=namespace,
            resource=deployment,
            action="right-size",
            new_value={
                "cpu": cpu,
                "memory": memory,
            },
        )

    def _resolve_deployment_name(
        self,
        namespace: str,
        pod_name: str,
    ) -> Optional[str]:
        """Resolve a Pod to its owning Deployment.

        Kubernetes ownership hierarchy:

            Pod -> ReplicaSet -> Deployment
        """
        if not pod_name:
            self.logger.warning(
                "Cannot resolve deployment because pod name is empty."
            )
            return None

        if namespace in self.PROTECTED_NAMESPACES:
            self.logger.warning(
                "Refusing to resolve resources in protected namespace: %s",
                namespace,
            )
            return None

        try:
            pod_result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pod",
                    pod_name,
                    "-n",
                    namespace,
                    "-o",
                    "jsonpath={.metadata.ownerReferences[0].name}",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            replicaset_name = pod_result.stdout.strip()

            if not replicaset_name:
                self.logger.warning(
                    "No ReplicaSet owner found for pod %s/%s",
                    namespace,
                    pod_name,
                )
                return None

            self.logger.info(
                "Resolved pod %s/%s -> ReplicaSet %s",
                namespace,
                pod_name,
                replicaset_name,
            )

            deployment_result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "replicaset",
                    replicaset_name,
                    "-n",
                    namespace,
                    "-o",
                    "jsonpath={.metadata.ownerReferences[0].name}",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            deployment_name = deployment_result.stdout.strip()

            if not deployment_name:
                self.logger.warning(
                    "No Deployment owner found for ReplicaSet %s/%s",
                    namespace,
                    replicaset_name,
                )
                return None

            self.logger.info(
                "Resolved ReplicaSet %s/%s -> Deployment %s",
                namespace,
                replicaset_name,
                deployment_name,
            )

            return deployment_name

        except subprocess.CalledProcessError as exc:
            self.logger.error(
                "kubectl failed while resolving deployment for "
                "pod %s/%s: %s",
                namespace,
                pod_name,
                exc,
            )
            return None

        except subprocess.TimeoutExpired as exc:
            self.logger.error(
                "Timeout while resolving deployment for pod %s/%s: %s",
                namespace,
                pod_name,
                exc,
            )
            return None

        except OSError as exc:
            self.logger.error(
                "Unable to execute kubectl while resolving pod %s/%s: %s",
                namespace,
                pod_name,
                exc,
            )
            return None

    def execute_recommendation(
        self,
        recommendation: Dict[str, Any],
    ) -> bool:
        """Execute a recommendation safely."""
        namespace = recommendation.get(
            "namespace",
            "default",
        )

        pod_name = recommendation.get(
            "pod_name",
            "",
        )

        if namespace in self.PROTECTED_NAMESPACES:
            self.logger.warning(
                "Skipping protected pod %s/%s",
                namespace,
                pod_name,
            )
            return False

        if not pod_name:
            self.logger.warning(
                "Skipping recommendation because pod name is missing."
            )
            return False

        cpu = recommendation.get(
            "actual_cpu_cores",
            0.0,
        )

        memory = recommendation.get(
            "actual_memory_gb",
            0.0,
        )

        try:
            cpu_value = f"{max(float(cpu) * 1.5, 0.01):.3f}"
            memory_value = (
                f"{max(float(memory) * 1.5, 0.01):.3f}Gi"
            )
        except (TypeError, ValueError) as exc:
            self.logger.error(
                "Invalid resource values for %s/%s: %s",
                namespace,
                pod_name,
                exc,
            )
            return False

        deployment = self._resolve_deployment_name(
            namespace=namespace,
            pod_name=pod_name,
        )

        if not deployment:
            self.logger.warning(
                "Skipping recommendation because deployment "
                "could not be resolved for pod %s/%s",
                namespace,
                pod_name,
            )
            return False

        self.logger.info(
            "Executing recommendation for %s/%s via deployment %s",
            namespace,
            pod_name,
            deployment,
        )

        return self.update_resource_limits(
            namespace=namespace,
            deployment=deployment,
            cpu=cpu_value,
            memory=memory_value,
        )

    def log_action(
        self,
        namespace: str,
        resource: str,
        old_value: Any,
        new_value: Any,
        action: str,
    ) -> None:
        """Record an executed or simulated action."""
        entry = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "namespace": namespace,
            "resource": resource,
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "dry_run": self.dry_run,
        }

        self.action_log.append(entry)

        self.logger.info(
            "AUDIT | %s",
            json.dumps(entry),
        )

    def send_weekly_report(
        self,
        report_text: str,
        reports_dir: Path,
    ) -> Path:
        """Save the weekly report and action audit."""
        reports_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = reports_dir / "weekly_report.txt"

        path.write_text(
            report_text,
            encoding="utf-8",
        )

        audit_path = reports_dir / "action_audit.json"

        audit_path.write_text(
            json.dumps(
                self.action_log,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.logger.info(
            "Weekly report written to %s",
            path,
        )

        self.logger.info(
            "Action audit written to %s",
            audit_path,
        )

        return path

    def generate_report_text(
        self,
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """Generate a concise savings summary."""
        total = sum(
            float(
                item.get(
                    "estimated_monthly_savings_inr",
                    0,
                )
            )
            for item in recommendations
        )

        lines = [
            "Kubernetes Cost Optimizer - Weekly Summary",
            "=" * 50,
            f"Recommendations: {len(recommendations)}",
            f"Estimated monthly savings: ₹{total:,.2f}",
            "",
        ]

        for item in recommendations:
            lines.append(
                f"- {item['namespace']}/"
                f"{item['pod_name']}: "
                f"{item['suggested_action']} | "
                f"₹{float(item['estimated_monthly_savings_inr']):,.2f}"
                f"/month"
            )

        return "\n".join(lines)

    def _run_action(
        self,
        command: List[str],
        namespace: str,
        resource: str,
        action: str,
        new_value: Any,
    ) -> bool:
        """Execute or simulate a kubectl command."""
        command_string = " ".join(command)

        self.logger.info(
            "kubectl action: %s",
            command_string,
        )

        if self.dry_run:
            print(
                f"[DRY-RUN] Would execute: {command_string}"
            )

            self.log_action(
                namespace=namespace,
                resource=resource,
                old_value="unknown",
                new_value=new_value,
                action=action,
            )

            return True

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.log_action(
                namespace=namespace,
                resource=resource,
                old_value="unknown",
                new_value=new_value,
                action=action,
            )

            self.logger.info(
                "kubectl succeeded: %s",
                result.stdout.strip(),
            )

            if result.stderr.strip():
                self.logger.debug(
                    "kubectl stderr: %s",
                    result.stderr.strip(),
                )

            return True

        except subprocess.CalledProcessError as exc:
            self.logger.error(
                "kubectl execution failed with exit code %s: %s",
                exc.returncode,
                exc.stderr.strip() if exc.stderr else str(exc),
            )
            return False

        except subprocess.TimeoutExpired as exc:
            self.logger.error(
                "kubectl command timed out: %s",
                exc,
            )
            return False

        except OSError as exc:
            self.logger.error(
                "Unable to execute kubectl: %s",
                exc,
            )
            return False