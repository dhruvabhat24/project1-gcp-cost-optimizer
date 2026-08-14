"""
Prometheus and Kubernetes metrics analysis module.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from kubernetes import client, config as kube_config
from kubernetes.config.config_exception import ConfigException

import config


class PrometheusMetricsAnalyzer:
    """Analyze Kubernetes resource usage against resource requests."""

    def __init__(self) -> None:
        """Initialize Prometheus and Kubernetes clients."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.prometheus_url: str = config.PROMETHEUS_URL
        self.k8s_api: Optional[client.CoreV1Api] = None
        self.prometheus_available: bool = False

    def connect_to_prometheus(self) -> bool:
        """Check connectivity to local Prometheus.

        Returns:
            bool: True when Prometheus is reachable.
        """
        try:
            response = requests.get(
                f"{self.prometheus_url}/-/ready",
                timeout=5,
            )

            self.prometheus_available = (
                response.status_code == 200
            )

            if self.prometheus_available:
                self.logger.info(
                    "Prometheus available at %s",
                    self.prometheus_url,
                )
            else:
                self.logger.warning(
                    "Prometheus returned HTTP %s",
                    response.status_code,
                )

            return self.prometheus_available

        except requests.RequestException as exc:
            self.prometheus_available = False

            self.logger.warning(
                "Prometheus unavailable: %s",
                exc,
            )

            return False

    def _connect_to_kubernetes(self) -> bool:
        """Connect to the local Kubernetes cluster.

        Returns:
            bool: True if Kubernetes API access succeeds.
        """
        try:
            try:
                kube_config.load_kube_config()
            except ConfigException:
                kube_config.load_incluster_config()

            self.k8s_api = client.CoreV1Api()

            self.logger.info(
                "Kubernetes API connection initialized"
            )

            return True

        except ConfigException as exc:
            self.logger.error(
                "Failed to load Kubernetes configuration: %s",
                exc,
            )
            self.k8s_api = None
            return False

        except Exception as exc:
            self.logger.exception(
                "Unexpected error while connecting to Kubernetes: %s",
                exc,
            )
            self.k8s_api = None
            return False

    def _query_prometheus(
        self,
        query: str,
    ) -> List[Dict[str, Any]]:
        """Execute an instant Prometheus query.

        Args:
            query: PromQL query.

        Returns:
            List[Dict[str, Any]]: Prometheus result vector.
        """
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=10,
            )

            response.raise_for_status()

            payload = response.json()

            if payload.get("status") != "success":
                raise RuntimeError(
                    payload.get("error", "Prometheus query failed")
                )

            return payload.get(
                "data",
                {},
            ).get(
                "result",
                [],
            )

        except Exception as exc:
            self.logger.warning(
                "Prometheus query failed: %s",
                exc,
            )

            return []

    def get_pod_resource_usage(self) -> Dict[str, Dict[str, float]]:
        """Retrieve CPU and memory usage for Kubernetes pods.

        Returns:
            Dict[str, Dict[str, float]]: Pod usage indexed by namespace/name.
        """
        if not self.prometheus_available:
            self.logger.info(
                "Using mock Prometheus usage data"
            )
            return self._mock_usage()

        cpu_query = (
            'sum by (namespace,pod) '
            '(rate(container_cpu_usage_seconds_total'
            '{container!="",container!="POD"}[5m]))'
        )

        memory_query = (
            'sum by (namespace,pod) '
            '(container_memory_working_set_bytes'
            '{container!="",container!="POD"})'
        )

        cpu_results = self._query_prometheus(cpu_query)
        memory_results = self._query_prometheus(memory_query)

        usage: Dict[str, Dict[str, float]] = {}

        for result in cpu_results:
            metric = result.get("metric", {})
            key = self._pod_key(metric)

            try:
                usage.setdefault(key, {})["cpu"] = float(
                    result["value"][1]
                )
            except (KeyError, ValueError, TypeError, IndexError):
                continue

        for result in memory_results:
            metric = result.get("metric", {})
            key = self._pod_key(metric)

            try:
                usage.setdefault(key, {})["memory"] = (
                    float(result["value"][1]) / 1024 / 1024 / 1024
                )
            except (KeyError, ValueError, TypeError, IndexError):
                continue

        if not usage:
            self.logger.warning(
                "Prometheus returned no usable pod metrics; "
                "falling back to mock usage"
            )
            return self._mock_usage()

        return usage

    def get_pod_resource_requests(
        self,
    ) -> Dict[str, Dict[str, float]]:
        """Retrieve Kubernetes resource requests.

        Returns:
            Dict[str, Dict[str, float]]: Requested CPU and memory.

        Raises:
            RuntimeError: If Kubernetes cannot be accessed and no mock
                data is available.
        """
        if not self.k8s_api and not self._connect_to_kubernetes():
            self.logger.warning(
                "Using mock Kubernetes resource requests"
            )
            return self._mock_requests()

        try:
            pods = self.k8s_api.list_pod_for_all_namespaces()

            requests_data: Dict[str, Dict[str, float]] = {}

            for pod in pods.items:
                namespace = pod.metadata.namespace or "default"
                name = pod.metadata.name

                cpu = 0.0
                memory = 0.0

                if not pod.spec.containers:
                    continue

                for container in pod.spec.containers:
                    resources = container.resources

                    if not resources or not resources.requests:
                        continue

                    cpu += self._parse_cpu(
                        resources.requests.get("cpu", "0")
                    )

                    memory += self._parse_memory(
                        resources.requests.get("memory", "0")
                    )

                requests_data[
                    f"{namespace}/{name}"
                ] = {
                    "cpu": cpu,
                    "memory": memory,
                }

            return requests_data

        except Exception as exc:
            self.logger.warning(
                "Failed to retrieve Kubernetes requests: %s",
                exc,
            )
            return self._mock_requests()

    def calculate_utilization_percent(
        self,
        usage: Dict[str, Dict[str, float]],
        requests: Dict[str, Dict[str, float]],
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate CPU and memory utilization percentages.

        Args:
            usage: Actual resource usage.
            requests: Kubernetes resource requests.

        Returns:
            Dict[str, Dict[str, Any]]: Combined utilization data.
        """
        results: Dict[str, Dict[str, Any]] = {}

        for pod_key, request in requests.items():
            actual = usage.get(
                pod_key,
                {"cpu": 0.0, "memory": 0.0},
            )

            cpu_request = request.get("cpu", 0.0)
            memory_request = request.get("memory", 0.0)

            cpu_usage = actual.get("cpu", 0.0)
            memory_usage = actual.get("memory", 0.0)

            cpu_percent = (
                cpu_usage / cpu_request * 100
                if cpu_request > 0
                else 0
            )

            memory_percent = (
                memory_usage / memory_request * 100
                if memory_request > 0
                else 0
            )

            namespace, name = pod_key.split("/", 1)

            results[pod_key] = {
                "namespace": namespace,
                "name": name,
                "cpu_request": cpu_request,
                "memory_request": memory_request,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "cpu_utilization_percent": round(cpu_percent, 2),
                "memory_utilization_percent": round(
                    memory_percent,
                    2,
                ),
                "average_utilization_percent": round(
                    (cpu_percent + memory_percent) / 2,
                    2,
                ),
            }

        return results

    def identify_over_provisioned_pods(
        self,
        utilization: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify pods below the configured utilization threshold.

        Args:
            utilization: Calculated pod utilization.

        Returns:
            List[Dict[str, Any]]: Optimization opportunities.
        """
        opportunities: List[Dict[str, Any]] = []

        for pod in utilization.values():
            cpu_ratio = pod["cpu_utilization_percent"] / 100
            memory_ratio = pod["memory_utilization_percent"] / 100

            if (
                cpu_ratio < config.COST_THRESHOLD
                or memory_ratio < config.COST_THRESHOLD
            ):
                opportunities.append(
                    {
                        **pod,
                        "reason": "Resource utilization below 30%",
                    }
                )

        return opportunities

    @staticmethod
    def _pod_key(metric: Dict[str, str]) -> str:
        """Build namespace/pod key from Prometheus labels."""
        return (
            f'{metric.get("namespace", "default")}/'
            f'{metric.get("pod", "unknown")}'
        )

    @staticmethod
    def _parse_cpu(value: str) -> float:
        """Convert Kubernetes CPU quantity into CPU cores."""
        try:
            value = str(value).strip()

            if value.endswith("m"):
                return float(value[:-1]) / 1000

            return float(value)

        except (TypeError, ValueError):
            logger.error(
                "Invalid Kubernetes CPU quantity: %r",
                value,
            )
            return 0.0

    @staticmethod
    def _parse_memory(value: str) -> float:
        """Convert Kubernetes memory quantity into GiB."""
        value = str(value)

        units = {
            "Ki": 1024,
            "Mi": 1024 ** 2,
            "Gi": 1024 ** 3,
            "Ti": 1024 ** 4,
        }

        for suffix, multiplier in units.items():
            if value.endswith(suffix):
                return (
                    float(value[:-len(suffix)])
                    * multiplier
                    / 1024 ** 3
                )

        if value.endswith("M"):
            return float(value[:-1]) / 1024

        if value.endswith("G"):
            return float(value[:-1])

        return float(value) / 1024 ** 3

    def _mock_usage(self) -> Dict[str, Dict[str, float]]:
        """Return demonstration resource usage."""
        return {
            "default/web-app": {
                "cpu": 0.10,
                "memory": 0.05,
            },
            "default/api-service": {
                "cpu": 0.10,
                "memory": 0.20,
            },
            "default/optimized-service": {
                "cpu": 0.05,
                "memory": 0.05,
            },
            "default/high-cpu-app": {
                "cpu": 0.45,
                "memory": 0.40,
            },
            "default/batch-worker": {
                "cpu": 0.40,
                "memory": 1.00,
            },
        }

    def _mock_requests(self) -> Dict[str, Dict[str, float]]:
        """Return demonstration resource requests."""
        return {
            "default/web-app": {
                "cpu": 1.0,
                "memory": 2.0,
            },
            "default/api-service": {
                "cpu": 1.0,
                "memory": 1.0,
            },
            "default/optimized-service": {
                "cpu": 0.05,
                "memory": 0.05,
            },
            "default/high-cpu-app": {
                "cpu": 0.5,
                "memory": 0.5,
            },
            "default/batch-worker": {
                "cpu": 1.0,
                "memory": 2.0,
            },
        }

    def get_mock_optimization_opportunities(
        self,
    ) -> Dict[str, Dict[str, Any]]:
        """Return complete mock utilization data for demo mode.

        Returns:
            Dict[str, Dict[str, Any]]: Mock analysis data.
        """
        return self.calculate_utilization_percent(
            self._mock_usage(),
            self._mock_requests(),
        )