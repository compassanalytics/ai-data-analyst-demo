"""Data-aware benchmark query generator.

This module generates benchmark queries based on actual data profiles from parquet files,
ensuring questions use real column names, actual enum values, and realistic date/numeric ranges.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import Config
from src.evaluation.models import ComplexityLevel, FailureCategory, QueryType

from .data_profiler import DataProfile, DataProfiler
from .llm_client import create_llm_client
from .models import BenchmarkQuery, Severity

logger = logging.getLogger(__name__)


# =============================================================================
# DEFAULT COMPLEXITY DISTRIBUTION
# =============================================================================

DEFAULT_COMPLEXITY_DISTRIBUTION: dict[ComplexityLevel, float] = {
    ComplexityLevel.SIMPLE: 0.40,
    ComplexityLevel.MODERATE: 0.30,
    ComplexityLevel.COMPLEX: 0.20,
    ComplexityLevel.EXPERT: 0.10,
}

# Percentage of queries that should be adversarial/trick questions
ADVERSARIAL_PERCENTAGE = 0.05


# =============================================================================
# SYSTEM PROMPT FOR DATA-AWARE GENERATION
# =============================================================================

DATA_AWARE_SYSTEM_PROMPT = """You are an expert at generating benchmark test queries for evaluating AI data assistants.

Your task is to generate natural language questions that a business user might ask about the data.
The questions MUST reference actual column names and values from the data profiles provided.

## Key Requirements:
1. **Use Actual Data Values**: Questions must use real column names and actual values from the profiles
2. **Realistic Business Questions**: Frame questions as a business user would naturally ask
3. **Cover Failure Categories**: Test different AI failure scenarios (ambiguity, temporal confusion, etc.)
4. **Vary Complexity**: Mix of simple to expert-level queries

## Query Types to Generate:
- **aggregation**: SUM, COUNT, AVG, MIN, MAX operations
- **filter**: WHERE clauses with conditions
- **join**: Questions requiring multiple tables
- **temporal**: Date-based filtering and comparisons
- **ranking**: TOP N, RANK, ORDER BY scenarios
- **comparison**: Period-over-period, entity comparisons

## Complexity Levels:
- **simple**: Single table, basic filters/aggregations
- **moderate**: 2 tables with JOIN, GROUP BY with HAVING
- **complex**: 3+ tables, subqueries, date functions, CASE expressions
- **expert**: CTEs, window functions (ROW_NUMBER, LAG, LEAD), self-joins

## Failure Categories to Test:
- **ambiguous_columns**: Questions where multiple similar columns exist
- **cryptic_codes**: Questions using natural language for coded values
- **business_logic**: Questions requiring domain knowledge
- **temporal_confusion**: Ambiguous date/time references
- **aggregation_ambiguity**: Where aggregation level is unclear
- **join_complexity**: Complex multi-table relationships

IMPORTANT: Output ONLY valid JSON, no other text.

Output Format:
{
    "queries": [
        {
            "question": "Natural language question using actual column names/values",
            "query_type": "aggregation|filter|join|temporal|ranking|comparison",
            "complexity": "simple|moderate|complex|expert",
            "expected_columns": ["col1", "col2"],
            "expected_tables": ["table1"],
            "description": "What this query tests",
            "failure_category": "ambiguous_columns|cryptic_codes|business_logic|temporal_confusion|aggregation_ambiguity|join_complexity"
        }
    ]
}
"""

TRICK_QUESTIONS_SYSTEM_PROMPT = """You are an expert at generating ADVERSARIAL test queries that should NOT be answerable from the given data.

Generate trick questions that test whether an AI data assistant appropriately:
1. Refuses to answer when data doesn't exist
2. Asks for clarification when questions are ambiguous
3. Identifies misleading assumptions
4. Recognizes cross-domain confusion

