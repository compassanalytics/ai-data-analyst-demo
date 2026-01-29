"""LLM-powered query generator for the benchmark system.

This module generates domain-specific test queries using an LLM
based on schema context. Supports multiple providers via LiteLLM:
- Anthropic (Claude)
- OpenAI (GPT-4)
- Databricks Foundation Models

Supports mock mode for testing without LLM API access.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import Config
from src.evaluation.models import ComplexityLevel, FailureCategory, QueryType

from .llm_client import create_llm_client
from .models import BenchmarkQuery, Severity
from .schema_parser import DomainContext

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPT TEMPLATE
# =============================================================================

QUERY_GENERATION_SYSTEM_PROMPT = """You are an expert at generating test queries for evaluating AI data assistants like Databricks Genie.

Given a database schema and domain context, generate natural language questions that test specific failure scenarios.

Each query should:
1. Be realistic for the domain
2. Target the specified failure category
3. Include expected columns and tables that should appear in the SQL
4. Vary in complexity

IMPORTANT: Output ONLY valid JSON, no other text.

Output Format:
{
    "queries": [
        {
            "question": "Natural language question",
            "query_type": "aggregation|filter|join|temporal|ranking|comparison",
            "complexity": "simple|moderate|complex|expert",
            "expected_columns": ["col1", "col2"],
            "expected_tables": ["table1"],
            "description": "What this query tests",
            "expected_failure": "How AI might fail on this",
            "severity": "low|medium|high|critical"
        }
    ]
}
"""


# =============================================================================
# FAILURE CATEGORY PROMPTS
# =============================================================================

FAILURE_CATEGORY_PROMPTS: dict[FailureCategory, str] = {
    FailureCategory.AMBIGUOUS_COLUMNS: """Generate queries that test handling of AMBIGUOUS COLUMN NAMES.

Focus on scenarios where:
- Multiple columns have similar names (e.g., net_amt, net_sales, REV, revenue)
- Column naming is inconsistent (e.g., sales_amount vs sale_amt vs SALES)
- There are synonymous columns across tables (e.g., cost, item_cost, unit_cost)
- Abbreviations make intent unclear (e.g., qty vs quantity, amt vs amount)

The AI assistant might pick the wrong column or fail to disambiguate between options.
Generate questions that would naturally refer to these ambiguous concepts.""",
    FailureCategory.CRYPTIC_CODES: """Generate queries that test handling of CRYPTIC CODES, abbreviations, and synonyms.

CRITICAL: Only test codes and values that ACTUALLY EXIST in this schema.
Check the "Valid Column Values" section above for the exact values available.

Focus on scenarios where:
- Users use abbreviations that need mapping to actual column values
  (e.g., "CPO cars" -> condition = 'Certified Pre-Owned')
- Users use synonyms that need translation
  (e.g., "financed deals" -> payment_method = 'Financing')
- Case sensitivity might cause issues
  (e.g., "COMPLETED orders" -> status = 'Completed')
- Users describe values differently than stored
  (e.g., "paid in full" -> payment_method = 'Cash')

DO NOT generate queries for:
- Columns that don't exist in the schema (no channel, segment, category, type unless listed)
- Numeric codes if the column uses text values
- Values not listed in the Valid Column Values section

The AI assistant might fail to map user terminology to actual column values.
Generate questions using natural language synonyms for existing values.""",
    FailureCategory.BUSINESS_LOGIC: """Generate queries that test understanding of BUSINESS LOGIC and domain rules.

Focus on scenarios where:
- Fiscal vs calendar year definitions differ
- Business definitions need domain knowledge (e.g., "active customer" = last 90 days)
- Calculated metrics require specific formulas (e.g., gross margin, NPS, CLV)
- Thresholds define categories (e.g., "premium" products, "high-value" transactions)
- Custom business rules apply (e.g., specific discount calculations)

The AI assistant might use incorrect formulas or misinterpret business terminology.
Generate questions that require specific business logic to answer correctly.""",
    FailureCategory.TEMPORAL_CONFUSION: """Generate queries that test handling of TEMPORAL/DATE concepts.

Focus on scenarios where:
- "Last week" could mean 7 days, calendar week, or business week
- Date formats are ambiguous (01/02/2024 - US vs EU)
- Fiscal periods differ from calendar periods
- Relative dates need context ("this quarter", "last month", "YTD")
- Point-in-time vs period calculations matter
- Time zone considerations affect results

The AI assistant might use wrong date boundaries or interpret periods incorrectly.
Generate questions with time-based requirements that could be misinterpreted.""",
    FailureCategory.AGGREGATION_AMBIGUITY: """Generate queries that test AGGREGATION logic and calculations.

Focus on scenarios where:
- AVG might be per-row vs per-order/customer
- COUNT vs COUNT(DISTINCT) matters for correct results
- SUM needs proper grouping to avoid double-counting
- Ratios require careful numerator/denominator definitions
- Percentiles vs averages yield different insights
- Weighted vs unweighted averages apply

