"""LLM-powered query generator for the benchmark system.

This module generates domain-specific test queries using an LLM (ChatDatabricks)
based on schema context. Supports mock mode for testing without LLM API access.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import Config
from src.evaluation.models import ComplexityLevel, FailureCategory, QueryType

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
            "complexity": "simple|moderate|complex",
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
    FailureCategory.CRYPTIC_CODES: """Generate queries that test handling of CRYPTIC CODES and abbreviations.

Focus on scenarios where:
- Status codes are numeric (1,2,3,4,5) instead of descriptive
- Segment codes like ENT/MID/SMB need interpretation
- Channel codes like ON/OFF/EC represent business concepts
- Category codes like BER/CID/RTD/NAB need domain knowledge
- Type indicators use non-obvious abbreviations

The AI assistant might not know how to map natural language terms to these codes.
Generate questions using natural language that requires code translation.""",
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

    Uses ChatDatabricks to generate domain-specific test queries based on
    schema context. Supports mock mode for testing without LLM API access.

    Example:
        >>> config = Config.from_env()
        >>> generator = LLMQueryGenerator(config)
        >>> queries = generator.generate(domain_context, queries_per_category=5)
    """

    def __init__(self, config: Config):
        """Initialize the LLM query generator.

        Args:
            config: Configuration instance with model settings
        """
        self.config = config
        self._llm = None
        self._temperature = 0.7  # Some creativity for variety

    @property
    def llm(self):
        """Lazy-load ChatDatabricks LLM."""
        if self._llm is None and not self.config.mock_mode:
            from databricks_langchain import ChatDatabricks

            self._llm = ChatDatabricks(
                endpoint=self.config.model_endpoint,
                temperature=self._temperature,
            )
        return self._llm

    def generate(
        self,
        domain_context: DomainContext,
        failure_categories: list[FailureCategory] | None = None,
        queries_per_category: int = 5,
        seed: int | None = None,
        schema_version: str = "",
    ) -> list[BenchmarkQuery]:
        """Generate benchmark queries for the domain.

        Args:
            domain_context: Schema context with table/column information
            failure_categories: Categories to generate for (None = all)
            queries_per_category: Number of queries per category
            seed: Random seed for reproducibility (used in mock mode)
            schema_version: Version of the schema (optional, for provenance)

        Returns:
            List of generated BenchmarkQuery objects
        """
        if self.config.mock_mode:
            return self._mock_generate(
                domain_context, failure_categories, queries_per_category, seed, schema_version=schema_version
            )
        return self._llm_generate(
            domain_context, failure_categories, queries_per_category, schema_version=schema_version
        )

    def _llm_generate(
        self,
        domain_context: DomainContext,
        failure_categories: list[FailureCategory] | None,
        queries_per_category: int,
        schema_version: str = "",
    ) -> list[BenchmarkQuery]:
        """Generate queries using LLM.

        Args:
            domain_context: Schema context with table/column information
            failure_categories: Categories to generate for (None = all)
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
        count: int,
        timestamp: str,
        schema_version: str = "",
    ) -> list[BenchmarkQuery]:
        """Generate queries for a single failure category.

        Args:
            domain_context: Schema context
            category: The failure category to target
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
        user_prompt = self._build_user_prompt(domain_context, category, count)

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
    ) -> str:
        """Build user prompt with schema context.

        Args:
            domain_context: Schema context with table/column information
            category: The failure category to target
            count: Number of queries to generate

        Returns:
            User prompt string
        """
        # Get category-specific instructions
        category_instructions = FAILURE_CATEGORY_PROMPTS.get(
            category, f"Generate queries that test {category.value.replace('_', ' ')} scenarios."
        )

        # Get schema context from domain
        schema_context = domain_context.to_prompt_context()

        prompt = f"""## Domain: {domain_context.domain_name}

## Schema Context
{schema_context}

## Target Failure Category: {category.value}

{category_instructions}

## Task
Generate exactly {count} test queries for the {category.value} failure category.

Each query must:
1. Be appropriate for the {domain_context.domain_name} domain
2. Use tables and columns from the schema above
3. Test the specific failure scenario described
4. Have varying complexity (mix of simple, moderate, complex)

Return ONLY valid JSON in the format specified in the system prompt."""

        return prompt

    def _parse_llm_response(self, response_text: str) -> list[dict]:
        """Parse LLM JSON response.

        Handles JSON wrapped in markdown code blocks.

        Args:
            response_text: Raw LLM response text

        Returns:
            List of query dictionaries
        """
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Try to find raw JSON
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
            logger.debug(f"Response text: {response_text[:500]}")
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

        # Validate query_type is valid
        query_type_str = query_dict.get("query_type", "").lower()
        valid_query_types = {qt.value for qt in QueryType}
        if query_type_str not in valid_query_types:
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
            # Use get_table_names() method from DomainContext
            domain_tables = {name.lower() for name in domain_context.get_table_names()}
            for table in expected_tables:
                if table.lower() not in domain_tables:
                    logger.warning(f"Table '{table}' not found in domain schema. Available: {domain_tables}")
                    # Don't fail validation - LLM might use reasonable table names
                    # that we should accept even if not exact matches

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
            is_adversarial=False,
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

            # Take up to queries_per_category templates
            for idx, template in enumerate(templates[:queries_per_category]):
                # Customize template with domain context
                question = self._customize_mock_question(
                    template["question"],
                    domain_context,
                )

                # Get expected tables from domain if not specified
                expected_tables = template.get("expected_tables", [])
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
                    is_adversarial=False,
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
