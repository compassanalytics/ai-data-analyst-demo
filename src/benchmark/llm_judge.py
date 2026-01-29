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
  "reasoning": "Brief explanation of your assessment (1-2 sentences)",
  "column_assessment": {
    "semantically_matched": ["expected_col→actual_col pairs that match semantically"],
    "missing": ["expected columns not present even semantically"],
    "irrelevant_extra": ["extra columns that don't help answer the question"]
  },
  "answers_question": true | false
}
```

## Scoring Guide

- **correct**: SQL fully answers the question. All key expected columns present (semantic matches count). Query logic is correct. Extra helpful columns are OK.
- **partial**: SQL partially answers but has minor issues:
  - Missing 1-2 non-critical columns
  - Has correct core logic but missing some refinement
  - Answers the question but with extra irrelevant data
- **wrong**: SQL does not answer the question:
  - Fundamentally wrong aggregation or logic
  - Missing critical columns that are central to the question
  - Wrong tables or joins producing incorrect results
  - Query retrieves different data than what was asked"""


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
    """

    accuracy: str  # "correct", "partial", "wrong"
    reasoning: str
    column_assessment: dict[str, Any] = field(default_factory=dict)
    answers_question: bool = False

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

    Uses ChatDatabricks to assess whether generated SQL correctly answers
    the original question, with semantic understanding of column equivalence.

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

    def __init__(
        self,
        config: Config,
        model_override: str | None = None,
    ):
        """Initialize LLM judge evaluator.

        Args:
            config: Configuration with model endpoint settings
            model_override: Optional model endpoint to use instead of config default
        """
        self.config = config
        self._model_endpoint = model_override or config.model_endpoint
        self._llm = None
        self._temperature = 0.0  # Deterministic for consistent evaluation

    @property
    def model_endpoint(self) -> str:
        """Get the model endpoint being used."""
        return self._model_endpoint

    @property
    def llm(self):
        """Lazy-load ChatDatabricks LLM."""
        if self._llm is None and not self.config.mock_mode:
            from databricks_langchain import ChatDatabricks

            self._llm = ChatDatabricks(
                endpoint=self._model_endpoint,
                temperature=self._temperature,
            )
        return self._llm

    def evaluate(
        self,
        question: str,
        expected_columns: list[str],
        expected_tables: list[str],
        sql: str | None,
        actual_columns: list[str],
    ) -> tuple[AccuracyScore, EvaluationFailureType, ComparisonDetails]:
        """Evaluate SQL correctness using LLM judge.

        Args:
            question: Original natural language question
            expected_columns: Columns expected in result
            expected_tables: Tables expected in SQL
            sql: Generated SQL to evaluate (None if generation failed)
            actual_columns: Columns found in result

        Returns:
            Tuple of (accuracy_score, failure_type, comparison_details)
        """
        # Handle no SQL case
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
            return self._mock_evaluate(question, expected_columns, expected_tables, sql, actual_columns)
        return self._llm_evaluate(question, expected_columns, expected_tables, sql, actual_columns)

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

            return LLMJudgeResult(
                accuracy=accuracy,
                reasoning=data.get("reasoning", "No reasoning provided"),
                column_assessment=data.get("column_assessment", {}),
                answers_question=data.get("answers_question", False),
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
            )

    def _mock_evaluate(
        self,
        question: str,
        expected_columns: list[str],
        expected_tables: list[str],
        sql: str,
        actual_columns: list[str],
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

        Returns:
            Tuple of (accuracy_score, failure_type, comparison_details)
        """
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

        # Determine accuracy based on match percentage
        if match_pct >= 0.8:
            accuracy = AccuracyScore.CORRECT
            reasoning = "Mock judge: Semantic column matching indicates correct answer"
        elif match_pct >= 0.5:
            accuracy = AccuracyScore.PARTIAL
            reasoning = f"Mock judge: Partial match ({match_pct:.0%}), some expected columns missing"
        else:
            accuracy = AccuracyScore.WRONG
            reasoning = f"Mock judge: Poor match ({match_pct:.0%}), most expected columns missing"

        # Build comparison details
        comparison = ComparisonDetails(
            expected_columns=expected_columns,
            actual_columns=actual_columns,
            missing_columns=[c for c in expected_columns if c.lower() in missing],
            extra_columns=[],  # Mock doesn't assess irrelevant extras
            expected_tables=expected_tables,
            sql_generated=sql,
            comparison_notes=f"[Mock LLM Judge] {reasoning}",
        )

        return accuracy, EvaluationFailureType.NONE, comparison