## Types of Trick Questions:
1. **IMPOSSIBLE**: Ask about data that doesn't exist (weather, HR salaries, competitor data)
2. **AMBIGUOUS PRONOUNS**: "What were their sales?" (whose?)
3. **MISLEADING ASSUMPTIONS**: "Why did sales drop?" (assumes they dropped)
4. **CROSS-DOMAIN**: Medical questions for automotive data
5. **CALCULATION TRAPS**: Metrics requiring non-existent data (market share without competitor data)

CRITICAL: These questions should NOT be answerable. Do NOT use actual table or column names.
expected_columns and expected_tables should be EMPTY for trick questions.

IMPORTANT: Output ONLY valid JSON, no other text.

Output Format:
{
    "queries": [
        {
            "question": "Unanswerable natural language question",
            "query_type": "aggregation|filter|join|temporal|ranking|comparison",
            "complexity": "simple|moderate|complex|expert",
            "expected_columns": [],
            "expected_tables": [],
            "description": "Why this is unanswerable",
            "failure_category": "trick_questions"
        }
    ]
}
"""


# =============================================================================
# MOCK TEMPLATES FOR TESTING
# =============================================================================

MOCK_DATA_AWARE_TEMPLATES: list[dict[str, Any]] = [
    {
        "question": "What is the total {numeric_col} for {category_col} = '{category_value}'?",
        "query_type": QueryType.AGGREGATION,
        "complexity": ComplexityLevel.SIMPLE,
        "description": "Tests basic aggregation with filter",
        "failure_category": FailureCategory.AGGREGATION_AMBIGUITY,
    },
    {
        "question": "Show all records where {date_col} is in the last month",
        "query_type": QueryType.TEMPORAL,
        "complexity": ComplexityLevel.SIMPLE,
        "description": "Tests temporal interpretation of 'last month'",
        "failure_category": FailureCategory.TEMPORAL_CONFUSION,
    },
    {
        "question": "What is the average {numeric_col} by {category_col}?",
        "query_type": QueryType.AGGREGATION,
        "complexity": ComplexityLevel.MODERATE,
        "description": "Tests GROUP BY aggregation",
        "failure_category": FailureCategory.AGGREGATION_AMBIGUITY,
    },
    {
        "question": "Show the top 10 {entity} by {numeric_col}",
        "query_type": QueryType.RANKING,
        "complexity": ComplexityLevel.MODERATE,
        "description": "Tests ranking with ORDER BY and LIMIT",
        "failure_category": FailureCategory.AGGREGATION_AMBIGUITY,
    },
    {
        "question": "Compare {numeric_col} between '{category_value}' and other {category_col} values",
        "query_type": QueryType.COMPARISON,
        "complexity": ComplexityLevel.COMPLEX,
        "description": "Tests comparison logic",
        "failure_category": FailureCategory.BUSINESS_LOGIC,
    },
]

MOCK_TRICK_TEMPLATES: list[dict[str, Any]] = [
    {
        "question": "How did weather affect our sales last quarter?",
        "query_type": QueryType.AGGREGATION,
        "complexity": ComplexityLevel.MODERATE,
        "expected_columns": [],
        "expected_tables": [],
        "description": "IMPOSSIBLE: No weather data exists",
        "failure_category": FailureCategory.TRICK_QUESTIONS,
    },
    {
        "question": "What were their sales last month?",
        "query_type": QueryType.AGGREGATION,
        "complexity": ComplexityLevel.SIMPLE,
        "expected_columns": [],
        "expected_tables": [],
        "description": "AMBIGUOUS: 'their' has no referent",
        "failure_category": FailureCategory.TRICK_QUESTIONS,
    },
    {
        "question": "What is our market share compared to competitors?",
        "query_type": QueryType.AGGREGATION,
        "complexity": ComplexityLevel.COMPLEX,
        "expected_columns": [],
        "expected_tables": [],
        "description": "CALCULATION TRAP: No competitor data",
        "failure_category": FailureCategory.TRICK_QUESTIONS,
    },
]


# =============================================================================
# DATA-AWARE GENERATOR
# =============================================================================


class DataAwareGenerator:
    """Generate benchmark queries based on actual data profiles.

    This generator uses data profiler outputs to create questions that reference
    real column names, actual categorical values, and realistic numeric/date ranges.

    Example:
        >>> config = Config.from_env()
        >>> generator = DataAwareGenerator(config, "data/velocity_motors")
        >>> queries = generator.generate(num_queries=20)
    """

    # Default to Claude for best schema understanding
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(
        self,
        config: Config,
        data_dir: str | Path,
        model_override: str | None = None,
    ) -> None:
        """Initialize the data-aware generator.

        Args:
            config: Configuration instance with model settings
            data_dir: Directory containing parquet files to profile
            model_override: Override the default model (e.g., for testing)
        """
        self.config = config
        self.data_dir = Path(data_dir)
        self._model = model_override or config.llm_model or self.DEFAULT_MODEL
        self._temperature = 0.4  # Slightly higher for creative questions
        self._llm = None
        self._profiler: DataProfiler | None = None
        self._profiles: dict[str, DataProfile] | None = None

    @property
    def llm(self):
        """Lazy-load LLM client."""
        if self._llm is None and not self.config.mock_mode:
            self._llm = create_llm_client(
                provider="litellm",
                model=self._model,
                temperature=self._temperature,
            )
        return self._llm

    @property
    def profiler(self) -> DataProfiler:
        """Lazy-load data profiler."""
        if self._profiler is None:
            self._profiler = DataProfiler(self.data_dir)
        return self._profiler

    @property
    def profiles(self) -> dict[str, DataProfile]:
        """Lazy-load or return cached data profiles."""
        if self._profiles is None:
            # Check for cached profiles
            cache_path = self.data_dir / ".data_profiles.json"
            current_signature = self.profiler.get_data_signature()

            if cache_path.exists():
                try:
                    cached = self.profiler.load_profiles(cache_path)
                    # Verify signature matches
                    if cached and any(p.data_signature for p in cached.values()):
                        first_profile = next(iter(cached.values()))
                        if first_profile.data_signature == current_signature:
                            logger.info("Using cached data profiles")
                            self._profiles = cached
                            return self._profiles
                except Exception as e:
                    logger.warning(f"Could not load cached profiles: {e}")

            # Profile all tables
            logger.info("Profiling data tables...")
            self._profiles = self.profiler.profile_all_tables()

            # Cache the profiles
            try:
                self.profiler.save_profiles(self._profiles, cache_path)
            except Exception as e:
                logger.warning(f"Could not cache profiles: {e}")

        # At this point, _profiles is guaranteed to be set
        assert self._profiles is not None, "Data profiles should be loaded"
        return self._profiles

    def generate(
        self,
        num_queries: int = 20,
        complexity_distribution: dict[ComplexityLevel, float] | None = None,
    ) -> list[BenchmarkQuery]:
        """Generate benchmark queries based on data profiles.

        Args:
            num_queries: Total number of queries to generate
            complexity_distribution: Distribution of complexity levels (must sum to 1.0)
                Defaults to: simple=40%, moderate=30%, complex=20%, expert=10%

        Returns:
            List of generated BenchmarkQuery objects
        """
        if self.config.mock_mode:
            return self._mock_generate(num_queries, complexity_distribution)

        return self._llm_generate(num_queries, complexity_distribution)

    def _llm_generate(
        self,
        num_queries: int,
        complexity_distribution: dict[ComplexityLevel, float] | None,
    ) -> list[BenchmarkQuery]:
        """Generate queries using LLM with data profile context.

        Args:
            num_queries: Total number of queries to generate
            complexity_distribution: Distribution of complexity levels

        Returns:
            List of generated BenchmarkQuery objects
        """
        distribution = complexity_distribution or DEFAULT_COMPLEXITY_DISTRIBUTION

        # Calculate queries per complexity tier
        queries_per_tier = self._calculate_queries_per_tier(num_queries, distribution)

        # Calculate adversarial count
        adversarial_count = max(1, int(num_queries * ADVERSARIAL_PERCENTAGE))
        regular_count = num_queries - adversarial_count

        # Adjust queries per tier to account for adversarial
        scale_factor = regular_count / num_queries
        for tier in queries_per_tier:
            queries_per_tier[tier] = max(1, int(queries_per_tier[tier] * scale_factor))

        # Build profile context for LLM
        profile_context = self.profiler.to_prompt_context(self.profiles)

        # Generate regular queries
        all_queries: list[BenchmarkQuery] = []
        timestamp = datetime.now().isoformat()

        for complexity, count in queries_per_tier.items():
            if count <= 0:
                continue

            try:
                queries = self._generate_for_complexity(
                    profile_context=profile_context,
                    complexity=complexity,
                    count=count,
                    timestamp=timestamp,
                )
                all_queries.extend(queries)
                if len(queries) < count:
                    logger.warning(f"Requested {count} {complexity.value} queries, LLM returned {len(queries)}")
                else:
                    logger.info(f"Generated {len(queries)} {complexity.value} queries")
            except Exception as e:
                logger.error(f"Failed to generate {complexity.value} queries: {e}")

        # Generate adversarial/trick questions
        try:
            trick_queries = self._generate_trick_questions(
                count=adversarial_count,
                timestamp=timestamp,
            )
            all_queries.extend(trick_queries)
            logger.info(f"Generated {len(trick_queries)} trick questions")
        except Exception as e:
            logger.error(f"Failed to generate trick questions: {e}")

        logger.info(f"Total generated: {len(all_queries)} queries")
        return all_queries

    def _generate_for_complexity(
        self,
        profile_context: str,
        complexity: ComplexityLevel,
        count: int,
        timestamp: str,
    ) -> list[BenchmarkQuery]:
        """Generate queries for a specific complexity level.

        Args:
            profile_context: Formatted data profile context
            complexity: Target complexity level
            count: Number of queries to generate
            timestamp: Generation timestamp

        Returns:
            List of BenchmarkQuery objects
        """
        llm = self.llm
        if llm is None:
            logger.warning("LLM not available")
            return []

        # Build user prompt with profile context and complexity requirements
        user_prompt = self._build_user_prompt(profile_context, complexity, count)

        # Calculate prompt hash for provenance
        prompt_content = DATA_AWARE_SYSTEM_PROMPT + user_prompt
        prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()[:16]

        # Invoke LLM with retry for insufficient queries
        messages = [
            {"role": "system", "content": DATA_AWARE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        max_retries = 2
        query_dicts: list[dict] = []

        for attempt in range(max_retries + 1):
            response = llm.invoke(messages)
            query_dicts = self._parse_llm_response(response.content)

            if len(query_dicts) >= count:
                break
            elif attempt < max_retries:
                logger.warning(
                    f"LLM returned {len(query_dicts)} queries, expected {count}. Retrying... ({attempt + 1}/{max_retries})"
                )

        # If still short after retries, log it
        if len(query_dicts) < count:
            logger.warning(
                f"After {max_retries} retries, only got {len(query_dicts)}/{count} {complexity.value} queries"
            )

        # Convert to BenchmarkQuery objects
        queries: list[BenchmarkQuery] = []
        for idx, query_dict in enumerate(query_dicts):
            if self._validate_query(query_dict):
                query = self._dict_to_benchmark_query(
                    query_dict=query_dict,
                    index=idx,
                    timestamp=timestamp,
                    prompt_hash=prompt_hash,
                    complexity_override=complexity,
                )
                queries.append(query)
            else:
                logger.warning(f"Skipping invalid query: {query_dict.get('question', 'unknown')}")

        return queries

    def _generate_trick_questions(
        self,
        count: int,
        timestamp: str,
    ) -> list[BenchmarkQuery]:
        """Generate adversarial/trick questions that should not be answerable.

        Args:
            count: Number of trick questions to generate
            timestamp: Generation timestamp

        Returns:
            List of adversarial BenchmarkQuery objects
        """
        llm = self.llm
        if llm is None:
            logger.warning("LLM not available for trick questions")
            return []

        # Build a minimal context prompt (we don't want real data in trick questions)
        user_prompt = f"""Generate exactly {count} adversarial/trick questions.

