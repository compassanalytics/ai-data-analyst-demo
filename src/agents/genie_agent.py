"""Genie Data Agent - Wrapper for Databricks Genie Space API.

This module provides a high-level interface to interact with Databricks Genie Spaces
for natural language to SQL data analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from src.config import Config
from src.utils.errors import AgentError, classify_error


class QueryStatus(Enum):
    """Status of a Genie query."""
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class GenieResult:
    """Result from a Genie query.

    Attributes:
        success: Whether the query completed successfully
        data: The query results (list of dictionaries)
        sql: The generated SQL query
        description: Natural language description of results
        error: Error message if query failed
        columns: Column names in the result
        error_details: Structured error information for classification
    """
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    sql: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    columns: list[str] = field(default_factory=list)
    error_details: Optional[AgentError] = None

    @property
    def is_retryable(self) -> bool:
        """Check if the error is retryable.

        Returns:
            True if the error is retryable, False otherwise
        """
        if self.error_details is not None:
            return self.error_details.retryable
        return False

    def get_user_message(self) -> str:
        """Get a user-friendly error message.

        Returns:
            User-friendly message if error_details available, else raw error
        """
        if self.error_details is not None:
            return self.error_details.to_user_message()
        return self.error or "Unknown error"

    def to_markdown_table(self, max_rows: int = 10) -> str:
        """Convert results to a markdown table.

        Args:
            max_rows: Maximum number of rows to include

        Returns:
            Markdown formatted table string
        """
        if not self.data:
            return "_No results_"

        columns = self.columns or list(self.data[0].keys())

        # Header
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"

        # Rows
        rows = []
        for row in self.data[:max_rows]:
            row_values = [str(row.get(col, "")) for col in columns]
            rows.append("| " + " | ".join(row_values) + " |")

        result = "\n".join([header, separator] + rows)

        if len(self.data) > max_rows:
            result += f"\n\n_Showing {max_rows} of {len(self.data)} rows_"

        return result


class GenieDataAgent:
    """Agent for interacting with Databricks Genie Spaces.

    Provides natural language to SQL capabilities through the Genie API.
    Supports both real Genie API calls and mock mode for demos.

    Example:
        >>> config = Config(genie_space_id="abc123", mock_mode=False)
        >>> agent = GenieDataAgent(config)
        >>> result = agent.query("What are the top 10 products by revenue?")
        >>> print(result.to_markdown_table())
    """

    def __init__(self, config: Config):
        """Initialize the Genie Data Agent.

        Args:
            config: Configuration instance with Genie settings
        """
        self.config = config
        self._client = None
        self._conversation_id: Optional[str] = None

    @property
    def client(self):
        """Lazy-load the Databricks SDK client."""
        if self._client is None and not self.config.mock_mode:
            from databricks.sdk import WorkspaceClient

            # Initialize client (uses DATABRICKS_HOST and DATABRICKS_TOKEN from env,
            # or auto-authentication when running in Databricks)
            self._client = WorkspaceClient(
                host=self.config.databricks_host or None,
                token=self.config.databricks_token,
            )
        return self._client

    def query(
        self,
        question: str,
        timeout_seconds: int = 120,
        poll_interval: float = 2.0,
    ) -> GenieResult:
        """Query the Genie Space with a natural language question.

        Args:
            question: Natural language question about the data
            timeout_seconds: Maximum time to wait for query completion
            poll_interval: Seconds between status checks

        Returns:
            GenieResult with query results or error
        """
        if self.config.mock_mode:
            return self._mock_query(question)

        return self._real_query(question, timeout_seconds, poll_interval)

    def _real_query(
        self,
        question: str,
        timeout_seconds: int,
        poll_interval: float,
    ) -> GenieResult:
        """Execute a real query against the Genie API.

        Uses the SDK's built-in _and_wait methods for reliable polling.

        Args:
            question: Natural language question
            timeout_seconds: Maximum wait time (used by SDK internally)
            poll_interval: Polling interval (unused, SDK handles this)

        Returns:
            GenieResult with actual data from Genie
        """
        try:
            from datetime import timedelta
            from databricks.sdk.service.dashboards import GenieMessage

            genie = self.client.genie
            space_id = self.config.genie_space_id
            timeout_delta = timedelta(seconds=timeout_seconds)

            # Start a conversation or continue existing one
            if self._conversation_id is None:
                # Start new conversation and wait for completion
                response = genie.start_conversation_and_wait(
                    space_id=space_id,
                    content=question,
                    timeout=timeout_delta,
                )
                self._conversation_id = response.conversation_id
            else:
                # Continue existing conversation and wait for completion
                response = genie.create_message_and_wait(
                    space_id=space_id,
                    conversation_id=self._conversation_id,
                    content=question,
                    timeout=timeout_delta,
                )

            return self._parse_genie_response(response)

        except Exception as e:
            # Classify the error while the exception is intact
            classified_error = classify_error(
                e,
                context={"space_id": self.config.genie_space_id, "question": question},
            )
            return GenieResult(
                success=False,
                error=str(e),
                error_details=classified_error,
            )

    def _parse_genie_response(self, message_info: Any) -> GenieResult:
        """Parse the Genie API response into a GenieResult.

        Args:
            message_info: Response from Genie API (GenieMessage)

        Returns:
            Parsed GenieResult
        """
        try:
            # Extract attachments which contain query results and text
            attachments = getattr(message_info, "attachments", []) or []

            sql_query = None
            description = None
            text_content = None

            for attachment in attachments:
                # Check for query attachment (contains SQL)
                query_att = getattr(attachment, "query", None)
                if query_att:
                    sql_query = getattr(query_att, "query", None)
                    description = getattr(query_att, "description", None)

                # Check for text attachment (contains answer)
                text_att = getattr(attachment, "text", None)
                if text_att:
                    text_content = getattr(text_att, "content", None)

            # Use text content as description if we have it
            if text_content and not description:
                description = text_content

            # For now, we return the text answer as data display
            # The actual query results would require additional API call
            result_data = []
            columns = []

            if text_content:
                # Parse the text content to extract structured data if possible
                result_data = [{"answer": text_content}]
                columns = ["answer"]

            return GenieResult(
                success=True,
                data=result_data,
                sql=sql_query,
                description=description,
                columns=columns,
            )

        except Exception as e:
            return GenieResult(
                success=False,
                error=f"Failed to parse Genie response: {e}"
            )

    def _mock_query(self, question: str) -> GenieResult:
        """Return mock data for demonstration purposes.

        Args:
            question: The question (used to determine mock response)

        Returns:
            GenieResult with mock data
        """
        question_lower = question.lower()

        # Mock responses based on question patterns
        if "top" in question_lower and ("product" in question_lower or "revenue" in question_lower):
            return GenieResult(
                success=True,
                data=[
                    {"product_name": "Enterprise Suite", "revenue": 2450000, "units_sold": 245},
                    {"product_name": "Professional Plan", "revenue": 1820000, "units_sold": 910},
                    {"product_name": "Team Package", "revenue": 1560000, "units_sold": 1300},
                    {"product_name": "Starter Kit", "revenue": 980000, "units_sold": 1960},
                    {"product_name": "Basic Plan", "revenue": 750000, "units_sold": 2500},
                    {"product_name": "Premium Add-on", "revenue": 620000, "units_sold": 310},
                    {"product_name": "Support Package", "revenue": 540000, "units_sold": 540},
                    {"product_name": "Training Module", "revenue": 420000, "units_sold": 420},
                    {"product_name": "Integration API", "revenue": 380000, "units_sold": 190},
                    {"product_name": "Analytics Dashboard", "revenue": 350000, "units_sold": 175},
                ],
                sql="""SELECT
    product_name,
    SUM(revenue) as revenue,
    SUM(units_sold) as units_sold
