"""Query Generator for the Genie Testing and Evaluation Framework.

This module provides test query generation based on failure categories
from genie_failure_scenarios.py. Generates structured test suites for
evaluating Genie's ability to handle various data quality challenges.
"""

from __future__ import annotations

from typing import Optional

from src.evaluation.models import (
    ComplexityLevel,
    FailureCategory,
    QueryType,
    TestQuery,
)


# =============================================================================
# QUERY TEMPLATES BY FAILURE CATEGORY
# =============================================================================

QUERY_TEMPLATES: dict[FailureCategory, list[dict]] = {
    # -------------------------------------------------------------------------
    # FAILURE CATEGORY 1: AMBIGUOUS COLUMN NAMES
    # -------------------------------------------------------------------------
    FailureCategory.AMBIGUOUS_COLUMNS: [
        {
            "question": "What was total revenue last month?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["revenue", "net_amount", "total"],
            "expected_tables": ["sales", "fact_sales", "transactions"],
            "description": "Tests handling of multiple revenue-like columns (net_amt, net_sales, REV, etc.)",
        },
        {
            "question": "Show me the sales amount by product",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["product", "sales", "amount"],
            "expected_tables": ["sales", "products"],
            "description": "Tests disambiguation between sales_amount, sale_amt, SALES columns",
        },
        {
            "question": "What is the total cost for each order?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["order", "cost", "total"],
            "expected_tables": ["orders", "order_items"],
            "description": "Tests cost vs cost_amount vs item_cost vs unit_cost disambiguation",
        },
        {
            "question": "Calculate the net value per transaction",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["transaction", "net", "value"],
            "expected_tables": ["transactions", "sales"],
            "description": "Tests net_value vs net_amount vs net_amt disambiguation",
        },
        {
            "question": "Show quantity sold by category",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["category", "quantity"],
            "expected_tables": ["sales", "products"],
            "description": "Tests qty vs quantity vs units_sold vs QTY disambiguation",
        },
        {
            "question": "What is the price for each item?",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["item", "price"],
            "expected_tables": ["products", "items"],
            "description": "Tests unit_price vs list_price vs price vs PRICE disambiguation",
        },
        {
            "question": "Show the date and amount for recent orders",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["date", "amount", "order"],
            "expected_tables": ["orders", "sales"],
            "description": "Tests order_date vs sale_date vs created_at and amount fields",
        },
    ],

    # -------------------------------------------------------------------------
    # FAILURE CATEGORY 2: CRYPTIC CODES/ABBREVIATIONS
    # -------------------------------------------------------------------------
    FailureCategory.CRYPTIC_CODES: [
        {
            "question": "Show sales by customer segment",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["segment", "sales"],
            "expected_tables": ["customers", "sales"],
            "description": "Tests if Genie can handle ENT/MID/SMB/IND codes",
        },
        {
            "question": "How many orders have status pending?",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["count", "status"],
            "expected_tables": ["orders"],
            "description": "Tests mapping 'pending' to numeric status codes (1,2,3,4,5)",
        },
        {
            "question": "What is the breakdown by sales channel?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["channel", "sales", "count"],
            "expected_tables": ["sales", "orders"],
            "description": "Tests understanding ON/OFF/EC channel codes",
        },
        {
            "question": "Show revenue by product category",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["category", "revenue"],
            "expected_tables": ["products", "sales"],
            "description": "Tests handling BER/CID/RTD/NAB category codes",
        },
        {
            "question": "Filter to enterprise customers only",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["customer"],
            "expected_tables": ["customers"],
            "description": "Tests mapping 'enterprise' to 'ENT' code",
        },
        {
            "question": "Show completed orders by type",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["type", "count", "orders"],
            "expected_tables": ["orders"],
            "description": "Tests mapping 'completed' status and numeric type codes",
        },
        {
            "question": "List customers in the mid-market segment",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["customer", "segment"],
            "expected_tables": ["customers"],
            "description": "Tests mapping 'mid-market' to 'MID' code",
        },
        {
            "question": "Show e-commerce sales trends",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["date", "sales", "channel"],
            "expected_tables": ["sales"],
            "description": "Tests mapping 'e-commerce' to 'EC' channel code",
        },
    ],

    # -------------------------------------------------------------------------
    # FAILURE CATEGORY 3: BUSINESS LOGIC
    # -------------------------------------------------------------------------
    FailureCategory.BUSINESS_LOGIC: [
        {
            "question": "What was Q1 revenue?",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["revenue", "quarter"],
            "expected_tables": ["sales", "dim_date"],
            "description": "Tests fiscal Q1 (Feb-Apr) vs calendar Q1 (Jan-Mar)",
        },
        {
            "question": "Show active customers only",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["customer"],
            "expected_tables": ["customers", "sales"],
            "description": "Tests definition of 'active' (90 days? status flag? not churned?)",
        },
        {
            "question": "What is our gross margin?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["margin", "revenue", "cost"],
            "expected_tables": ["sales", "costs"],
            "description": "Tests business formula: (Revenue - COGS) / Revenue",
        },
        {
            "question": "Show premium products",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["product", "tier", "category"],
            "expected_tables": ["products"],
            "description": "Tests definition of 'premium' (price? tier? category?)",
        },
        {
            "question": "Calculate customer lifetime value",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["customer", "ltv", "value"],
            "expected_tables": ["customers", "sales"],
            "description": "Tests complex CLV business calculation",
        },
        {
            "question": "Show high-value transactions",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["transaction", "value", "amount"],
            "expected_tables": ["transactions", "sales"],
            "description": "Tests threshold definition for 'high-value'",
        },
        {
            "question": "What is our net promoter score breakdown?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["nps", "score", "category"],
            "expected_tables": ["surveys", "customers"],
            "description": "Tests NPS calculation (promoters - detractors)",
        },
    ],

    # -------------------------------------------------------------------------
    # FAILURE CATEGORY 4: TEMPORAL CONFUSION
    # -------------------------------------------------------------------------
    FailureCategory.TEMPORAL_CONFUSION: [
        {
            "question": "Show last week's sales",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["sales", "date"],
            "expected_tables": ["sales"],
            "description": "Tests 'last week' (7 days? calendar week? business week?)",
        },
        {
            "question": "Compare YoY growth",
            "query_type": QueryType.COMPARISON,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["growth", "year", "revenue"],
            "expected_tables": ["sales", "dim_date"],
            "description": "Tests year-over-year calculation with proper period alignment",
        },
        {
            "question": "What were sales on 01/02/2024?",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["sales", "date"],
            "expected_tables": ["sales"],
            "description": "Tests date format interpretation (US vs EU)",
        },
        {
            "question": "Show this quarter's performance",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["quarter", "performance", "sales"],
            "expected_tables": ["sales"],
            "description": "Tests current quarter identification (fiscal vs calendar)",
        },
        {
            "question": "What were the monthly trends for last year?",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["month", "trend", "sales"],
            "expected_tables": ["sales"],
            "description": "Tests 'last year' (calendar? fiscal? trailing 12 months?)",
        },
        {
            "question": "Show week-over-week change",
            "query_type": QueryType.COMPARISON,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["week", "change", "sales"],
            "expected_tables": ["sales"],
            "description": "Tests WoW calculation with proper week boundaries",
        },
        {
            "question": "Sales for the current fiscal period",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["sales", "fiscal_period"],
            "expected_tables": ["sales", "dim_date"],
            "description": "Tests fiscal calendar awareness",
        },
        {
            "question": "Show data as of end of last month",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["data", "date"],
            "expected_tables": ["sales"],
            "description": "Tests point-in-time snapshot logic",
        },
    ],

    # -------------------------------------------------------------------------
    # FAILURE CATEGORY 5: AGGREGATION AMBIGUITY
    # -------------------------------------------------------------------------
    FailureCategory.AGGREGATION_AMBIGUITY: [
        {
            "question": "What is our average order value?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["average", "order", "value"],
            "expected_tables": ["orders", "sales"],
            "description": "Tests AVG(line_item) vs SUM/COUNT(DISTINCT order) aggregation",
        },
        {
            "question": "How many customers bought Product X?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["count", "customer"],
            "expected_tables": ["sales", "customers"],
            "description": "Tests COUNT vs COUNT(DISTINCT customer_id)",
        },
        {
            "question": "What is our customer retention rate?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["retention", "rate", "customers"],
            "expected_tables": ["customers", "sales"],
            "description": "Tests cohort-based retention calculation",
        },
        {
            "question": "Show average items per order",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["average", "items", "order"],
            "expected_tables": ["orders", "order_items"],
            "description": "Tests SUM(items)/COUNT(DISTINCT order_id) aggregation",
        },
        {
            "question": "Calculate repeat purchase rate",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["repeat", "rate", "customers"],
            "expected_tables": ["sales", "customers"],
            "description": "Tests customers with multiple orders / total customers",
        },
        {
            "question": "What is the median order value?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["median", "order", "value"],
            "expected_tables": ["orders"],
            "description": "Tests PERCENTILE_CONT vs approximation methods",
        },
        {
            "question": "Show unique visitors per day",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["visitors", "day", "unique"],
            "expected_tables": ["visits", "sessions"],
            "description": "Tests COUNT(DISTINCT visitor_id) grouping",
        },
    ],

    # -------------------------------------------------------------------------
    # FAILURE CATEGORY 6: JOIN COMPLEXITY
    # -------------------------------------------------------------------------
    FailureCategory.JOIN_COMPLEXITY: [
        {
            "question": "Which products have never been sold?",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["product"],
            "expected_tables": ["products", "sales"],
            "description": "Tests LEFT JOIN + NULL check pattern",
        },
        {
            "question": "Show customers who bought in Q1 but not Q2",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["customer"],
            "expected_tables": ["customers", "sales"],
            "description": "Tests set difference / NOT EXISTS / EXCEPT pattern",
        },
        {
            "question": "Top customers by total spend across all orders",
            "query_type": QueryType.RANKING,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["customer", "spend", "total"],
            "expected_tables": ["customers", "orders", "sales"],
            "description": "Tests proper grouping with joins",
        },
        {
            "question": "Products sold in all regions",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["product"],
            "expected_tables": ["products", "sales", "regions"],
            "description": "Tests relational division pattern",
        },
        {
            "question": "Customers without any orders this year",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["customer"],
            "expected_tables": ["customers", "orders"],
            "description": "Tests anti-join with temporal filter",
        },
        {
            "question": "Show supplier performance with product details",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["supplier", "product", "performance"],
            "expected_tables": ["suppliers", "products", "sales"],
            "description": "Tests multi-table join paths",
        },
        {
            "question": "Orders with all items from the same category",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["order", "category"],
            "expected_tables": ["orders", "order_items", "products"],
            "description": "Tests grouped having clause with joins",
        },
        {
            "question": "Find matching records between sales and returns",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["sale", "return", "match"],
            "expected_tables": ["sales", "returns"],
            "description": "Tests proper join conditions for matching",
        },
    ],
}


