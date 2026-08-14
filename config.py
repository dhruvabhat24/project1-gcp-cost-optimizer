"""
Central configuration for the Kubernetes Cost Optimizer.

The application supports two operating modes:

1. DEMO MODE
   - Uses deterministic mock billing data.
   - Does not require GCP credentials.
   - Does not require BigQuery.
   - Ideal for local development and portfolio demonstrations.

2. REAL MODE
   - Queries Google Cloud Billing Export data stored in BigQuery.
   - Uses Application Default Credentials.
   - Requires Cloud Billing export to BigQuery to be enabled.
   - Requires appropriate BigQuery IAM permissions.

Environment variables can override all major settings.
"""

import os
from pathlib import Path


# ============================================================================
# Project paths
# ============================================================================

BASE_DIR: Path = Path(__file__).resolve().parent

REPORTS_DIR: Path = BASE_DIR / "reports"

LOGS_DIR: Path = BASE_DIR / "logs"


# ============================================================================
# GCP / BigQuery configuration
# ============================================================================

# Project containing the BigQuery billing-export dataset.
GCP_PROJECT_ID: str = os.getenv(
    "GCP_PROJECT_ID",
    "demo-project",
)

# BigQuery dataset containing the Cloud Billing export.
#
# Example:
#   billing_export
#
# This is NOT necessarily the same project as GCP_PROJECT_ID.
BIGQUERY_BILLING_DATASET: str = os.getenv(
    "BIGQUERY_BILLING_DATASET",
    "billing_export",
)

# Billing export table.
#
# Example:
#   gcp_billing_export_resource_v1_012345_ABCDEF_123456
#
# If empty, the application automatically constructs the detailed
# export table name from GCP_BILLING_ACCOUNT_ID.
BIGQUERY_BILLING_TABLE: str = os.getenv(
    "BIGQUERY_BILLING_TABLE",
    "",
)

# Cloud Billing account ID.
#
# Example:
#   012345-ABCDEF-123456
#
# Google Cloud Billing export replaces hyphens with underscores
# in the exported table name.
GCP_BILLING_ACCOUNT_ID: str = os.getenv(
    "GCP_BILLING_ACCOUNT_ID",
    "",
)

# Optional path to a service-account JSON file.
#
# Example Windows path:
# C:\Users\Raider\gcp\cost-optimizer-sa.json
#
# Prefer Application Default Credentials / Workload Identity in
# production rather than distributing service-account keys.
GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "",
)


# ============================================================================
# Kubernetes configuration
# ============================================================================

KUBERNETES_NAMESPACE: str = os.getenv(
    "KUBERNETES_NAMESPACE",
    "default",
)


# ============================================================================
# Prometheus configuration
# ============================================================================

PROMETHEUS_URL: str = os.getenv(
    "PROMETHEUS_URL",
    "http://localhost:9090",
)

PROMETHEUS_SCRAPE_INTERVAL: int = int(
    os.getenv(
        "PROMETHEUS_SCRAPE_INTERVAL",
        "15",
    )
)


# ============================================================================
# Cost optimization configuration
# ============================================================================

# Pods below this utilization ratio are considered candidates
# for optimization.
#
# 0.30 = 30%
COST_THRESHOLD: float = float(
    os.getenv(
        "COST_THRESHOLD",
        "0.30",
    )
)

# Demonstration estimates used by the optimization engine.
#
# These values are NOT official GCP prices.
MONTHLY_COST_PER_CPU: float = float(
    os.getenv(
        "MONTHLY_COST_PER_CPU",
        "25.0",
    )
)

MONTHLY_COST_PER_GB_MEMORY: float = float(
    os.getenv(
        "MONTHLY_COST_PER_GB_MEMORY",
        "3.50",
    )
)

# Estimated discount for interruptible batch workloads.
SPOT_DISCOUNT_PERCENT: float = float(
    os.getenv(
        "SPOT_DISCOUNT_PERCENT",
        "60.0",
    )
)

# Usage below this ratio can be considered effectively unused.
UNUSED_USAGE_THRESHOLD: float = float(
    os.getenv(
        "UNUSED_USAGE_THRESHOLD",
        "0.01",
    )
)


# ============================================================================
# Reporting configuration
# ============================================================================

REPORT_DAY: str = os.getenv(
    "REPORT_DAY",
    "Monday",
)

REPORT_TIME: str = os.getenv(
    "REPORT_TIME",
    "02:00",
)


# ============================================================================
# Runtime configuration
# ============================================================================

# True:
#   BigQuery is not contacted.
#
# False:
#   The application attempts to query the BigQuery billing export.
USE_MOCK_DATA: bool = os.getenv(
    "USE_MOCK_DATA",
    "True",
).lower() in {
    "true",
    "1",
    "yes",
    "y",
}

DEBUG_MODE: bool = os.getenv(
    "DEBUG_MODE",
    "True",
).lower() in {
    "true",
    "1",
    "yes",
    "y",
}

DRY_RUN: bool = os.getenv(
    "DRY_RUN",
    "True",
).lower() in {
    "true",
    "1",
    "yes",
    "y",
}


# ============================================================================
# BigQuery query configuration
# ============================================================================

# Number of historical days requested by the optimizer.
COST_LOOKBACK_DAYS: int = int(
    os.getenv(
        "COST_LOOKBACK_DAYS",
        "7",
    )
)

# BigQuery job timeout.
BIGQUERY_QUERY_TIMEOUT_SECONDS: int = int(
    os.getenv(
        "BIGQUERY_QUERY_TIMEOUT_SECONDS",
        "60",
    )
)


# ============================================================================
# Create runtime directories
# ============================================================================

REPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LOGS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)