FROM sales.products
GROUP BY product_name
ORDER BY revenue DESC
LIMIT 10""",
                description="Top 10 products ranked by total revenue",
                columns=["product_name", "revenue", "units_sold"],
            )

        elif "region" in question_lower or "breakdown" in question_lower:
            return GenieResult(
                success=True,
                data=[
                    {"region": "North America", "revenue": 4250000, "percentage": 42.5},
                    {"region": "Europe", "revenue": 2850000, "percentage": 28.5},
                    {"region": "Asia Pacific", "revenue": 1950000, "percentage": 19.5},
                    {"region": "Latin America", "revenue": 650000, "percentage": 6.5},
                    {"region": "Middle East & Africa", "revenue": 300000, "percentage": 3.0},
                ],
                sql="""SELECT
    region,
    SUM(revenue) as revenue,
    ROUND(SUM(revenue) * 100.0 / (SELECT SUM(revenue) FROM sales.regional), 1) as percentage
FROM sales.regional
GROUP BY region
ORDER BY revenue DESC""",
                description="Revenue breakdown by geographic region",
                columns=["region", "revenue", "percentage"],
            )

        elif "trend" in question_lower or "month" in question_lower or "time" in question_lower:
            return GenieResult(
                success=True,
                data=[
                    {"month": "2024-01", "revenue": 780000, "growth_pct": None},
                    {"month": "2024-02", "revenue": 820000, "growth_pct": 5.1},
                    {"month": "2024-03", "revenue": 910000, "growth_pct": 11.0},
                    {"month": "2024-04", "revenue": 875000, "growth_pct": -3.8},
                    {"month": "2024-05", "revenue": 950000, "growth_pct": 8.6},
                    {"month": "2024-06", "revenue": 1020000, "growth_pct": 7.4},
                ],
                sql="""SELECT
    DATE_FORMAT(sale_date, '%Y-%m') as month,
    SUM(revenue) as revenue,
    ROUND((SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY month)) * 100.0
          / LAG(SUM(revenue)) OVER (ORDER BY month), 1) as growth_pct
