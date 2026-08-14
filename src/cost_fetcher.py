"""
Google Cloud Billing cost collection through BigQuery.

Architecture:

    Cloud Billing
          |
          v
    BigQuery Billing Export
          |
          v
    GCPCostFetcher
          |
          v
    Optimization Engine

The class intentionally keeps the same interface used by the rest of the
project:

    authenticate_gcp()
    fetch_daily_costs()
    get_cost_by_service()

DEMO MODE:
    USE_MOCK_DATA=true

REAL MODE:
    USE_MOCK_DATA=false

Real mode requires:
    - Cloud Billing export to BigQuery
    - BigQuery dataset containing billing data
    - Google Cloud credentials
    - BigQuery read permissions
"""

import logging
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from google.auth import default
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery

import config


class GCPCostFetcher:
    """Fetch GCP Cloud Billing Export data from BigQuery."""

    def __init__(self) -> None:
        """Initialize the BigQuery-based GCP cost fetcher.

        The BigQuery client is initialized lazily after authentication so
        demo mode does not require a live GCP connection.

        Raises:
            ValueError: If a required BigQuery configuration value is invalid.
        """
        self.logger = logging.getLogger(
            self.__class__.__name__
        )

        self.credentials: Optional[Credentials] = None

        self.bigquery_client: Optional[
            bigquery.Client
        ] = None

        self.authenticated: bool = False

        self.billing_table: str = (
            self._build_billing_table_reference()
        )

    def authenticate_gcp(self) -> bool:
        """Authenticate with Google Cloud and initialize BigQuery.

        Application Default Credentials are used. This supports:

        - GOOGLE_APPLICATION_CREDENTIALS
        - gcloud application-default login
        - Workload Identity
        - Service account environments
        - Other ADC-supported environments

        Returns:
            bool: True when authentication and BigQuery initialization
                succeed, otherwise False.

        Raises:
            DefaultCredentialsError: Not propagated; authentication failures
                are logged and converted to False.
        """
        if config.USE_MOCK_DATA:
            self.logger.info(
                "Mock mode enabled; skipping GCP authentication"
            )

            self.authenticated = False
            return False

        try:
            self.logger.info(
                "Authenticating with Google Cloud for BigQuery"
            )

            credentials, detected_project = default(
                scopes=[
                    "https://www.googleapis.com/auth/cloud-platform"
                ]
            )

            self.credentials = credentials

            project_id = (
                config.GCP_PROJECT_ID
                if config.GCP_PROJECT_ID != "demo-project"
                else detected_project
            )

            if not project_id:
                raise RuntimeError(
                    "Unable to determine GCP project ID"
                )

            self.bigquery_client = bigquery.Client(
                project=project_id,
                credentials=credentials,
            )

            self.authenticated = True

            self.logger.info(
                "BigQuery authentication successful"
            )

            self.logger.debug(
                "BigQuery project: %s",
                project_id,
            )

            self.logger.debug(
                "Billing table: %s",
                self.billing_table,
            )

            return True

        except DefaultCredentialsError as exc:
            self.logger.error(
                "Google Cloud credentials unavailable: %s",
                exc,
            )

        except Exception as exc:
            self.logger.exception(
                "BigQuery authentication failed: %s",
                exc,
            )

        self.authenticated = False
        self.bigquery_client = None

        return False

    def fetch_daily_costs(self) -> Dict[str, Any]:
        """Fetch the previous seven days of GCP billing costs.

        In real mode this queries the Cloud Billing detailed usage export
        in BigQuery.

        The query groups billing data by calendar day and sums the exported
        cost field.

        Returns:
            Dict[str, Any]: Normalized cost information containing:

                - source
                - project_id
                - billing_table
                - currency
                - daily_costs
                - services
                - seven_day_total
                - estimated_monthly_cost

        Raises:
            RuntimeError: If BigQuery is required but unavailable.
        """
        if config.USE_MOCK_DATA:
            self.logger.info(
                "USE_MOCK_DATA=true; returning mock billing data"
            )

            return self._mock_cost_data()

        if not self.authenticated:
            authenticated = self.authenticate_gcp()

            if not authenticated:
                self.logger.warning(
                    "Unable to authenticate with BigQuery. "
                    "Falling back to mock billing data."
                )

                return self._mock_cost_data(
                    source="bigquery-auth-fallback"
                )

        if not self.bigquery_client:
            self.logger.warning(
                "BigQuery client unavailable. "
                "Falling back to mock data."
            )

            return self._mock_cost_data(
                source="bigquery-client-fallback"
            )

        try:
            daily_costs = self._query_daily_costs()

            services = self._query_service_costs()

            if not daily_costs:
                self.logger.warning(
                    "BigQuery returned no daily cost records. "
                    "Using mock billing data."
                )

                return self._mock_cost_data(
                    source="bigquery-empty-fallback"
                )

            total_cost = round(
                sum(
                    item["cost"]
                    for item in daily_costs
                ),
                2,
            )

            estimated_monthly_cost = round(
                total_cost
                / max(len(daily_costs), 1)
                * 30,
                2,
            )

            currency = self._detect_currency(
                daily_costs
            )

            result = {
                "source": "bigquery",
                "project_id": config.GCP_PROJECT_ID,
                "billing_table": self.billing_table,
                "currency": currency,
                "daily_costs": daily_costs,
                "services": services,
                "seven_day_total_inr": total_cost,
                "estimated_monthly_cost_inr": (
                    estimated_monthly_cost
                ),
            }

            self.logger.info(
                "Successfully retrieved %d daily cost records",
                len(daily_costs),
            )

            self.logger.info(
                "Seven-day billing total: %.2f %s",
                total_cost,
                currency,
            )

            return result

        except Exception as exc:
            self.logger.exception(
                "BigQuery cost query failed: %s",
                exc,
            )

            return self._mock_cost_data(
                source="bigquery-error-fallback"
            )

    def get_cost_by_service(
        self,
        cost_data: Dict[str, Any],
    ) -> Dict[str, float]:
        """Return cost totals grouped by Google Cloud service.

        Args:
            cost_data: Normalized cost data returned by
                fetch_daily_costs().

        Returns:
            Dict[str, float]: Service name to cost mapping.
        """
        services: Dict[str, float] = {}

        raw_services = cost_data.get(
            "services",
            {},
        )

        if not isinstance(raw_services, dict):
            self.logger.warning(
                "Invalid service cost structure"
            )
            return services

        for service, value in raw_services.items():
            try:
                services[str(service)] = round(
                    float(value),
                    2,
                )

            except (
                TypeError,
                ValueError,
            ):
                self.logger.warning(
                    "Unable to parse cost for service %s: %r",
                    service,
                    value,
                )

        return services

    def _query_daily_costs(
        self,
    ) -> List[Dict[str, Any]]:
        """Query BigQuery for daily Cloud Billing costs.

        The Cloud Billing export provides cost records with timestamps.
        The query aggregates the cost field by calendar date.

        Returns:
            List[Dict[str, Any]]: Daily cost records.

        Raises:
            RuntimeError: If the BigQuery client is unavailable.
        """
        if not self.bigquery_client:
            raise RuntimeError(
                "BigQuery client is not initialized"
            )

        table = self._safe_table_reference()

        query = f"""
        SELECT
            DATE(usage_start_time) AS usage_date,
            SUM(cost) AS total_cost,
            ANY_VALUE(currency) AS currency
        FROM `{table}`
        WHERE
            usage_start_time >= TIMESTAMP_SUB(
                CURRENT_TIMESTAMP(),
                INTERVAL @lookback_days DAY
            )
            AND usage_start_time < CURRENT_TIMESTAMP()
            AND cost_type = 'regular'
            AND project.id = @project_id
        GROUP BY
            usage_date
        ORDER BY
            usage_date ASC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "lookback_days",
                    "INT64",
                    config.COST_LOOKBACK_DAYS,
                ),
                bigquery.ScalarQueryParameter(
                    "project_id",
                    "STRING",
                    config.GCP_PROJECT_ID,
                ),
            ]
        )

        self.logger.debug(
            "Executing daily BigQuery billing query"
        )

        query_job = self.bigquery_client.query(
            query,
            job_config=job_config,
        )

        rows = query_job.result(
            timeout=config.BIGQUERY_QUERY_TIMEOUT_SECONDS
        )

        daily_costs: List[Dict[str, Any]] = []

        for row in rows:
            total_cost = float(
                row.total_cost or 0
            )

            daily_costs.append(
                {
                    "date": row.usage_date.isoformat(),
                    "cost": round(
                        total_cost,
                        2,
                    ),
                    "cost_inr": round(
                        total_cost,
                        2,
                    ),
                    "currency": row.currency or "UNKNOWN",
                }
            )

        return daily_costs

    def _query_service_costs(
        self,
    ) -> Dict[str, float]:
        """Query BigQuery for cost grouped by Google Cloud service.

        Returns:
            Dict[str, float]: Service-level cost breakdown.

        Raises:
            RuntimeError: If BigQuery is unavailable.
        """
        if not self.bigquery_client:
            raise RuntimeError(
                "BigQuery client is not initialized"
            )

        table = self._safe_table_reference()

        query = f"""
        SELECT
            service.description AS service_name,
            SUM(cost) AS total_cost
        FROM `{table}`
        WHERE
            usage_start_time >= TIMESTAMP_SUB(
                CURRENT_TIMESTAMP(),
                INTERVAL @lookback_days DAY
            )
            AND usage_start_time < CURRENT_TIMESTAMP()
            AND cost_type = 'regular'
            AND project.id = @project_id
        GROUP BY
            service_name
        ORDER BY
            total_cost DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "lookback_days",
                    "INT64",
                    config.COST_LOOKBACK_DAYS,
                ),
                bigquery.ScalarQueryParameter(
                    "project_id",
                    "STRING",
                    config.GCP_PROJECT_ID,
                ),
            ]
        )

        self.logger.debug(
            "Executing service-level BigQuery billing query"
        )

        query_job = self.bigquery_client.query(
            query,
            job_config=job_config,
        )

        rows = query_job.result(
            timeout=config.BIGQUERY_QUERY_TIMEOUT_SECONDS
        )

        services: Dict[str, float] = {}

        for row in rows:
            service_name = (
                row.service_name or "Unknown"
            )

            services[service_name] = round(
                float(row.total_cost or 0),
                2,
            )

        return services

    def _build_billing_table_reference(self) -> str:
        """Build the fully-qualified BigQuery billing table name.

        Returns:
            str: project.dataset.table reference.

        Raises:
            ValueError: If billing configuration is incomplete.
        """
        table_name = config.BIGQUERY_BILLING_TABLE

        if not table_name:
            billing_account_id = (
                config.GCP_BILLING_ACCOUNT_ID
            )

            if not billing_account_id:
                return (
                    f"{config.GCP_PROJECT_ID}."
                    f"{config.BIGQUERY_BILLING_DATASET}."
                    "gcp_billing_export_resource_v1_UNKNOWN"
                )

            normalized_account_id = (
                billing_account_id.replace("-", "_")
            )

            table_name = (
                "gcp_billing_export_resource_v1_"
                f"{normalized_account_id}"
            )

        return (
            f"{config.GCP_PROJECT_ID}."
            f"{config.BIGQUERY_BILLING_DATASET}."
            f"{table_name}"
        )

    def _safe_table_reference(self) -> str:
        """Validate the BigQuery table reference before using it.

        BigQuery table identifiers cannot be passed as query parameters,
        therefore they are validated before being interpolated into SQL.

        Returns:
            str: Validated fully-qualified table reference.

        Raises:
            ValueError: If the table identifier contains unsafe characters.
        """
        table = self.billing_table

        allowed_characters = set(
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789"
            "._-"
        )

        if not table:
            raise ValueError(
                "BigQuery billing table is empty"
            )

        if any(
            character not in allowed_characters
            for character in table
        ):
            raise ValueError(
                "Invalid characters found in BigQuery table reference"
            )

        return table

    @staticmethod
    def _detect_currency(
        daily_costs: List[Dict[str, Any]],
    ) -> str:
        """Determine the billing currency from returned records.

        Args:
            daily_costs: Daily BigQuery billing records.

        Returns:
            str: Billing currency code.
        """
        currencies = {
            item.get(
                "currency",
                "UNKNOWN",
            )
            for item in daily_costs
        }

        if len(currencies) == 1:
            return next(iter(currencies))

        return "MIXED"

    def _mock_cost_data(
        self,
        source: str = "mock",
    ) -> Dict[str, Any]:
        """Generate deterministic billing data for demo mode.

        Args:
            source: Identifier describing why mock data was used.

        Returns:
            Dict[str, Any]: Seven-day demonstration billing dataset.
        """
        values = [
            142.50,
            147.25,
            139.80,
            151.20,
            146.75,
            153.40,
            149.90,
        ]

        daily_costs: List[Dict[str, Any]] = []

        for index, value in enumerate(values):
            current_date: date = (
                date.today()
                - timedelta(
                    days=6 - index
                )
            )

            daily_costs.append(
                {
                    "date": current_date.isoformat(),
                    "cost": value,
                    "cost_inr": value,
                    "currency": "INR",
                }
            )

        services: Dict[str, float] = {
            "Compute Engine": 620.50,
            "Google Kubernetes Engine": 210.75,
            "Cloud Storage": 74.20,
            "Cloud Monitoring": 38.50,
            "Other": 87.60,
        }

        seven_day_total = round(
            sum(values),
            2,
        )

        estimated_monthly_cost = round(
            seven_day_total / 7 * 30,
            2,
        )

        return {
            "source": source,
            "project_id": config.GCP_PROJECT_ID,
            "billing_table": self.billing_table,
            "currency": "INR",
            "daily_costs": daily_costs,
            "services": services,
            "seven_day_total_inr": seven_day_total,
            "estimated_monthly_cost_inr": (
                estimated_monthly_cost
            ),
        }