"""
Cost optimization and recommendation engine.

This module analyzes Kubernetes resource waste, estimates potential
monthly savings, generates actionable recommendations, ranks them by
priority, and creates a machine-readable optimization report.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import config


class CostOptimizationEngine:
    """Analyze Kubernetes resource waste and produce recommendations."""

    def __init__(self) -> None:
        """Initialize the cost optimization engine.

        The engine stores the most recent waste analysis so that later
        recommendation-generation steps can reuse it without repeating
        the calculations.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.analysis: List[Dict[str, Any]] = []

    def analyze_waste(
        self,
        opportunities: Any,
    ) -> List[Dict[str, Any]]:
        """Calculate unused CPU and memory resources for each pod.

        Args:
            opportunities: Pod utilization information returned by
                PrometheusMetricsAnalyzer.identify_over_provisioned_pods().
                A dictionary or list of dictionaries is supported.

        Returns:
            List[Dict[str, Any]]: Normalized pod waste-analysis records.

        Raises:
            ValueError: If opportunities is not a dictionary or list.
        """
        if isinstance(opportunities, dict):
            values = list(opportunities.values())
        elif isinstance(opportunities, list):
            values = opportunities
        else:
            raise ValueError(
                "opportunities must be a dictionary or list"
            )

        self.analysis = []

        for pod in values:
            if not isinstance(pod, dict):
                self.logger.warning(
                    "Skipping invalid optimization opportunity: %r",
                    pod,
                )
                continue

            cpu_request = float(
                pod.get("cpu_request", 0.0)
            )
            memory_request = float(
                pod.get("memory_request", 0.0)
            )

            cpu_usage = float(
                pod.get("cpu_usage", 0.0)
            )
            memory_usage = float(
                pod.get("memory_usage", 0.0)
            )

            cpu_waste = max(
                cpu_request - cpu_usage,
                0.0,
            )

            memory_waste = max(
                memory_request - memory_usage,
                0.0,
            )

            waste_record = {
                **pod,
                "cpu_waste": round(cpu_waste, 4),
                "memory_waste": round(memory_waste, 4),
            }

            self.analysis.append(waste_record)

        self.logger.info(
            "Analyzed resource waste for %d pods",
            len(self.analysis),
        )

        return self.analysis

    def calculate_savings(
        self,
        pod: Dict[str, Any],
    ) -> float:
        """Estimate monthly savings from right-sizing one pod.

        The calculation uses the configured approximate monthly CPU and
        memory costs and the amount of unused requested capacity.

        Args:
            pod: A single pod waste-analysis dictionary.

        Returns:
            float: Estimated monthly savings in INR.

        Raises:
            ValueError: If pod is not a dictionary.
        """
        if not isinstance(pod, dict):
            raise ValueError(
                "pod must be a dictionary"
            )

        cpu_waste = float(
            pod.get("cpu_waste", 0.0)
        )

        memory_waste = float(
            pod.get("memory_waste", 0.0)
        )

        cpu_savings = (
            cpu_waste
            * config.MONTHLY_COST_PER_CPU
        )

        memory_savings = (
            memory_waste
            * config.MONTHLY_COST_PER_GB_MEMORY
        )

        total_savings = (
            cpu_savings
            + memory_savings
        )

        return round(
            total_savings,
            2,
        )

    def generate_recommendations(
        self,
        opportunities: Any,
    ) -> List[Dict[str, Any]]:
        """Generate actionable and prioritized recommendations.

        Recommendations are based on CPU and memory utilization. Very
        low-utilization workloads receive higher priority because they
        represent larger right-sizing opportunities.

        Batch workloads additionally receive a Spot instance suggestion.

        Args:
            opportunities: Pod utilization information.

        Returns:
            List[Dict[str, Any]]: Prioritized optimization recommendations.

        Raises:
            ValueError: If opportunities cannot be analyzed.
        """
        if not self.analysis:
            self.analyze_waste(opportunities)

        recommendations: List[Dict[str, Any]] = []

        for pod in self.analysis:
            namespace = pod.get(
                "namespace",
                "default",
            )

            name = pod.get(
                "name",
                "unknown",
            )

            cpu_percent = float(
                pod.get(
                    "cpu_utilization_percent",
                    0.0,
                )
            )

            memory_percent = float(
                pod.get(
                    "memory_utilization_percent",
                    0.0,
                )
            )

            average = float(
                pod.get(
                    "average_utilization_percent",
                    0.0,
                )
            )

            savings = self.calculate_savings(
                pod
            )

            # Default recommendation.
            action = "Maintain current resource allocation"
            priority = "Low"

            # Very high utilization means the workload may need
            # additional capacity rather than optimization.
            if average >= 80:
                action = (
                    "Monitor workload; resources are "
                    "appropriately utilized"
                )
                priority = "Low"

            # Low utilization indicates a right-sizing opportunity.
            elif (
                cpu_percent < 30
                or memory_percent < 30
            ):
                action = (
                    "Right-size CPU and memory requests "
                    "based on observed utilization"
                )

                if average < 10:
                    priority = "High"
                elif average < 20:
                    priority = "High"
                else:
                    priority = "Medium"

            # Detect batch-worker regardless of the generated
            # Kubernetes ReplicaSet/Deployment suffix.
            if (
                namespace != "kube-system"
                and name.startswith("batch-worker")
            ):
                action = (
                    "Right-size resources and consider "
                    "Spot instance/node pool for batch workload"
                )

                # Spot discount represents the percentage of cost
                # removed. Example: 70% discount => retain 30%.
                spot_discount = (
                    config.SPOT_DISCOUNT_PERCENT / 100
                )

                savings += (
                    savings * spot_discount
                )

            recommendation = {
                "namespace": namespace,
                "pod_name": name,
                "current_cpu_cores": round(
                    float(
                        pod.get(
                            "cpu_request",
                            0.0,
                        )
                    ),
                    4,
                ),
                "actual_cpu_cores": round(
                    float(
                        pod.get(
                            "cpu_usage",
                            0.0,
                        )
                    ),
                    4,
                ),
                "current_memory_gb": round(
                    float(
                        pod.get(
                            "memory_request",
                            0.0,
                        )
                    ),
                    4,
                ),
                "actual_memory_gb": round(
                    float(
                        pod.get(
                            "memory_usage",
                            0.0,
                        )
                    ),
                    4,
                ),
                "cpu_utilization_percent": cpu_percent,
                "memory_utilization_percent": memory_percent,
                "average_utilization_percent": average,
                "cpu_waste": pod.get(
                    "cpu_waste",
                    0.0,
                ),
                "memory_waste": pod.get(
                    "memory_waste",
                    0.0,
                ),
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

            recommendation["priority_score"] = (
                self.priority_score(
                    recommendation
                )
            )

            recommendations.append(
                recommendation
            )

        recommendations.sort(
            key=lambda item: item["priority_score"],
            reverse=True,
        )

        self.logger.info(
            "Generated %d optimization recommendations",
            len(recommendations),
        )

        return recommendations

    def priority_score(
        self,
        recommendation: Dict[str, Any],
    ) -> float:
        """Calculate a 0-100 priority score for a recommendation.

        Higher scores indicate greater resource waste and/or greater
        potential monthly savings.

        Args:
            recommendation: Recommendation dictionary.

        Returns:
            float: Priority score between 0 and 100.
        """
        savings = float(
            recommendation.get(
                "estimated_monthly_savings_inr",
                0.0,
            )
        )

        cpu_utilization = float(
            recommendation.get(
                "cpu_utilization_percent",
                100.0,
            )
        )

        memory_utilization = float(
            recommendation.get(
                "memory_utilization_percent",
                100.0,
            )
        )

        average_utilization = (
            cpu_utilization
            + memory_utilization
        ) / 2

        waste_factor = max(
            100.0 - average_utilization,
            0.0,
        )

        # Waste contributes up to 70 points.
        waste_score = (
            waste_factor * 0.7
        )

        # Savings contributes up to 30 points.
        savings_score = min(
            savings / 10.0,
            30.0,
        )

        score = min(
            100.0,
            waste_score + savings_score,
        )

        return round(
            score,
            2,
        )

    def create_optimization_report(
        self,
        recommendations: List[Dict[str, Any]],
        cost_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a machine-readable and human-readable report.

        Args:
            recommendations: Generated optimization recommendations.
            cost_data: Cost information from the cost fetcher.

        Returns:
            Dict[str, Any]: Complete optimization report containing
                timestamp, summary, cost data, recommendations, and
                formatted text.

        Raises:
            ValueError: If recommendations or cost_data have invalid types.
        """
        if not isinstance(
            recommendations,
            list,
        ):
            raise ValueError(
                "recommendations must be a list"
            )

        if not isinstance(
            cost_data,
            dict,
        ):
            raise ValueError(
                "cost_data must be a dictionary"
            )

        total_savings = round(
            sum(
                float(
                    item.get(
                        "estimated_monthly_savings_inr",
                        0.0,
                    )
                )
                for item in recommendations
            ),
            2,
        )

        high_priority = sum(
            item.get(
                "implementation_priority"
            ) == "High"
            for item in recommendations
        )

        medium_priority = sum(
            item.get(
                "implementation_priority"
            ) == "Medium"
            for item in recommendations
        )

        low_priority = sum(
            item.get(
                "implementation_priority"
            ) == "Low"
            for item in recommendations
        )

        seven_day_cost = float(
            cost_data.get(
                "seven_day_total_inr",
                0.0,
            )
        )

        monthly_cost = float(
            cost_data.get(
                "estimated_monthly_cost_inr",
                0.0,
            )
        )

        lines = [
            "=" * 72,
            "KUBERNETES COST OPTIMIZATION REPORT",
            "=" * 72,
            "",
            (
                "Generated: "
                f"{datetime.now(timezone.utc).isoformat()}"
            ),
            (
                "GCP Project: "
                f"{cost_data.get('project_id', 'demo-project')}"
            ),
            (
                "Cost Source: "
                f"{cost_data.get('source', 'unknown')}"
            ),
            "",
            (
                f"7-Day GCP Cost: "
                f"₹{seven_day_cost:,.2f}"
            ),
            (
                "Estimated Monthly GCP Cost: "
                f"₹{monthly_cost:,.2f}"
            ),
            "",
            (
                "Optimization Opportunities: "
                f"{len(recommendations)}"
            ),
            (
                f"High Priority: {high_priority}"
            ),
            (
                f"Medium Priority: {medium_priority}"
            ),
            (
                f"Low Priority: {low_priority}"
            ),
            (
                "Estimated Monthly Savings: "
                f"₹{total_savings:,.2f}"
            ),
            "",
            "RECOMMENDATIONS",
            "-" * 72,
        ]

        for item in recommendations:
            lines.extend(
                [
                    (
                        "Pod: "
                        f"{item.get('namespace', 'default')}/"
                        f"{item.get('pod_name', 'unknown')}"
                    ),
                    (
                        f"CPU: "
                        f"{item.get('actual_cpu_cores', 0):.4f} / "
                        f"{item.get('current_cpu_cores', 0):.4f} cores "
                        f"({item.get('cpu_utilization_percent', 0):.1f}%)"
                    ),
                    (
                        f"Memory: "
                        f"{item.get('actual_memory_gb', 0):.4f} / "
                        f"{item.get('current_memory_gb', 0):.4f} GB "
                        f"({item.get('memory_utilization_percent', 0):.1f}%)"
                    ),
                    (
                        "Action: "
                        f"{item.get('suggested_action', 'N/A')}"
                    ),
                    (
                        "Savings: "
                        f"₹{item.get('estimated_monthly_savings_inr', 0):,.2f}"
                        "/month"
                    ),
                    (
                        "Priority: "
                        f"{item.get('implementation_priority', 'Low')}"
                    ),
                    (
                        "Priority Score: "
                        f"{item.get('priority_score', 0):.2f}"
                    ),
                    "",
                ]
            )

        lines.extend(
            [
                "-" * 72,
                (
                    "Potential monthly savings represent "
                    "estimated optimization opportunities."
                ),
                (
                    "Actual GCP savings depend on the resulting "
                    "resource allocation and billing model."
                ),
                "=" * 72,
            ]
        )

        report = {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": {
                "recommendation_count": len(
                    recommendations
                ),
                "high_priority_count": high_priority,
                "medium_priority_count": medium_priority,
                "low_priority_count": low_priority,
                "estimated_monthly_savings_inr": total_savings,
            },
            "cost_data": cost_data,
            "recommendations": recommendations,
            "text": "\n".join(lines),
        }

        self.logger.info(
            "Optimization report created: %d recommendations, "
            "₹%.2f estimated monthly savings",
            len(recommendations),
            total_savings,
        )

        return report