The AI assistant might use wrong aggregation functions or improper grouping.
Generate questions about averages, counts, rates, and ratios that need precise definitions.""",
    FailureCategory.JOIN_COMPLEXITY: """Generate queries that test complex JOIN scenarios.

Focus on scenarios where:
- Anti-joins find "customers who didn't buy" or "products never sold"
- Set differences need EXCEPT or NOT EXISTS (e.g., "Q1 but not Q2")
- Relational division finds entities matching all criteria
- Multi-hop joins traverse 3+ tables with potential fan-out
- Self-joins compare records within the same table
- Left/right outer joins affect result completeness

The AI assistant might use wrong join types or produce Cartesian products.
Generate questions that require specific join patterns to answer correctly.""",
    FailureCategory.TRICK_QUESTIONS: """Generate ADVERSARIAL / TRICK QUESTIONS that test whether the AI appropriately refuses or indicates uncertainty.

These queries are designed to have NO valid SQL answer. The correct response is "I don't know" or "This data is not available."

Focus on 5 subcategories:

1. **IMPOSSIBLE QUERIES** - Ask about data that doesn't exist in the schema:
   - Weather/climate data (no weather tables exist)
   - Employee HR data (salary, benefits, PTO - only basic salesperson info exists)
   - Customer reviews/star ratings (only service_orders.customer_rating exists for service)
   - Competitor pricing or market share
   - Marketing campaign data or ad spend

2. **AMBIGUOUS PRONOUNS** - Use unclear references:
   - "What were their sales last month?" (whose sales?)
   - "Show the other customers" (other than what?)
   - "Compare it to the previous one" (what to what?)

3. **MISLEADING ASSUMPTIONS** - Presuppose facts that aren't true:
   - "Why did sales drop in March?" (assumes sales dropped)
   - "Show the 10 stores in California" (assumes stores exist)
   - "What is our refund policy impact?" (assumes refund tracking exists)

4. **CROSS-DOMAIN CONFUSION** - Ask about wrong domain concepts:
   - Ask medical questions about automotive data
   - Ask about flight schedules or hotel bookings
   - Ask about streaming subscriptions

5. **CALCULATION TRAPS** - Request metrics requiring missing data:
   - Market share (no competitor data)
   - Weather-adjusted sales (no weather data)
   - ROI by marketing channel (no marketing data)

IMPORTANT: For trick questions, do NOT require using schema tables. These should reference data that DOES NOT EXIST.
All generated queries should have:
- expected_columns: [] (empty)
- expected_tables: [] (empty)

The AI should recognize these as unanswerable and NOT generate SQL.""",
}


# =============================================================================
# COMPLEXITY TIER PROMPTS
# =============================================================================

COMPLEXITY_TIER_PROMPTS: dict[ComplexityLevel, str] = {
    ComplexityLevel.SIMPLE: """Generate queries at SIMPLE complexity level.
Characteristics:
- Single table queries only
- Basic filters using WHERE clause
- Simple aggregations: COUNT, SUM, AVG
- No joins or subqueries
- Direct column references

Examples: "How many orders do we have?", "What is the total revenue?", "Show all products".""",
    ComplexityLevel.MODERATE: """Generate queries at MODERATE complexity level.
Characteristics:
- 2 tables with JOIN (INNER, LEFT, RIGHT)
- GROUP BY with HAVING clauses
- Multiple filter conditions (AND/OR)
- Date comparisons and ranges
- Basic sorting with ORDER BY and LIMIT

Examples: "Show sales by region last month", "Top 10 customers by revenue", "Products with sales above average".""",
    ComplexityLevel.COMPLEX: """Generate queries at COMPLEX complexity level.
Characteristics:
- 3+ tables with multiple joins
- Subqueries (scalar, correlated, EXISTS)
- Date functions: DATE_TRUNC, DATEDIFF, DATE_ADD
- CASE expressions for conditional logic
- Multiple aggregation levels
- UNION/INTERSECT/EXCEPT set operations

Examples: "Year-over-year growth by category", "Customers who bought in Q1 but not Q2", "Revenue contribution % by segment".""",
    ComplexityLevel.EXPERT: """Generate queries at EXPERT complexity level.
Characteristics:
- Common Table Expressions (CTEs) - WITH clauses
- Window functions: ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD
- PARTITION BY for advanced analytics
- Running totals and moving averages
- Complex business logic with nested aggregations
- Self-joins for hierarchical or sequential data
- Pivoting/unpivoting patterns