FROM sales.transactions
GROUP BY month
ORDER BY month""",
                description="Monthly revenue trend with growth percentage",
                columns=["month", "revenue", "growth_pct"],
            )

        elif "customer" in question_lower or "count" in question_lower:
            return GenieResult(
                success=True,
                data=[
                    {"segment": "Enterprise", "customer_count": 125, "avg_revenue": 45000},
                    {"segment": "Mid-Market", "customer_count": 450, "avg_revenue": 12000},
                    {"segment": "SMB", "customer_count": 2300, "avg_revenue": 2500},
                    {"segment": "Startup", "customer_count": 890, "avg_revenue": 1200},
                ],
                sql="""SELECT
    customer_segment as segment,
    COUNT(DISTINCT customer_id) as customer_count,
    ROUND(AVG(total_revenue), 0) as avg_revenue
FROM sales.customers
GROUP BY customer_segment
ORDER BY avg_revenue DESC""",
                description="Customer count and average revenue by segment",
                columns=["segment", "customer_count", "avg_revenue"],
            )

        else:
            # Generic mock response
            return GenieResult(
                success=True,
                data=[
                    {"metric": "Total Revenue", "value": 10000000},
                    {"metric": "Total Customers", "value": 3765},
                    {"metric": "Avg Order Value", "value": 2656},
                    {"metric": "YoY Growth", "value": 23.5},
                ],
                sql="""SELECT metric, value FROM analytics.summary_metrics""",
                description=f"Summary metrics for: {question}",
                columns=["metric", "value"],
            )

    def reset_conversation(self) -> None:
        """Reset the conversation state to start fresh."""
        self._conversation_id = None

    def get_conversation_id(self) -> Optional[str]:
        """Get the current conversation ID.

        Returns:
            Current conversation ID or None if no conversation started
        """
        return self._conversation_id