class QueryGenerator:
    """Generator for test query suites.

    Generates structured test queries for evaluating Genie's ability to handle
    various data quality challenges based on failure categories.

    Example:
        >>> generator = QueryGenerator()
        >>> suite = generator.generate_suite(
        ...     query_types=[QueryType.AGGREGATION],
        ...     complexity_levels=[ComplexityLevel.SIMPLE],
        ... )
        >>> print(len(suite))
    """

    def __init__(self) -> None:
        """Initialize the query generator."""
        self._templates = QUERY_TEMPLATES
        self._id_counter = 0

    def _generate_id(self, category: FailureCategory, index: int) -> str:
        """Generate a unique ID for a test query.

        Args:
            category: The failure category
            index: Index within the category

        Returns:
            Unique string ID
        """
        return f"{category.value}_{index:03d}"

    def generate_suite(
        self,
        query_types: Optional[list[QueryType]] = None,
        complexity_levels: Optional[list[ComplexityLevel]] = None,
        failure_categories: Optional[list[FailureCategory]] = None,
        adversarial: bool = False,
    ) -> list[TestQuery]:
        """Generate a test suite based on filters.

        Args:
            query_types: Filter to specific query types (None = all)
            complexity_levels: Filter to specific complexity levels (None = all)
            failure_categories: Filter to specific failure categories (None = all)
            adversarial: If True, mark all queries as adversarial test cases

        Returns:
            List of TestQuery objects matching the filters
        """
        result: list[TestQuery] = []

        # Use all categories if not specified
        categories = failure_categories or list(FailureCategory)

        for category in categories:
            templates = self._templates.get(category, [])

            for idx, template in enumerate(templates):
                # Apply query type filter
                if query_types and template["query_type"] not in query_types:
                    continue

                # Apply complexity filter
                if complexity_levels and template["complexity"] not in complexity_levels:
                    continue

                # Create TestQuery
                test_query = TestQuery(
                    id=self._generate_id(category, idx),
                    question=template["question"],
                    query_type=template["query_type"],
                    complexity=template["complexity"],
                    failure_category=category,
                    expected_columns=template.get("expected_columns", []),
                    expected_tables=template.get("expected_tables", []),
                    description=template.get("description", ""),
                    is_adversarial=adversarial,
                )

                result.append(test_query)

        return result

    def get_queries_by_category(
        self,
        category: FailureCategory,
    ) -> list[TestQuery]:
        """Get all queries for a specific failure category.

        Args:
            category: The failure category to get queries for

        Returns:
            List of TestQuery objects for the category
        """
        return self.generate_suite(failure_categories=[category])

    def get_queries_by_type(
        self,
        query_type: QueryType,
    ) -> list[TestQuery]:
        """Get all queries of a specific type.

        Args:
            query_type: The query type to filter by

        Returns:
            List of TestQuery objects of the specified type
        """
        return self.generate_suite(query_types=[query_type])

    def get_queries_by_complexity(
        self,
        complexity: ComplexityLevel,
    ) -> list[TestQuery]:
        """Get all queries of a specific complexity level.

        Args:
            complexity: The complexity level to filter by

        Returns:
            List of TestQuery objects of the specified complexity
        """
        return self.generate_suite(complexity_levels=[complexity])

    def get_all_queries(self) -> list[TestQuery]:
        """Get all available test queries.

        Returns:
            List of all TestQuery objects
        """
        return self.generate_suite()

    def get_summary(self) -> dict[str, int]:
        """Get a summary of available queries.

        Returns:
            Dictionary with counts by category, type, and complexity
        """
        all_queries = self.get_all_queries()

        summary = {
            "total": len(all_queries),
            "by_category": {},
            "by_type": {},
            "by_complexity": {},
        }

        for query in all_queries:
            # Count by category
            cat_key = query.failure_category.value
            summary["by_category"][cat_key] = summary["by_category"].get(cat_key, 0) + 1

            # Count by type
            type_key = query.query_type.value
            summary["by_type"][type_key] = summary["by_type"].get(type_key, 0) + 1

            # Count by complexity
            comp_key = query.complexity.value
            summary["by_complexity"][comp_key] = summary["by_complexity"].get(comp_key, 0) + 1

        return summary