These questions should be UNANSWERABLE with any reasonable SQL database.
Do NOT reference any actual table or column names.

Focus on:
- Questions about data that typically doesn't exist (weather, HR salaries, competitor data)
- Ambiguous pronouns ("their", "it", "the other one")
- Misleading assumptions ("Why did X happen?" when X may not have happened)
- Cross-domain confusion (asking medical questions about automotive data, etc.)
- Calculations requiring non-existent data (market share without competitor data)

Generate questions that test whether an AI appropriately refuses or asks for clarification.
"""

        # Calculate prompt hash
        prompt_content = TRICK_QUESTIONS_SYSTEM_PROMPT + user_prompt
        prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()[:16]

        # Invoke LLM
        messages = [
            {"role": "system", "content": TRICK_QUESTIONS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = llm.invoke(messages)

        # Parse response
        query_dicts = self._parse_llm_response(response.content)

        # Convert to BenchmarkQuery objects
        queries: list[BenchmarkQuery] = []
        for idx, query_dict in enumerate(query_dicts):
            # Force trick question attributes
            query_dict["expected_columns"] = []
            query_dict["expected_tables"] = []
            query_dict["failure_category"] = "trick_questions"

            query = self._dict_to_benchmark_query(
                query_dict=query_dict,
                index=idx,
                timestamp=timestamp,
                prompt_hash=prompt_hash,
                is_adversarial=True,
            )
            queries.append(query)

        return queries

    def _build_user_prompt(
        self,
        profile_context: str,
        complexity: ComplexityLevel,
        count: int,
    ) -> str:
        """Build user prompt with data profile context.

        Args:
            profile_context: Formatted data profile summary
            complexity: Target complexity level
            count: Number of queries to generate

        Returns:
            User prompt string
        """
        # Get table names for context
        table_names = list(self.profiles.keys())

        complexity_guidance = {
            ComplexityLevel.SIMPLE: """
