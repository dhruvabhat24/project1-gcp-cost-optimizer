"""
Cost optimization and recommendation engine.
"""

import logging
from typing import Any, Dict, List

import config


class CostOptimizationEngine:
    """Analyze Kubernetes waste and produce prioritized recommendations."""

    def __init__(self) -> None:
        """Initialize the optimization engine."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.analysis: List[Dict[str, Any]] = []

    def analyze_waste(
        self,
        opportunities: Any,
    ) -> List[Dict[str, Any]]:
        """Analyze resource waste for Kubernetes workloads.

        Args:
            opportunities: Pod utilization information. Supports either
                a dictionary or list.

        Returns:
            List[Dict[str, Any]]: Normalized waste analysis.
        """
        if isinstance(opportunities, dict):
            values = list(opportunities.values())
        else:
            values = list(opportunities)

        self.analysis = []

        for pod in values:
            cpu_request = float(pod.get("cpu_request", 0))
            memory_request = float(pod.get("memory_request", 0))

            cpu_usage = float(pod.get("cpu_usage", 0))
            memory_usage = float(pod.get("memory_usage", 0))

            cpu_waste = max(cpu_request - cpu_usage, 0)
            memory_waste = max(memory_request - memory_usage, 0)

            self.analysis.append(
                {
                    **pod,
                    "cpu_waste": round(cpu_waste, 4),
                    "memory_waste": round(memory_waste, 4),
                }
            )

        return self.analysis

    def calculate_savings(
        self,
        pod: Dict[str, Any],
    ) -> float:
        """Estimate monthly savings from right-sizing a pod.

        Args:
            pod: Pod waste analysis.

        Returns:
            float: Estimated monthly savings in INR.
        """
        cpu_savings = (
            pod.get("cpu_waste", 0)
            * config.MONTHLY_COST_PER_CPU
        )

        memory_savings = (
            pod.get("memory_waste", 0)
            * config.MONTHLY_COST_PER_GB_MEMORY
        )

        return round(
            cpu_savings + memory_savings,
            2,
        )

    def generate_recommendations(
        self,
        opportunities: Any,
    ) -> List[Dict[str, Any]]:
        """Generate actionable optimization recommendations.

        Args:
            opportunities: Pod utilization information.

        Returns:
            List[Dict[str, Any]]: Prioritized recommendations.
        """
        if not self.analysis:
            self.analyze_waste(opportunities)

        recommendations: List[Dict[str, Any]] = []

        for pod in self.analysis:
            namespace = pod.get("namespace", "default")
            name = pod.get("name", "unknown")

            cpu_percent = pod.get(
                "cpu_utilization_percent",
                0,
            )

            memory_percent = pod.get(
                "memory_utilization_percent",
                0,
            )

            average = pod.get(
                "average_utilization_percent",
                0,
            )

            savings = self.calculate_savings(pod)

            if average >= 80:
                action = "Monitor; workload is appropriately sized"
                priority = "Low"

            elif cpu_percent < 30 or memory_percent < 30:
                action = "Right-size CPU/memory requests"

                if average < 10:
                    priority = "High"
                elif average < 20:
                    priority = "High"
                else:
                    priority = "Medium"

            else:
                action = "Maintain current resource allocation"
                priority = "Low"

            if name == "batch-worker":
                action = (
                    "Right-size resources and consider Spot "
                    "instance/node pool"
                )

                savings *= (
                    1 + config.SPOT_DISCOUNT_PERCENT / 100
                )

            recommendation = {
                "namespace": namespace,
                "pod_name": name,
                "current_cpu_cores": pod.get("cpu_request", 0),
                "actual_cpu_cores": pod.get("cpu_usage", 0),
                "current_memory_gb": pod.get(
                    "memory_request",
                    0,
                ),
                "actual_memory_gb": pod.get(
                    "memory_usage",
                    0,
                ),
                "cpu_utilization_percent": cpu_percent,
                "memory_utilization_percent": memory_percent,
                "suggested_action": action,
                "estimated_monthly_savings_inr": round(
                    savings,
                    2,
                ),
                "implementation_priority": priority,
                "reason": pod.get(
                    "reason",
                    "Resource utilization analysis",
                ),
            }

            recommendation["priority_score"] = self.priority_score(
                recommendation
            )

            recommendations.append(recommendation)

        recommendations.sort(
            key=lambda item: item["priority_score"],
            reverse=True,
        )

        return recommendations

    def priority_score(
        self,
        recommendation: Dict[str, Any],
    ) -> float:
        """Calculate a recommendation priority score.

        Args:
            recommendation: Recommendation data.

        Returns:
            float: Score between approximately 0 and 100.
        """
        savings = float(
            recommendation.get(
                "estimated_monthly_savings_inr",
                0,
            )
        )

        utilization = (
            float(
                recommendation.get(
                    "cpu_utilization_percent",
                    100,
                )
            )
            + float(
                recommendation.get(
                    "memory_utilization_percent",
                    100,
                )
            )
        ) / 2

        waste_factor = max(
            100 - utilization,
            0,
        )

        score = min(
            100,
            waste_factor * 0.7
            + min(savings / 10, 30),
        )

        return round(score, 2)

    def create_optimization_report(
        self,
        recommendations: List[Dict[str, Any]],
        cost_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a machine-readable and human-readable report.

        Args:
            recommendations: Generated recommendations.
            cost_data: GCP cost information.

        Returns:
            Dict[str, Any]: Complete report.
        """
        total_savings = round(
            sum(
                item["estimated_monthly_savings_inr"]
                for item in recommendations
            ),
            2,
        )

        high_priority = sum(
            item["implementation_priority"] == "High"
            for item in recommendations
        )

        lines = [
            "=" * 72,
            "KUBERNETES COST OPTIMIZATION REPORT",
            "=" * 72,
            "",
            f"GCP Project: {cost_data.get('project_id', 'demo-project')}",
            f"Cost Source: {cost_data.get('source', 'unknown')}",
            "",
            f"7-Day GCP Cost: ₹"
            f"{cost_data.get('seven_day_total_inr', 0):,.2f}",
            f"Estimated Monthly GCP Cost: ₹"
            f"{cost_data.get('estimated_monthly_cost_inr', 0):,.2f}",
            "",
            f"Optimization Opportunities: "
            f"{len(recommendations)}",
            f"High Priority: {high_priority}",
            f"Estimated Monthly Savings: ₹"
            f"{total_savings:,.2f}",
            "",
            "RECOMMENDATIONS",
            "-" * 72,
        ]

        for item in recommendations:
            lines.extend(
                [
                    f"Pod: {item['namespace']}/"
                    f"{item['pod_name']}",
                    f"CPU: {item['actual_cpu_cores']:.2f} / "
                    f"{item['current_cpu_cores']:.2f} cores "
                    f"({item['cpu_utilization_percent']:.1f}%)",
                    f"Memory: {item['actual_memory_gb']:.2f} / "
                    f"{item['current_memory_gb']:.2f} GB "
                    f"({item['memory_utilization_percent']:.1f}%)",
                    f"Action: {item['suggested_action']}",
                    f"Savings: ₹"
                    f"{item['estimated_monthly_savings_inr']:,.2f}/month",
                    f"Priority: "
                    f"{item['implementation_priority']}",
                    f"Score: {item['priority_score']}",
                    "",
                ]
            )

        lines.append("=" * 72)

        return {
            "generated_at": __import__(
                "datetime"
            ).datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "summary": {
                "recommendation_count": len(recommendations),
                "high_priority_count": high_priority,
                "estimated_monthly_savings_inr": total_savings,
            },
            "cost_data": cost_data,
            "recommendations": recommendations,
            "text": "\n".join(lines),
        }