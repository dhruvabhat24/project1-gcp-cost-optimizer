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
from typing import Any, Dict, List


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
        """Scale a Kubernetes deployment.

        Args:
            namespace: Kubernetes namespace.
            deployment: Deployment name.
            replicas: Desired replica count.

        Returns:
            bool: True when the action succeeds or is simulated.

        Raises:
            ValueError: If replicas is invalid.
        """
        if replicas < 1:
            raise ValueError(
                "Replica count must be at least 1"
            )

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
        """Patch a deployment's container resource requests.

        Args:
            namespace: Kubernetes namespace.
            deployment: Deployment name.
            cpu: New CPU request.
            memory: New memory request.

        Returns:
            bool: True when successful or simulated.
        """
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

    def execute_recommendation(
    self,
    recommendation: Dict[str, Any],
    ) -> bool:
        """Execute a recommendation safely.

        Args:
            recommendation: Optimization recommendation.

        Returns:
            bool: True when successfully processed.
        """
        try:
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

            cpu = recommendation.get(
                "actual_cpu_cores",
                0.0,
            )

            memory = recommendation.get(
                "actual_memory_gb",
                0.0,
            )

            cpu_value = f"{max(float(cpu) * 1.5, 0.01):.3f}"

            memory_value = f"{max(float(memory) * 1.5, 0.01):.3f}Gi"

            return self.update_resource_limits(
                namespace=namespace,
                deployment=pod_name,
                cpu=cpu_value,
                memory=memory_value,
            )

        except (TypeError, ValueError) as exc:
            self.logger.error(
                "Invalid recommendation data for %s/%s: %s",
                namespace,
                pod_name,
                exc,
            )
            return False

        except Exception:
            self.logger.exception(
                "Unexpected error while executing recommendation for %s/%s",
                namespace,
                pod_name,
            )
            return False

    def log_action(
        self,
        namespace: str,
        resource: str,
        old_value: Any,
        new_value: Any,
        action: str,
    ) -> None:
        """Record an executed or simulated action.

        Args:
            namespace: Kubernetes namespace.
            resource: Kubernetes resource.
            old_value: Previous resource value.
            new_value: New value.
            action: Action type.
        """
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
        """Save the weekly report.

        Args:
            report_text: Human-readable report.
            reports_dir: Destination directory.

        Returns:
            Path: Written report path.
        """
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

        return path

    def generate_report_text(
        self,
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """Generate a concise savings summary.

        Args:
            recommendations: Optimization recommendations.

        Returns:
            str: Human-readable summary.
        """
        total = sum(
            item.get(
                "estimated_monthly_savings_inr",
                0,
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
                f"- {item['namespace']}/{item['pod_name']}: "
                f"{item['suggested_action']} | "
                f"₹{item['estimated_monthly_savings_inr']:,.2f}/month"
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
        """Execute or simulate a kubectl command.

        Args:
            command: kubectl command arguments.
            namespace: Kubernetes namespace.
            resource: Resource name.
            action: Action identifier.
            new_value: New resource value.

        Returns:
            bool: True when successful.
        """
        command_string = " ".join(command)

        self.logger.info(
            "kubectl action: %s",
            command_string,
        )

        if self.dry_run:
            print(f"[DRY-RUN] Would execute: {command_string}")

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

            return True

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            OSError,
        ) as exc:
            self.logger.exception(
                "kubectl execution failed: %s",
                exc,
            )

            return False