Generate SIMPLE queries:
- Single table queries only
- Basic WHERE filters using actual column values
- Simple aggregations: COUNT, SUM, AVG
- Use actual categorical values from the profiles""",
            ComplexityLevel.MODERATE: """
Generate MODERATE complexity queries:
- Can use 2 tables with JOIN
- GROUP BY with simple HAVING clauses
- Multiple filter conditions
- Date comparisons using the actual date ranges
- ORDER BY with LIMIT""",
            ComplexityLevel.COMPLEX: """
Generate COMPLEX queries:
- 3+ table JOINs
- Subqueries (scalar, correlated)
- Date functions like DATE_TRUNC, DATEDIFF
- CASE expressions
- Set operations (UNION/EXCEPT)
- Year-over-year or period comparisons""",
            ComplexityLevel.EXPERT: """
Generate EXPERT-level queries:
- CTEs (WITH clauses)
- Window functions: ROW_NUMBER, RANK, LAG, LEAD
- PARTITION BY for analytics
- Running totals, moving averages
- Self-joins for sequential data analysis
- Complex multi-level aggregations""",
        }

        prompt = f"""## Available Tables
{", ".join(table_names)}

## Data Profile Context
{profile_context}

## Complexity Level: {complexity.value.upper()}

{complexity_guidance.get(complexity, "")}

