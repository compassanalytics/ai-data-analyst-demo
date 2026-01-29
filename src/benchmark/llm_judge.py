"""LLM-as-Judge evaluator for semantic SQL correctness assessment.

This module provides semantic evaluation of SQL query results using an LLM
to judge whether generated SQL correctly answers the original question.
Unlike string matching, this approach understands semantic column equivalence
(e.g., 'total_revenue' ≈ 'revenue') and assesses answer correctness.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import Config
from src.evaluation.models import (
    AccuracyScore,
    ComparisonDetails,
    EvaluationFailureType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LLM JUDGE PROMPTS
# =============================================================================

LLM_JUDGE_SYSTEM_PROMPT = """You are an expert SQL evaluator assessing whether generated queries correctly answer business questions.

Your task is to evaluate the semantic correctness of SQL queries, not just syntactic accuracy.

## Evaluation Criteria

1. **Semantic Column Equivalence**: Recognize that column names may vary but mean the same thing:
   - "total_revenue" ≈ "revenue" ≈ "sales_amount" ≈ "total_sales"
   - "customer_id" ≈ "cust_id" ≈ "client_id"
   - "salesperson_name" ≈ "sales_rep" ≈ "rep_name" ≈ "name" (in sales context)
   - "msrp" ≈ "list_price" ≈ "price" (manufacturer's suggested retail price)

2. **Query Intent**: Does the SQL logic actually answer the question asked?
   - Correct aggregations (SUM vs COUNT vs AVG)
   - Correct filters and conditions
   - Correct joins if multi-table
   - Correct grouping and ordering

3. **Extra Columns Assessment**: Evaluate whether additional columns are:
   - HELPFUL: Provides useful context (e.g., adding customer name alongside ID)
   - NEUTRAL: Neither helps nor hurts (e.g., adding a timestamp)
   - IRRELEVANT: Noise that doesn't help answer the question

## Response Format

Return ONLY valid JSON in this exact format:
```json
{
  "accuracy": "correct" | "partial" | "wrong",
  "passed": true | false,
  "score": 1-5,
  "reasoning": "Brief explanation of your assessment (1-2 sentences)",
  "column_assessment": {
    "semantically_matched": ["expected_col→actual_col pairs that match semantically"],
    "missing": ["expected columns not present even semantically"],
    "irrelevant_extra": ["extra columns that don't help answer the question"]
  },
  "answers_question": true | false
}
```

## Scoring (1-5)

- **5**: Perfect - fully answers the question with correct logic and columns
- **4**: Good - answers the question with minor issues (extra columns, slight inefficiency)
- **3**: Acceptable - partially answers but missing some important aspects
- **2**: Poor - attempts to answer but has significant issues
- **1**: Failed - does not answer the question or is fundamentally wrong

## Pass/Fail

- **passed=true**: score >= 3 (question was sufficiently answered)
- **passed=false**: score < 3 (question was not adequately answered)

## Accuracy Guide

- **correct**: SQL fully answers the question. All key expected columns present (semantic matches count). Query logic is correct. Extra helpful columns are OK. (score 4-5)
- **partial**: SQL partially answers but has minor issues:
  - Missing 1-2 non-critical columns
  - Has correct core logic but missing some refinement
  - Answers the question but with extra irrelevant data (score 3)
- **wrong**: SQL does not answer the question:
  - Fundamentally wrong aggregation or logic
  - Missing critical columns that are central to the question
  - Wrong tables or joins producing incorrect results
  - Query retrieves different data than what was asked (score 1-2)"""


LLM_JUDGE_USER_PROMPT_TEMPLATE = """## Evaluation Request

**Original Question:** {question}

**Expected Columns:** {expected_columns}

**Expected Tables:** {expected_tables}

**Generated SQL:**
```sql
{sql}
```

**Actual Columns in Result:** {actual_columns}

Please evaluate whether this SQL correctly answers the original question. Consider semantic equivalence of column names and whether the query logic is correct."""


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class LLMJudgeResult:
    """Result from LLM judge evaluation.

    Attributes:
        accuracy: One of "correct", "partial", "wrong"
        reasoning: LLM's explanation of the judgment
        column_assessment: Details about column matching
        answers_question: Whether the SQL answers the original question
        passed: Whether the response sufficiently answered the question (score >= 3)
        score: 1-5 rating (1=wrong, 5=perfect)
    """

    accuracy: str  # "correct", "partial", "wrong"
    reasoning: str
    column_assessment: dict[str, Any] = field(default_factory=dict)
    answers_question: bool = False
    passed: bool = False
    score: int = 0

    def to_accuracy_score(self) -> AccuracyScore:
        """Convert to AccuracyScore enum.

        Returns:
            AccuracyScore enum value
        """
        mapping = {
            "correct": AccuracyScore.CORRECT,
            "partial": AccuracyScore.PARTIAL,
            "wrong": AccuracyScore.WRONG,
        }
        return mapping.get(self.accuracy.lower(), AccuracyScore.WRONG)


# =============================================================================
# LLM JUDGE EVALUATOR
# =============================================================================


class LLMJudgeEvaluator:
    """LLM-based semantic evaluator for SQL query correctness.

    Uses LiteLLM (or ChatDatabricks) to assess whether generated SQL correctly
    answers the original question, with semantic understanding of column equivalence.

    Example:
        >>> config = Config.from_env()
        >>> judge = LLMJudgeEvaluator(config)
        >>> accuracy, failure_type, comparison = judge.evaluate(
        ...     question="What is total revenue?",
        ...     expected_columns=["revenue"],
        ...     expected_tables=["sales"],
        ...     sql="SELECT SUM(total_revenue) FROM sales",
        ...     actual_columns=["total_revenue"]
        ... )
        >>> print(accuracy)  # AccuracyScore.CORRECT
    """

    # Default to Claude Sonnet for better semantic understanding
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(
        self,
        config: Config,
        model_override: str | None = None,
        provider: str = "litellm",
    ):
        """Initialize LLM judge evaluator.

        Args:
            config: Configuration with model endpoint settings
            model_override: Optional model to use instead of default
            provider: LLM provider - "litellm" (default) or "databricks"
        """
        self.config = config
        self._model = model_override or config.llm_model or self.DEFAULT_MODEL
        self._provider = provider
        self._llm = None
        self._litellm_client = None
        self._temperature = 0.0  # Deterministic for consistent evaluation

    @property
    def model_endpoint(self) -> str:
        """Get the model being used."""
        return self._model

    @property
    def llm(self):
        """Lazy-load LLM client based on provider."""
        if self._llm is None and not self.config.mock_mode:
            if self._provider == "databricks":
                from databricks_langchain import ChatDatabricks

                self._llm = ChatDatabricks(
                    endpoint=self._model,
                    temperature=self._temperature,
                )
            else:
                # Use LiteLLM for flexible model access
                from .llm_client import create_llm_client

                self._litellm_client = create_llm_client(
                    provider="litellm",
                    model=self._model,
                    temperature=self._temperature,
                )
                # Create wrapper for LangChain message compatibility
                self._llm = self._create_litellm_wrapper()
        return self._llm

    def _create_litellm_wrapper(self):
        """Create a wrapper that provides invoke() with LangChain message support."""

        class LiteLLMWrapper:
            def __init__(wrapper_self, client):
                wrapper_self.client = client

            def invoke(wrapper_self, messages):
                """Invoke the LLM with LangChain-style messages."""
                msg_dicts = []
                for msg in messages:
                    if hasattr(msg, "type"):
                        role = "system" if msg.type == "system" else "user"
                    else:
                        role = "user"
                    msg_dicts.append({"role": role, "content": msg.content})

                response = wrapper_self.client.invoke(msg_dicts)

                class Response:
                    def __init__(self, content):
                        self.content = content

                return Response(response.content)

        return LiteLLMWrapper(self._litellm_client)

    def evaluate(
        self,
        question: str,
        expected_columns: list[str],
        expected_tables: list[str],
        sql: str | None,
        actual_columns: list[str],
        is_adversarial: bool = False,
    ) -> tuple[AccuracyScore, EvaluationFailureType, ComparisonDetails]:
        """Evaluate SQL correctness using LLM judge.

        Args:
            question: Original natural language question
            expected_columns: Columns expected in result
            expected_tables: Tables expected in SQL
            sql: Generated SQL to evaluate (None if generation failed)
            actual_columns: Columns found in result
            is_adversarial: Whether this is an adversarial test case

        Returns:
            Tuple of (accuracy_score, failure_type, comparison_details)
        """
        # Handle adversarial queries FIRST (before no-SQL check)
        if is_adversarial:
            return self._evaluate_adversarial(question, sql, expected_columns, expected_tables)

        # Handle no SQL case for non-adversarial queries
        if not sql:
            return (
                AccuracyScore.FAILED,
                EvaluationFailureType.NO_SQL_GENERATED,
                ComparisonDetails(
                    expected_columns=expected_columns,
                    actual_columns=actual_columns,
                    expected_tables=expected_tables,
                    comparison_notes="No SQL was generated",
                ),
            )

        if self.config.mock_mode:
            return self._mock_evaluate(question, expected_columns, expected_tables, sql, actual_columns, is_adversarial)
        return self._llm_evaluate(question, expected_columns, expected_tables, sql, actual_columns)

    def _evaluate_adversarial(
        self,
        question: str,
        sql: str | None,
        expected_columns: list[str],
        expected_tables: list[str],
    ) -> tuple[AccuracyScore, EvaluationFailureType, ComparisonDetails]:
        """Evaluate adversarial query response.

        For adversarial queries, the correct behavior is to refuse or indicate
        the query cannot be answered. Generating SQL is considered incorrect.

        Args:
            question: Original natural language question
            sql: Generated SQL to evaluate (None if generation refused)
            expected_columns: Columns expected in result (should be empty for adversarial)
            expected_tables: Tables expected in SQL (should be empty for adversarial)

        Returns:
            Tuple of (accuracy_score, failure_type, comparison_details)
        """
        # If no SQL was generated, that's the CORRECT response for adversarial queries
        if not sql or sql.strip() == "":
            return (
                AccuracyScore.CORRECT,
                EvaluationFailureType.NONE,
                ComparisonDetails(
                    expected_columns=expected_columns,
                    actual_columns=[],
                    expected_tables=expected_tables,
                    actual_tables=[],
                    comparison_notes=f"[Adversarial] Correct: Appropriately refused to generate SQL for trick question: '{question[:100]}...'",
                ),
            )

        # If SQL was generated for an adversarial query, that's WRONG
        return (
            AccuracyScore.WRONG,
            EvaluationFailureType.NONE,
            ComparisonDetails(
                expected_columns=expected_columns,
                actual_columns=[],
                expected_tables=expected_tables,
                actual_tables=[],
                sql_generated=sql,
                comparison_notes=f"[Adversarial] Wrong: Generated SQL for unanswerable trick question: '{question[:100]}...'",
            ),
        )

    def _llm_evaluate(
        self,
        question: str,
        expected_columns: list[str],
        expected_tables: list[str],
        sql: str,
        actual_columns: list[str],
    ) -> tuple[AccuracyScore, EvaluationFailureType, ComparisonDetails]:
        """Execute real evaluation using LLM.

        Args:
            question: Original natural language question
            expected_columns: Columns expected in result
            expected_tables: Tables expected in SQL
            sql: Generated SQL to evaluate
            actual_columns: Columns found in result

        Returns:
            Tuple of (accuracy_score, failure_type, comparison_details)
        """
        try:
            llm = self.llm
            if llm is None:
                logger.error("LLM not available - check configuration")
                return (
                    AccuracyScore.FAILED,
                    EvaluationFailureType.API_ERROR,
                    ComparisonDetails(
                        expected_columns=expected_columns,
                        actual_columns=actual_columns,
                        expected_tables=expected_tables,
                        sql_generated=sql,
                        comparison_notes="LLM not available for evaluation",
                    ),
                )

            # Build user prompt
            user_prompt = LLM_JUDGE_USER_PROMPT_TEMPLATE.format(
                question=question,
                expected_columns=", ".join(expected_columns) if expected_columns else "None specified",
                expected_tables=", ".join(expected_tables) if expected_tables else "None specified",
                sql=sql,
                actual_columns=", ".join(actual_columns) if actual_columns else "None found",
            )

            # Invoke LLM
            response = llm.invoke(
                [
                    SystemMessage(content=LLM_JUDGE_SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            )

            # Parse response
            judge_result = self._parse_llm_response(response.content)

            # Convert to standard return format
            accuracy = judge_result.to_accuracy_score()
            failure_type = EvaluationFailureType.NONE

            # Build comparison details with LLM judge information
            comparison = ComparisonDetails(
                expected_columns=expected_columns,
                actual_columns=actual_columns,
                missing_columns=judge_result.column_assessment.get("missing", []),
                extra_columns=judge_result.column_assessment.get("irrelevant_extra", []),
                expected_tables=expected_tables,
                sql_generated=sql,
                comparison_notes=f"[LLM Judge] {judge_result.reasoning}",
                judge_info={
                    "passed": judge_result.passed,
                    "score": judge_result.score,
                    "reasoning": judge_result.reasoning,
                },
            )

            return accuracy, failure_type, comparison

        except TimeoutError:
            logger.error("LLM evaluation timed out")
            return (
                AccuracyScore.FAILED,
                EvaluationFailureType.TIMEOUT,
                ComparisonDetails(
                    expected_columns=expected_columns,
                    actual_columns=actual_columns,
                    expected_tables=expected_tables,
                    sql_generated=sql,
                    comparison_notes="LLM evaluation timed out",
                ),
            )
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return (
                AccuracyScore.FAILED,
                EvaluationFailureType.API_ERROR,
                ComparisonDetails(
                    expected_columns=expected_columns,
                    actual_columns=actual_columns,
                    expected_tables=expected_tables,
                    sql_generated=sql,
                    comparison_notes=f"LLM evaluation error: {e}",
                ),
            )

    def _parse_llm_response(self, response_text: str) -> LLMJudgeResult:
        """Parse LLM response JSON.

        Handles JSON wrapped in markdown code blocks.

        Args:
            response_text: Raw LLM response text

        Returns:
            LLMJudgeResult with parsed data

        Raises:
            ValueError: If response cannot be parsed
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

            # Validate and extract fields
            accuracy = data.get("accuracy", "wrong").lower()
            if accuracy not in ("correct", "partial", "wrong"):
                logger.warning(f"Invalid accuracy value '{accuracy}', defaulting to 'wrong'")
                accuracy = "wrong"

            # Parse score and passed fields with validation
            score = data.get("score", 0)
            if not isinstance(score, int) or score < 1 or score > 5:
                # Derive score from accuracy if invalid
                score_mapping = {"correct": 5, "partial": 3, "wrong": 1}
                score = score_mapping.get(accuracy, 1)

            passed = data.get("passed", score >= 3)

            return LLMJudgeResult(
                accuracy=accuracy,
                reasoning=data.get("reasoning", "No reasoning provided"),
                column_assessment=data.get("column_assessment", {}),
                answers_question=data.get("answers_question", False),
                passed=passed,
                score=score,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM judge response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            # Return a default "wrong" result on parse failure
            return LLMJudgeResult(
                accuracy="wrong",
                reasoning=f"Failed to parse LLM response: {e}",
                column_assessment={},
                answers_question=False,
                passed=False,
                score=1,
            )

    def _mock_evaluate(
        self,
        question: str,
        expected_columns: list[str],
        expected_tables: list[str],
        sql: str,
        actual_columns: list[str],
        is_adversarial: bool = False,
    ) -> tuple[AccuracyScore, EvaluationFailureType, ComparisonDetails]:
        """Mock evaluation for testing without LLM API.

        Uses simple heuristics to simulate semantic matching:
        - Checks for substring containment between expected and actual columns
        - Produces deterministic results for testing

        Args:
            question: Original natural language question
            expected_columns: Columns expected in result
            expected_tables: Tables expected in SQL
            sql: Generated SQL to evaluate
            actual_columns: Columns found in result
            is_adversarial: Whether this is an adversarial test case

        Returns:
            Tuple of (accuracy_score, failure_type, comparison_details)
        """
        # Handle adversarial in mock mode (defensive - should be caught earlier)
        if is_adversarial:
            return self._evaluate_adversarial(question, sql, expected_columns, expected_tables)
        # Normalize column names for comparison
        expected_lower = [c.lower() for c in expected_columns]
        actual_lower = [c.lower() for c in actual_columns]

        # Simulate semantic matching with substring containment
        semantically_matched = []
        missing = []

        for exp in expected_lower:
            matched = False
            for act in actual_lower:
                # Check if one contains the other (semantic equivalence heuristic)
                if exp in act or act in exp:
                    semantically_matched.append(f"{exp}→{act}")
                    matched = True
                    break
            if not matched:
                missing.append(exp)

        # Calculate match percentage
        if expected_lower:
            match_pct = len(semantically_matched) / len(expected_lower)
        else:
            match_pct = 1.0 if not actual_lower else 0.5

        # Determine score and passed based on match percentage
        if match_pct >= 0.8:
            score = 5
            passed = True
            accuracy = AccuracyScore.CORRECT
            reasoning = "Mock judge: Semantic column matching indicates correct answer"
        elif match_pct >= 0.6:
            score = 4
            passed = True
            accuracy = AccuracyScore.CORRECT
            reasoning = f"Mock judge: Good match ({match_pct:.0%}), minor columns missing"
        elif match_pct >= 0.4:
            score = 3
            passed = True
            accuracy = AccuracyScore.PARTIAL
            reasoning = f"Mock judge: Partial match ({match_pct:.0%}), some expected columns missing"
        elif match_pct >= 0.2:
            score = 2
            passed = False
            accuracy = AccuracyScore.WRONG
            reasoning = f"Mock judge: Poor match ({match_pct:.0%}), most expected columns missing"
        else:
            score = 1
            passed = False
            accuracy = AccuracyScore.WRONG
            reasoning = f"Mock judge: Failed ({match_pct:.0%}), expected columns missing"

        # Build comparison details with judge info
        comparison = ComparisonDetails(
            expected_columns=expected_columns,
            actual_columns=actual_columns,
            missing_columns=[c for c in expected_columns if c.lower() in missing],
            extra_columns=[],  # Mock doesn't assess irrelevant extras
            expected_tables=expected_tables,
            sql_generated=sql,
            comparison_notes=f"[Mock LLM Judge] {reasoning}",
            judge_info={
                "passed": passed,
                "score": score,
                "reasoning": reasoning,
            },
        )

        return accuracy, EvaluationFailureType.NONE, comparison