Examples: "Rank customers by monthly spend with running totals", "Month-over-month change with LAG", "Top 3 products per category using ROW_NUMBER".""",
}


# =============================================================================
# MOCK QUERY TEMPLATES
# =============================================================================

MOCK_QUERY_TEMPLATES: dict[FailureCategory, list[dict[str, Any]]] = {
    FailureCategory.AMBIGUOUS_COLUMNS: [
        {
            "question": "What was the total revenue last month?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["revenue", "amount"],
            "expected_tables": ["sales"],
            "description": "Tests disambiguation of revenue-like columns",
            "expected_failure": "May select wrong revenue column",
            "severity": Severity.MEDIUM,
        },
        {
            "question": "Show sales amount by product category",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["category", "amount", "sales"],
            "expected_tables": ["sales", "products"],
            "description": "Tests sales_amount vs sale_amt disambiguation",
            "expected_failure": "May use inconsistent amount columns",
            "severity": Severity.MEDIUM,
        },
        {
            "question": "Rank products by revenue contribution with running total percentage",
            "query_type": QueryType.RANKING,
            "complexity": ComplexityLevel.EXPERT,
            "expected_columns": ["product", "revenue", "rank", "running_total_pct"],
            "expected_tables": ["sales", "products"],
            "description": "Tests window functions with ambiguous revenue columns",
            "expected_failure": "May use wrong revenue column in SUM OVER",
            "severity": Severity.HIGH,
        },
    ],
    FailureCategory.CRYPTIC_CODES: [
        {
            "question": "Show sales by customer segment",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["segment", "sales"],
            "expected_tables": ["customers", "sales"],
            "description": "Tests ENT/MID/SMB code interpretation",
            "expected_failure": "May not translate segment names to codes",
            "severity": Severity.HIGH,
        },
        {
            "question": "How many orders are pending?",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["status", "count"],
            "expected_tables": ["orders"],
            "description": "Tests numeric status code mapping",
            "expected_failure": "May not know pending = status code 1",
            "severity": Severity.HIGH,
        },
        {
            "question": "Show top 3 products per segment with dense ranking",
            "query_type": QueryType.RANKING,
            "complexity": ComplexityLevel.EXPERT,
            "expected_columns": ["segment", "product", "sales", "rank"],
            "expected_tables": ["customers", "sales", "products"],
            "description": "Tests DENSE_RANK with segment code partitioning",
            "expected_failure": "May not map segment names to codes in PARTITION BY",
            "severity": Severity.CRITICAL,
        },
    ],
    FailureCategory.BUSINESS_LOGIC: [
        {
            "question": "What was our Q1 revenue?",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["revenue", "quarter"],
            "expected_tables": ["sales"],
            "description": "Tests fiscal vs calendar Q1 definition",
            "expected_failure": "May use calendar Q1 instead of fiscal",
            "severity": Severity.HIGH,
        },
        {
            "question": "Calculate the gross margin",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["revenue", "cost", "margin"],
            "expected_tables": ["sales"],
            "description": "Tests (Revenue-COGS)/Revenue formula",
            "expected_failure": "May use incorrect margin formula",
            "severity": Severity.CRITICAL,
        },
        {
            "question": "Calculate rolling 3-month average gross margin with LAG comparison",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.EXPERT,
            "expected_columns": ["month", "margin", "rolling_avg", "prev_margin"],
            "expected_tables": ["sales"],
            "description": "Tests moving average with LAG and business logic formula",
            "expected_failure": "May use wrong margin formula in window function",
            "severity": Severity.CRITICAL,
        },
    ],
    FailureCategory.TEMPORAL_CONFUSION: [
        {
            "question": "Show last week's sales",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["date", "sales"],
            "expected_tables": ["sales"],
            "description": "Tests 'last week' interpretation",
            "expected_failure": "May use wrong week boundaries",
            "severity": Severity.MEDIUM,
        },
        {
            "question": "Compare year-over-year growth",
            "query_type": QueryType.COMPARISON,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["year", "growth", "revenue"],
            "expected_tables": ["sales"],
            "description": "Tests YoY calculation alignment",
            "expected_failure": "May not align comparison periods",
            "severity": Severity.HIGH,
        },
        {
            "question": "Show month-over-month revenue change using LAG for each fiscal quarter",
            "query_type": QueryType.TEMPORAL,
            "complexity": ComplexityLevel.EXPERT,
            "expected_columns": ["month", "quarter", "revenue", "prev_revenue", "change_pct"],
            "expected_tables": ["sales"],
            "description": "Tests LAG window function with fiscal quarter partitioning",
            "expected_failure": "May use calendar quarters or wrong LAG offset",
            "severity": Severity.CRITICAL,
        },
    ],
    FailureCategory.AGGREGATION_AMBIGUITY: [
        {
            "question": "What is the average order value?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": ["order", "average", "value"],
            "expected_tables": ["orders", "order_items"],
            "description": "Tests AVG per-row vs per-order",
            "expected_failure": "May calculate AVG of line items not orders",
            "severity": Severity.HIGH,
        },
        {
            "question": "How many unique customers purchased?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": ["customer", "count"],
            "expected_tables": ["sales", "customers"],
            "description": "Tests COUNT vs COUNT DISTINCT",
            "expected_failure": "May use COUNT instead of COUNT DISTINCT",
            "severity": Severity.MEDIUM,
        },
        {
            "question": "Show customer running total orders and cumulative spend percentile",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.EXPERT,
            "expected_columns": ["customer", "orders", "running_total", "percentile"],
            "expected_tables": ["orders", "customers"],
            "description": "Tests window functions with proper order-level aggregation",
            "expected_failure": "May aggregate at wrong level before window function",
            "severity": Severity.CRITICAL,
        },
    ],
    FailureCategory.JOIN_COMPLEXITY: [
        {
            "question": "Which products have never been sold?",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["product"],
            "expected_tables": ["products", "sales"],
            "description": "Tests LEFT JOIN + NULL pattern",
            "expected_failure": "May use INNER JOIN missing unsold products",
            "severity": Severity.HIGH,
        },
        {
            "question": "Customers who bought in Q1 but not Q2",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": ["customer"],
            "expected_tables": ["customers", "sales"],
            "description": "Tests set difference pattern",
            "expected_failure": "May not correctly exclude Q2 customers",
            "severity": Severity.CRITICAL,
        },
        {
            "question": "Rank customers by category spend using CTE and show top 3 per category",
            "query_type": QueryType.JOIN,
            "complexity": ComplexityLevel.EXPERT,
            "expected_columns": ["category", "customer", "spend", "rank"],
            "expected_tables": ["customers", "sales", "products"],
            "description": "Tests CTE with ROW_NUMBER across multiple joins",
            "expected_failure": "May create Cartesian product or use wrong ranking",
            "severity": Severity.CRITICAL,
        },
    ],
    FailureCategory.TRICK_QUESTIONS: [
        # Subcategory 1: Impossible queries
        {
            "question": "How did weather affect our vehicle sales last quarter?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "IMPOSSIBLE: No weather data exists in the schema",
            "expected_failure": "Appropriate refusal - no weather data available",
            "severity": Severity.HIGH,
        },
        {
            "question": "What is the average employee salary by department?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "IMPOSSIBLE: No HR/salary data exists - only basic salesperson info",
            "expected_failure": "Appropriate refusal - no salary data available",
            "severity": Severity.HIGH,
        },
        # Subcategory 2: Ambiguous pronouns
        {
            "question": "What were their sales last month?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "AMBIGUOUS: 'their' has no clear referent - whose sales?",
            "expected_failure": "Appropriate clarification request - ambiguous pronoun",
            "severity": Severity.MEDIUM,
        },
        {
            "question": "Compare it to the previous period",
            "query_type": QueryType.COMPARISON,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "AMBIGUOUS: 'it' and 'previous period' have no clear referent",
            "expected_failure": "Appropriate clarification request - ambiguous reference",
            "severity": Severity.MEDIUM,
        },
        # Subcategory 3: Misleading assumptions
        {
            "question": "Why did our customer satisfaction score drop in Q2?",
            "query_type": QueryType.FILTER,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "MISLEADING: Presupposes satisfaction dropped - may not be true",
            "expected_failure": "Appropriate challenge of assumption or data verification",
            "severity": Severity.HIGH,
        },
        {
            "question": "Show me the refund rate by product category",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.MODERATE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "MISLEADING: Assumes refund tracking exists - no refund data in schema",
            "expected_failure": "Appropriate refusal - no refund data available",
            "severity": Severity.HIGH,
        },
        # Subcategory 4: Cross-domain confusion
        {
            "question": "What is the average patient wait time by department?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "CROSS-DOMAIN: Medical/healthcare question for automotive data",
            "expected_failure": "Appropriate domain mismatch indication",
            "severity": Severity.HIGH,
        },
        {
            "question": "Show flight bookings by destination for last month",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.SIMPLE,
            "expected_columns": [],
            "expected_tables": [],
            "description": "CROSS-DOMAIN: Travel/airline question for automotive data",
            "expected_failure": "Appropriate domain mismatch indication",
            "severity": Severity.HIGH,
        },
        # Subcategory 5: Calculation traps
        {
            "question": "What is our market share compared to competitors?",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": [],
            "expected_tables": [],
            "description": "CALCULATION TRAP: Requires competitor data which doesn't exist",
            "expected_failure": "Appropriate refusal - no competitor data available",
            "severity": Severity.CRITICAL,
        },
        {
            "question": "Calculate ROI for each marketing campaign",
            "query_type": QueryType.AGGREGATION,
            "complexity": ComplexityLevel.COMPLEX,
            "expected_columns": [],
            "expected_tables": [],
            "description": "CALCULATION TRAP: No marketing campaign data exists in schema",
            "expected_failure": "Appropriate refusal - no marketing data available",
            "severity": Severity.CRITICAL,
        },
    ],
}


# =============================================================================
# LLM QUERY GENERATOR
# =============================================================================


@dataclass
class GenerationMetadata:
    """Metadata about a query generation session."""

    model_name: str
    temperature: float
    prompt_hash: str
    generated_at: str
    domain_name: str
    schema_version: str
    queries_requested: int
    queries_generated: int
    failure_categories: list[str]
    validation_errors: list[str] = field(default_factory=list)


class LLMQueryGenerator:
    """Generate benchmark queries using LLM.

    Supports multiple LLM providers via LiteLLM:
    - Anthropic (Claude) - recommended for best schema understanding
    - OpenAI (GPT-4)
    - Databricks Foundation Models

    Example:
        >>> config = Config.from_env()
        >>> generator = LLMQueryGenerator(config)
        >>> queries = generator.generate(domain_context, queries_per_category=5)
    """

    # Default to Claude for better schema understanding
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, config: Config, model: str | None = None, provider: str = "litellm"):
        """Initialize the LLM query generator.

        Args:
            config: Configuration instance with model settings
            model: Model identifier (defaults to Claude 3.5 Sonnet)
            provider: LLM provider - "litellm" (default) or "databricks"
        """
        self.config = config
        self._llm = None
        self._litellm_client = None
        self._temperature = 0.3  # Lower for more deterministic generation
        self._model = model or os.getenv("LLM_MODEL", self.DEFAULT_MODEL)
        self._provider = provider

    @property
    def llm(self):
        """Lazy-load LLM client based on provider.

        Uses LiteLLM for multi-provider support, or Databricks directly.
        """
        if self._llm is None and not self.config.mock_mode:
            if self._provider == "databricks":
                # Use Databricks directly
                from databricks_langchain import ChatDatabricks

                self._llm = ChatDatabricks(
                    endpoint=self.config.model_endpoint,
                    temperature=self._temperature,
                )
            else:
                # Use LiteLLM for flexible model access
                self._litellm_client = create_llm_client(
                    provider="litellm",
                    model=self._model,
                    temperature=self._temperature,
                )
                # Create a wrapper that matches the ChatDatabricks interface
                self._llm = self._create_litellm_wrapper()
        return self._llm

    def _create_litellm_wrapper(self):
        """Create a wrapper that provides invoke() with LangChain message support."""

        class LiteLLMWrapper:
            def __init__(wrapper_self, client):
                wrapper_self.client = client

            def invoke(wrapper_self, messages):
                """Invoke the LLM with LangChain-style messages."""
                # Convert LangChain messages to dict format
                msg_dicts = []
                for msg in messages:
                    if hasattr(msg, "type"):
                        role = "system" if msg.type == "system" else "user"
                    else:
                        role = "user"
                    msg_dicts.append({"role": role, "content": msg.content})

                response = wrapper_self.client.invoke(msg_dicts)

                # Return an object with .content attribute
                class Response:
                    def __init__(self, content):
                        self.content = content

                return Response(response.content)

        return LiteLLMWrapper(self._litellm_client)

    def generate(
        self,
        domain_context: DomainContext,
        failure_categories: list[FailureCategory] | None = None,
        complexity_tiers: list[ComplexityLevel] | None = None,
        queries_per_category: int = 5,
        seed: int | None = None,
        schema_version: str = "",
    ) -> list[BenchmarkQuery]:
        """Generate benchmark queries for the domain.

        Args:
            domain_context: Schema context with table/column information
            failure_categories: Categories to generate for (None = all)
            complexity_tiers: Complexity tiers to generate for (None = all)
            queries_per_category: Number of queries per category
            seed: Random seed for reproducibility (used in mock mode)
            schema_version: Version of the schema (optional, for provenance)

        Returns:
            List of generated BenchmarkQuery objects
        """
        if self.config.mock_mode:
            return self._mock_generate(
                domain_context,
                failure_categories,
                complexity_tiers,
                queries_per_category,
                seed,
                schema_version=schema_version,
            )
        return self._llm_generate(
            domain_context, failure_categories, complexity_tiers, queries_per_category, schema_version=schema_version
        )

    def _llm_generate(
        self,
        domain_context: DomainContext,
        failure_categories: list[FailureCategory] | None,
        complexity_tiers: list[ComplexityLevel] | None,
        queries_per_category: int,
        schema_version: str = "",
    ) -> list[BenchmarkQuery]:
        """Generate queries using LLM.

        Args:
            domain_context: Schema context with table/column information
            failure_categories: Categories to generate for (None = all)
            complexity_tiers: Complexity tiers to generate for (None = all)
            queries_per_category: Number of queries per category
            schema_version: Version of the schema (optional)

        Returns:
            List of generated BenchmarkQuery objects
        """
        categories = failure_categories or list(FailureCategory)
        all_queries: list[BenchmarkQuery] = []
        timestamp = datetime.now().isoformat()

        for category in categories:
            try:
                queries = self._generate_for_category(
                    domain_context=domain_context,
                    category=category,
                    complexity_tiers=complexity_tiers,
                    count=queries_per_category,
                    timestamp=timestamp,
                    schema_version=schema_version,
                )
                all_queries.extend(queries)
                logger.info(f"Generated {len(queries)} queries for {category.value}")
            except Exception as e:
                logger.error(f"Failed to generate queries for {category.value}: {e}")
                # Continue with other categories

        return all_queries

    def _generate_for_category(
        self,
        domain_context: DomainContext,
        category: FailureCategory,
        complexity_tiers: list[ComplexityLevel] | None,
        count: int,
        timestamp: str,
        schema_version: str = "",
    ) -> list[BenchmarkQuery]:
        """Generate queries for a single failure category.

        Args:
            domain_context: Schema context
            category: The failure category to target
            complexity_tiers: Complexity tiers to generate for (None = all)
            count: Number of queries to generate
            timestamp: Generation timestamp for provenance
            schema_version: Version of the schema (optional)

        Returns:
            List of BenchmarkQuery objects for this category
        """
        llm = self.llm
        if llm is None:
            logger.warning("LLM not available, falling back to mock")
            return []

        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(domain_context, category, count, complexity_tiers)

        # Calculate prompt hash for provenance
        prompt_content = system_prompt + user_prompt
        prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()[:16]

        # Invoke LLM
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        # Parse response
        query_dicts = self._parse_llm_response(response.content)

        # Convert to BenchmarkQuery objects
        queries: list[BenchmarkQuery] = []
        for idx, query_dict in enumerate(query_dicts):
            if self._validate_query(query_dict, domain_context):
                query = self._dict_to_benchmark_query(
                    query_dict=query_dict,
                    category=category,
                    domain_context=domain_context,
                    index=idx,
                    timestamp=timestamp,
                    prompt_hash=prompt_hash,
                    schema_version=schema_version,
                )
                queries.append(query)
            else:
                logger.warning(f"Skipping invalid query: {query_dict.get('question', 'unknown')}")

        return queries

    def _build_system_prompt(self) -> str:
        """Build system prompt for query generation.

        Returns:
            System prompt string
        """
        return QUERY_GENERATION_SYSTEM_PROMPT

    def _build_user_prompt(
        self,
        domain_context: DomainContext,
        category: FailureCategory,
        count: int,
        complexity_tiers: list[ComplexityLevel] | None = None,
    ) -> str:
        """Build user prompt with schema context.

        Args:
            domain_context: Schema context with table/column information
            category: The failure category to target
            count: Number of queries to generate
            complexity_tiers: Complexity tiers to generate for (None = all)

        Returns:
            User prompt string
        """
        # Get category-specific instructions
        category_instructions = FAILURE_CATEGORY_PROMPTS.get(
            category, f"Generate queries that test {category.value.replace('_', ' ')} scenarios."
        )

        # Get schema context from domain
        schema_context = domain_context.to_prompt_context()

        # Build complexity instructions
        if complexity_tiers:
            tier_instructions_parts = []
            for tier in complexity_tiers:
                tier_prompt = COMPLEXITY_TIER_PROMPTS.get(tier)
                if tier_prompt:
                    tier_instructions_parts.append(tier_prompt)
            complexity_instruction = "\n\n".join(tier_instructions_parts)
            complexity_requirement = (
                f"5. Generate queries ONLY at these complexity levels: {', '.join(t.value for t in complexity_tiers)}"
            )
        else:
            complexity_instruction = ""
            complexity_requirement = "4. Have varying complexity (mix of simple, moderate, complex, expert)"

        prompt = f"""## Domain: {domain_context.domain_name}