## Task
Generate EXACTLY {count} benchmark queries at {complexity.value} complexity level.
You MUST return exactly {count} queries in the response - no more, no fewer.

CRITICAL REQUIREMENTS:
1. Use ACTUAL column names from the profiles above
2. Use ACTUAL categorical values (e.g., if 'make' has values 'Ford', 'Toyota', use those exact values)
3. Use realistic date ranges based on the date column min/max values
4. Use realistic numeric ranges based on the numeric column statistics
5. Cover different failure categories (ambiguous_columns, cryptic_codes, business_logic, temporal_confusion, aggregation_ambiguity, join_complexity)

Return ONLY valid JSON in the format specified."""

        return prompt

    def _parse_llm_response(self, response_text: str) -> list[dict]:
        """Parse LLM JSON response.

        Args:
            response_text: Raw LLM response text

        Returns:
            List of query dictionaries
        """
        if not response_text or not response_text.strip():
            logger.error("Empty response from LLM")
            return []

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

        # Strategy 3: Use raw response
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
            logger.warning(f"Response preview: {response_text[:300]}")
            return []

    def _validate_query(self, query_dict: dict) -> bool:
        """Validate a generated query dictionary.

        Args:
            query_dict: Dictionary from LLM response

        Returns:
            True if query is valid
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

        # Validate query_type
        query_type_str = query_dict.get("query_type", "").lower()
        valid_query_types = {qt.value for qt in QueryType}

        # Map common variants
        query_type_mapping = {
            "anti_join": "join",
            "anti-join": "join",
            "self_join": "join",
            "window": "ranking",
            "window_function": "ranking",
        }

        if query_type_str not in valid_query_types:
            if query_type_str in query_type_mapping:
                query_dict["query_type"] = query_type_mapping[query_type_str]
            else:
                logger.warning(f"Invalid query_type: {query_type_str}")
                return False

        # Validate complexity
        complexity_str = query_dict.get("complexity", "").lower()
        valid_complexities = {cl.value for cl in ComplexityLevel}
        if complexity_str not in valid_complexities:
            logger.warning(f"Invalid complexity: {complexity_str}")
            return False

        return True

    def _dict_to_benchmark_query(
        self,
        query_dict: dict,
        index: int,
        timestamp: str,
        prompt_hash: str,
        complexity_override: ComplexityLevel | None = None,
        is_adversarial: bool = False,
    ) -> BenchmarkQuery:
        """Convert dictionary to BenchmarkQuery.

        Args:
            query_dict: Dictionary from LLM response
            index: Query index for ID generation
            timestamp: Generation timestamp
            prompt_hash: Hash of the prompt used
            complexity_override: Override complexity from dict
            is_adversarial: Whether this is an adversarial query

        Returns:
            BenchmarkQuery instance
        """
        # Parse query_type
        query_type_str = query_dict.get("query_type", "aggregation").lower()
        try:
            query_type = QueryType(query_type_str)
        except ValueError:
            query_type = QueryType.AGGREGATION

        # Parse complexity (use override if provided)
        if complexity_override:
            complexity = complexity_override
        else:
            complexity_str = query_dict.get("complexity", "moderate").lower()
            try:
                complexity = ComplexityLevel(complexity_str)
            except ValueError:
                complexity = ComplexityLevel.MODERATE

        # Parse failure_category
        failure_cat_str = query_dict.get("failure_category", "aggregation_ambiguity").lower()
        try:
            failure_category = FailureCategory(failure_cat_str)
        except ValueError:
            failure_category = FailureCategory.AGGREGATION_AMBIGUITY

        # For adversarial queries, always use TRICK_QUESTIONS
        if is_adversarial:
            failure_category = FailureCategory.TRICK_QUESTIONS

        # Generate unique ID
        query_id = f"data_aware_{failure_category.value}_{index:03d}_{uuid.uuid4().hex[:8]}"

        # Derive domain from data directory name
        domain = self.data_dir.name

        return BenchmarkQuery(
            id=query_id,
            question=query_dict.get("question", ""),
            query_type=query_type,
            complexity=complexity,
            failure_category=failure_category,
            expected_columns=query_dict.get("expected_columns", []),
            expected_tables=query_dict.get("expected_tables", []),
            description=query_dict.get("description", ""),
            is_adversarial=is_adversarial,
            domain=domain,
            generated_by="llm",
            schema_version=self.profiler.get_data_signature()[:16] if self.profiles else "",
            expected_failure=query_dict.get("expected_failure"),
            correct_sql=query_dict.get("correct_sql"),
            severity=Severity.MEDIUM,
            model_name=self._model,
            temperature=self._temperature,
            prompt_hash=prompt_hash,
            generated_at=timestamp,
        )

    def _calculate_queries_per_tier(
        self,
        total: int,
        distribution: dict[ComplexityLevel, float],
    ) -> dict[ComplexityLevel, int]:
        """Calculate number of queries per complexity tier.

        Args:
            total: Total number of queries
            distribution: Percentage distribution per tier

        Returns:
            Dictionary mapping complexity to query count
        """
        counts: dict[ComplexityLevel, int] = {}
        remaining = total

        # Sort by distribution value descending to assign larger counts first
        sorted_tiers = sorted(distribution.items(), key=lambda x: x[1], reverse=True)

        for i, (tier, pct) in enumerate(sorted_tiers):
            if i == len(sorted_tiers) - 1:
                # Last tier gets remaining to avoid rounding issues
                counts[tier] = remaining
            else:
                count = max(1, int(total * pct))
                counts[tier] = count
                remaining -= count

        return counts

    def _mock_generate(
        self,
        num_queries: int,
        complexity_distribution: dict[ComplexityLevel, float] | None,
    ) -> list[BenchmarkQuery]:
        """Generate mock queries for testing (no LLM required).

        Args:
            num_queries: Total number of queries to generate
            complexity_distribution: Distribution of complexity levels

        Returns:
            List of mock BenchmarkQuery objects
        """
        distribution = complexity_distribution or DEFAULT_COMPLEXITY_DISTRIBUTION
        queries_per_tier = self._calculate_queries_per_tier(num_queries, distribution)

        # Get some data from profiles for templating
        sample_data = self._get_sample_data_for_mock()

        timestamp = datetime.now().isoformat()
        prompt_hash = hashlib.sha256(f"mock_{timestamp}".encode()).hexdigest()[:16]

        all_queries: list[BenchmarkQuery] = []
        query_idx = 0

        # Generate regular queries
        for complexity, count in queries_per_tier.items():
            for i in range(count):
                template = MOCK_DATA_AWARE_TEMPLATES[i % len(MOCK_DATA_AWARE_TEMPLATES)]

                # Fill in template with sample data
                question = self._fill_template(template["question"], sample_data)

                query = BenchmarkQuery(
                    id=f"mock_data_aware_{query_idx:03d}",
                    question=question,
                    query_type=template["query_type"],
                    complexity=complexity,
                    failure_category=template["failure_category"],
                    expected_columns=sample_data.get("expected_columns", []),
                    expected_tables=sample_data.get("expected_tables", []),
                    description=template["description"],
                    is_adversarial=False,
                    domain=self.data_dir.name,
                    generated_by="llm",
                    schema_version="mock",
                    model_name="mock",
                    temperature=0.0,
                    prompt_hash=prompt_hash,
                    generated_at=timestamp,
                )
                all_queries.append(query)
                query_idx += 1

        # Add some trick questions (about 5%)
        trick_count = max(1, int(num_queries * ADVERSARIAL_PERCENTAGE))
        for i in range(trick_count):
            template = MOCK_TRICK_TEMPLATES[i % len(MOCK_TRICK_TEMPLATES)]

            query = BenchmarkQuery(
                id=f"mock_trick_{i:03d}",
                question=template["question"],
                query_type=template["query_type"],
                complexity=template["complexity"],
                failure_category=FailureCategory.TRICK_QUESTIONS,
                expected_columns=[],
                expected_tables=[],
                description=template["description"],
                is_adversarial=True,
                domain=self.data_dir.name,
                generated_by="llm",
                schema_version="mock",
                model_name="mock",
                temperature=0.0,
                prompt_hash=prompt_hash,
                generated_at=timestamp,
            )
            all_queries.append(query)

        logger.info(f"Mock generated {len(all_queries)} queries")
        return all_queries

    def _get_sample_data_for_mock(self) -> dict[str, Any]:
        """Extract sample data from profiles for mock templating.

        Returns:
            Dictionary with sample column names, values, etc.
        """
        sample: dict[str, Any] = {
            "numeric_col": "amount",
            "category_col": "status",
            "category_value": "completed",
            "date_col": "created_at",
            "entity": "records",
            "expected_columns": [],
            "expected_tables": [],
        }

        if not self.profiles:
            return sample

        # Get first table for samples
        first_table = next(iter(self.profiles.values()), None)
        if not first_table:
            return sample

        sample["expected_tables"] = [first_table.table_name]

        # Find a numeric column
        numeric_cols = first_table.get_numeric_columns()
        if numeric_cols:
            sample["numeric_col"] = numeric_cols[0].name
            sample["expected_columns"].append(numeric_cols[0].name)

        # Find a categorical column with values
        cat_cols = first_table.get_categorical_columns()
        if cat_cols:
            col = cat_cols[0]
            sample["category_col"] = col.name
            sample["expected_columns"].append(col.name)
            if col.top_values:
                sample["category_value"] = col.top_values[0][0]

        # Find a date column
        date_cols = first_table.get_date_columns()
        if date_cols:
            sample["date_col"] = date_cols[0].name
            sample["expected_columns"].append(date_cols[0].name)

        # Entity name from table
        sample["entity"] = first_table.table_name.replace("_", " ")

        return sample

    def _fill_template(self, template: str, data: dict[str, Any]) -> str:
        """Fill a template string with sample data.

        Args:
            template: Template string with {placeholders}
            data: Dictionary with replacement values

        Returns:
            Filled template string
        """
        try:
            return template.format(**data)
        except KeyError:
            # Return template with any unfilled placeholders
            return template

    def save_queries(
        self,
        queries: list[BenchmarkQuery],
        output_path: str | Path,
    ) -> None:
        """Save generated queries to JSON file with provenance.

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
            "generator": "DataAwareGenerator",
            "data_dir": str(self.data_dir),
            "config": {
                "model": self._model,
                "mock_mode": self.config.mock_mode,
                "temperature": self._temperature,
            },
            "summary": {
                "total_queries": len(queries),
                "by_complexity": self._count_by_complexity(queries),
                "by_failure_category": self._count_by_category(queries),
                "by_query_type": self._count_by_query_type(queries),
                "adversarial_count": sum(1 for q in queries if q.is_adversarial),
            },
            "queries": [q.to_dict() for q in queries],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(queries)} queries to {output_path}")

    def _count_by_complexity(self, queries: list[BenchmarkQuery]) -> dict[str, int]:
        """Count queries by complexity level."""
        counts: dict[str, int] = {}
        for q in queries:
            key = q.complexity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_category(self, queries: list[BenchmarkQuery]) -> dict[str, int]:
        """Count queries by failure category."""
        counts: dict[str, int] = {}
        for q in queries:
            key = q.failure_category.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_query_type(self, queries: list[BenchmarkQuery]) -> dict[str, int]:
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
        """
        input_path = Path(input_path)

        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)

        queries_data = data.get("queries", [])
        queries = [BenchmarkQuery.from_dict(q) for q in queries_data]

        logger.info(f"Loaded {len(queries)} queries from {input_path}")
        return queries
