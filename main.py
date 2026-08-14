"""
Main orchestration entry point for the Kubernetes Cost Optimizer.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import config
from src.action_executor import ActionExecutor
from src.cost_fetcher import GCPCostFetcher
from src.metrics_analyzer import PrometheusMetricsAnalyzer
from src.optimizer_engine import CostOptimizationEngine


def configure_logging() -> None:
    """Configure application-wide logging.

    Raises:
        OSError: If the log file cannot be created.
    """
    log_file: Path = config.LOGS_DIR / "cost-optimizer.log"

    logging.basicConfig(
        level=logging.DEBUG if config.DEBUG_MODE else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed CLI arguments.

    Raises:
        SystemExit: If invalid arguments are supplied.
    """
    parser = argparse.ArgumentParser(
        description="Kubernetes Cost Optimizer"
    )

    mode_group = parser.add_mutually_exclusive_group()

    mode_group.add_argument(
        "--analyze",
        action="store_true",
        help="Run analysis without executing changes.",
    )

    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate recommendations without executing changes.",
    )

    mode_group.add_argument(
        "--execute",
        action="store_true",
        help="Run the complete workflow including actions.",
    )

    return parser.parse_args()


def save_reports(report: Dict[str, Any]) -> None:
    """Save JSON and text versions of the optimization report.

    Args:
        report: Optimization report dictionary.

    Raises:
        OSError: If report files cannot be written.
    """
    timestamp: str = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    json_path: Path = config.REPORTS_DIR / f"report_{timestamp}.json"
    text_path: Path = config.REPORTS_DIR / f"report_{timestamp}.txt"

    try:
        with json_path.open("w", encoding="utf-8") as json_file:
            json.dump(report, json_file, indent=2)
    except OSError as exc:
        logging.error("Failed to save JSON report: %s", exc)
        return

    try:
        with text_path.open("w", encoding="utf-8") as text_file:
            text_file.write(report["text"])
    except OSError as exc:
        logging.error("Failed to save text report: %s", exc)
        return

    logging.info("JSON report saved to %s", json_path)
    logging.info("Text report saved to %s", text_path)


def run() -> int:
    """Execute the complete cost optimization workflow.

    Returns:
        int: Process exit code.
    """
    logger = logging.getLogger(__name__)
    args = parse_arguments()

    execute_changes: bool = bool(args.execute)
    logger.info("Starting Kubernetes Cost Optimizer")

    try:
        logger.info("Step 1/5: Initializing GCP cost fetcher")
        cost_fetcher = GCPCostFetcher()

        logger.info("Step 2/5: Fetching GCP cost data")
        cost_data = cost_fetcher.fetch_daily_costs()

        logger.info(
            "Fetched %d days of cost data",
            len(cost_data.get("daily_costs", [])),
        )

    except Exception as exc:
        logger.exception("Cost collection failed: %s", exc)
        cost_data = {"daily_costs": [], "services": {}, "source": "error"}

    try:
        logger.info("Step 3/5: Initializing metrics analyzer")

        analyzer = PrometheusMetricsAnalyzer()

        analyzer.connect_to_prometheus()

        usage = analyzer.get_pod_resource_usage()
        requests = analyzer.get_pod_resource_requests()

        utilization = analyzer.calculate_utilization_percent(
            usage,
            requests,
        )

        opportunities = analyzer.identify_over_provisioned_pods(
            utilization,
        )

        logger.info(
            "Analyzed %d pods; found %d optimization opportunities",
            len(utilization),
            len(opportunities),
        )

    except Exception as exc:
        logger.exception("Metrics analysis failed: %s", exc)

        analyzer = PrometheusMetricsAnalyzer()
        opportunities = analyzer.get_mock_optimization_opportunities()
        utilization = opportunities

    try:
        logger.info("Step 4/5: Generating recommendations")

        engine = CostOptimizationEngine()

        engine.analyze_waste(opportunities)

        recommendations = engine.generate_recommendations(
            opportunities
        )

        report = engine.create_optimization_report(
            recommendations=recommendations,
            cost_data=cost_data,
        )

        logger.info(
            "Generated %d recommendations",
            len(recommendations),
        )

    except Exception as exc:
        logger.exception("Optimization engine failed: %s", exc)
        return 1

    try:
        logger.info("Step 5/5: Saving report")

        save_reports(report)

        executor = ActionExecutor(
            dry_run=not execute_changes
        )

        if execute_changes:
            logger.info("Execution mode enabled")

            for recommendation in recommendations:
                executor.execute_recommendation(
                    recommendation
                )
        else:
            logger.info(
                "No changes executed. Use --execute to enable actions."
            )

        report_text = executor.generate_report_text(
            recommendations
        )

        executor.send_weekly_report(
            report_text,
            config.REPORTS_DIR,
        )

    except Exception as exc:
        logger.exception("Action/report stage failed: %s", exc)
        return 1

    logger.info("Optimization workflow completed successfully")

    print("\n" + report["text"])

    return 0


if __name__ == "__main__":
    configure_logging()

    try:
        sys.exit(run())
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning(
            "Execution interrupted by user"
        )
        sys.exit(130)