## Schema Context
{schema_context}

## Target Failure Category: {category.value}

{category_instructions}
"""

        if complexity_instruction:
            prompt += f"""
## Complexity Tier Requirements

{complexity_instruction}
"""

        prompt += f"""
## Task
Generate exactly {count} test queries for the {category.value} failure category.

Each query must:
1. Be appropriate for the {domain_context.domain_name} domain
2. Use tables and columns from the schema above
3. Test the specific failure scenario described
{complexity_requirement}

Return ONLY valid JSON in the format specified in the system prompt."""

        return prompt

    def _parse_llm_response(self, response_text: str) -> list[dict]:
        """Parse LLM JSON response.

        Handles JSON wrapped in markdown code blocks and various edge cases.

        Args:
            response_text: Raw LLM response text

        Returns:
            List of query dictionaries
        """
        if not response_text or not response_text.strip():
            logger.error("Empty response from LLM")
            return []

        # Try multiple extraction strategies
        json_str = None

        # Strategy 1: Extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
        if json_match:
            json_str = json_match.group(1).strip()

        # Strategy 2: Find JSON object starting with {
        if not json_str:
            brace_match = re.search(r"(\{[\s\S]*\})", response_text)
            if brace_match:
                json_str = brace_match.group(1).strip()

        # Strategy 3: Use the raw response
        if not json_str:
            json_str = response_text.strip()

        try:
            data = json.loads(json_str)
            queries = data.get("queries", [])
            if not isinstance(queries, list):
                logger.error("Response 'queries' is not a list")
                return []
            return queries
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Log more context for debugging
            logger.warning(f"Response preview (first 300 chars): {response_text[:300]}")
            logger.warning(f"JSON string preview (first 300 chars): {json_str[:300] if json_str else 'None'}")
            return []

    def _validate_query(
        self,
        query_dict: dict,
        domain_context: DomainContext,
    ) -> bool:
        """Validate generated query against schema.

        Checks that expected_tables exist in the domain and that the
        query has all required fields.

        Args:
            query_dict: Dictionary from LLM response
            domain_context: Schema context for validation

        Returns:
            True if query is valid, False otherwise
        """
        # Check required fields
        required_fields = ["question", "query_type", "complexity"]
        for field_name in required_fields:
            if field_name not in query_dict:
                logger.warning(f"Query missing required field: {field_name}")
                return False

        # Validate question is not empty
        if not query_dict.get("question", "").strip():
            logger.warning("Query has empty question")
            return False

        # Validate query_type is valid, with auto-correction for common LLM mistakes
        query_type_str = query_dict.get("query_type", "").lower()
        valid_query_types = {qt.value for qt in QueryType}

        # Map common invalid query_types to valid ones
        query_type_mapping = {
            "anti_join": "join",
            "anti-join": "join",
            "self_join": "join",
            "self-join": "join",
            "relational_division": "join",
            "subquery": "join",
            "cte": "aggregation",
            "window": "ranking",
            "window_function": "ranking",
            "trick_questions": "filter",  # Adversarial queries default to filter
            "trick_question": "filter",  # Singular variant
            "trick": "filter",
            "adversarial": "filter",
            "unanswerable": "filter",
            "invalid": "filter",
        }

        if query_type_str not in valid_query_types:
            if query_type_str in query_type_mapping:
                corrected = query_type_mapping[query_type_str]
                logger.info(f"Auto-corrected query_type '{query_type_str}' -> '{corrected}'")
                query_dict["query_type"] = corrected
            else:
                logger.warning(f"Invalid query_type: {query_type_str}")
                return False

        # Validate complexity is valid
        complexity_str = query_dict.get("complexity", "").lower()
        valid_complexities = {cl.value for cl in ComplexityLevel}
        if complexity_str not in valid_complexities:
            logger.warning(f"Invalid complexity: {complexity_str}")
            return False

        # Validate expected_tables exist in domain (if provided)
        expected_tables = query_dict.get("expected_tables", [])
        if expected_tables:
            # Build set of valid table names - both short names and full identifiers
            domain_tables: set[str] = set()
            for table_info in domain_context.tables:
                domain_tables.add(table_info.name.lower())
                domain_tables.add(table_info.full_identifier.lower())
            for table in expected_tables:
                if table.lower() not in domain_tables:
                    logger.warning(f"Table '{table}' not found in domain schema. Available: {domain_tables}")
                    # Don't fail validation - LLM might use reasonable table names
                    # that we should accept even if not exact matches

        # Validate expected_columns - reject only known fictional columns
        # We can't validate all columns since YAML may not have full schema
        expected_columns = query_dict.get("expected_columns", [])
        if expected_columns:
            # Known fictional columns that indicate hallucination
            # These are columns that cryptic_codes tests incorrectly assume exist
            fictional_columns = {
                "channel",
                "segment",
                "category",
                "type",
                "type_indicator",
                "segment_code",
                "channel_code",
                "category_code",
                "status_code",
            }

            # Check for fictional columns
            fictional_found = []
            for col in expected_columns:
                col_lower = col.lower()
                if col_lower in fictional_columns:
                    fictional_found.append(col)

            if fictional_found:
                logger.warning(f"Query expects fictional columns: {fictional_found}. Rejecting.")
                return False

        return True

    def _dict_to_benchmark_query(
        self,
        query_dict: dict,
        category: FailureCategory,
        domain_context: DomainContext,
        index: int,
        timestamp: str,
        prompt_hash: str,
        schema_version: str = "",
    ) -> BenchmarkQuery:
        """Convert dictionary to BenchmarkQuery.

        Args:
            query_dict: Dictionary from LLM response
            category: The failure category
            domain_context: Schema context
            index: Query index for ID generation
            timestamp: Generation timestamp
            prompt_hash: Hash of the prompt used
            schema_version: Version of the schema (optional)

        Returns:
            BenchmarkQuery instance
        """
        # Parse query_type
        query_type_str = query_dict.get("query_type", "aggregation").lower()
        try:
            query_type = QueryType(query_type_str)
        except ValueError:
            query_type = QueryType.AGGREGATION

        # Parse complexity
        complexity_str = query_dict.get("complexity", "moderate").lower()
        try:
            complexity = ComplexityLevel(complexity_str)
        except ValueError:
            complexity = ComplexityLevel.MODERATE

        # Parse severity
        severity_str = query_dict.get("severity", "medium").lower()
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.MEDIUM

        # Generate unique ID
        query_id = f"llm_{category.value}_{index:03d}_{uuid.uuid4().hex[:8]}"

        return BenchmarkQuery(
            id=query_id,
            question=query_dict.get("question", ""),
            query_type=query_type,
            complexity=complexity,
            failure_category=category,
            expected_columns=query_dict.get("expected_columns", []),
            expected_tables=query_dict.get("expected_tables", []),
            description=query_dict.get("description", ""),
            is_adversarial=(category == FailureCategory.TRICK_QUESTIONS),
            domain=domain_context.domain_name,
            generated_by="llm",
            schema_version=schema_version,
            expected_failure=query_dict.get("expected_failure"),
            correct_sql=query_dict.get("correct_sql"),
            severity=severity,
            model_name=self.config.model_endpoint,
            temperature=self._temperature,
            prompt_hash=prompt_hash,
            generated_at=timestamp,
        )

    def _mock_generate(
        self,
        domain_context: DomainContext,
        failure_categories: list[FailureCategory] | None,
        complexity_tiers: list[ComplexityLevel] | None,
        queries_per_category: int,
        seed: int | None = None,
        schema_version: str = "",
    ) -> list[BenchmarkQuery]:
        """Generate mock queries for testing (no LLM).

        Creates deterministic mock queries based on domain context and
        predefined templates.

        Args:
            domain_context: Schema context with table/column information
            failure_categories: Categories to generate for (None = all)
            complexity_tiers: Complexity tiers to filter templates by (None = all)
            queries_per_category: Number of queries per category
            seed: Random seed for reproducibility
            schema_version: Version of the schema (optional)

        Returns:
            List of mock BenchmarkQuery objects
        """
        categories = failure_categories or list(FailureCategory)
        all_queries: list[BenchmarkQuery] = []
        timestamp = datetime.now().isoformat()

        # Create a deterministic prompt hash for mock mode
        mock_prompt = f"mock_{domain_context.domain_name}_{seed or 0}"
        prompt_hash = hashlib.sha256(mock_prompt.encode()).hexdigest()[:16]

        for category in categories:
            templates = MOCK_QUERY_TEMPLATES.get(category, [])

            # Filter templates by complexity tier if specified
            if complexity_tiers:
                templates = [t for t in templates if t.get("complexity") in complexity_tiers]

            # Take up to queries_per_category templates
            for idx, template in enumerate(templates[:queries_per_category]):
                # Customize template with domain context
                question = self._customize_mock_question(
                    template["question"],
                    domain_context,
                )

                # Get expected tables from domain if not specified
                # Skip auto-fill for adversarial queries that intentionally have empty expectations
                expected_tables = template.get("expected_tables", [])
                if category != FailureCategory.TRICK_QUESTIONS:
                    if not expected_tables and domain_context.tables:
                        expected_tables = [domain_context.tables[0].name]

                query_id = f"mock_{category.value}_{idx:03d}"

                query = BenchmarkQuery(
                    id=query_id,
                    question=question,
                    query_type=template["query_type"],
                    complexity=template["complexity"],
                    failure_category=category,
                    expected_columns=template.get("expected_columns", []),
                    expected_tables=expected_tables,
                    description=template.get("description", ""),
                    is_adversarial=(category == FailureCategory.TRICK_QUESTIONS),
                    domain=domain_context.domain_name,
                    generated_by="llm",  # Mark as LLM for consistency
                    schema_version=schema_version,
                    expected_failure=template.get("expected_failure"),
                    correct_sql=None,
                    severity=template.get("severity", Severity.MEDIUM),
                    model_name="mock",
                    temperature=0.0,
                    prompt_hash=prompt_hash,
                    generated_at=timestamp,
                )
                all_queries.append(query)

        logger.info(f"Mock generated {len(all_queries)} queries for {len(categories)} categories")
        return all_queries

    def _customize_mock_question(
        self,
        question: str,
        domain_context: DomainContext,
    ) -> str:
        """Customize mock question with domain-specific terms.

        Currently returns the question as-is. Can be extended to perform
        domain-specific term substitution based on business rules or metrics.

        Args:
            question: Template question
            domain_context: Schema context for customization

        Returns:
            Customized question string
        """
        # Future: Could use domain_context.business_rules or metrics
        # to customize questions with domain-specific terminology
        return question

    def save_queries(
        self,
        queries: list[BenchmarkQuery],
        output_path: str | Path,
    ) -> None:
        """Save generated queries to JSON file with provenance.

        The saved file includes full provenance metadata for reproducibility.

        Args:
            queries: List of BenchmarkQuery objects to save
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build output with provenance
        output = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "generator": "LLMQueryGenerator",
            "config": {
                "model_endpoint": self.config.model_endpoint,
                "mock_mode": self.config.mock_mode,
                "temperature": self._temperature,
            },
            "summary": {
                "total_queries": len(queries),
                "by_category": self._count_by_category(queries),
                "by_complexity": self._count_by_complexity(queries),
                "by_query_type": self._count_by_query_type(queries),
            },
            "queries": [q.to_dict() for q in queries],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(queries)} queries to {output_path}")

    def _count_by_category(
        self,
        queries: list[BenchmarkQuery],
    ) -> dict[str, int]:
        """Count queries by failure category."""
        counts: dict[str, int] = {}
        for q in queries:
            key = q.failure_category.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_complexity(
        self,
        queries: list[BenchmarkQuery],
    ) -> dict[str, int]:
        """Count queries by complexity level."""
        counts: dict[str, int] = {}
        for q in queries:
            key = q.complexity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_query_type(
        self,
        queries: list[BenchmarkQuery],
    ) -> dict[str, int]:
        """Count queries by query type."""
        counts: dict[str, int] = {}
        for q in queries:
            key = q.query_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @classmethod
    def load_queries(cls, input_path: str | Path) -> list[BenchmarkQuery]:
        """Load queries from JSON file.

        Args:
            input_path: Path to JSON file with queries

        Returns:
            List of BenchmarkQuery objects

        Raises:
            FileNotFoundError: If input file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        input_path = Path(input_path)

        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)

        queries_data = data.get("queries", [])
        queries = [BenchmarkQuery.from_dict(q) for q in queries_data]

        logger.info(f"Loaded {len(queries)} queries from {input_path}")
        return queries
