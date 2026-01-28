"""Genie Evaluator for the Testing and Evaluation Framework.

This module provides the core evaluation logic for assessing Genie query
performance against test suites. Handles query execution, result comparison,
failure classification, and summary generation.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from src.agents.genie_agent import GenieDataAgent, GenieResult
from src.config import Config
from src.evaluation.models import (
    AccuracyScore,
    ComparisonDetails,
    EvaluationFailureType,
    EvaluationResult,
    EvaluationSummary,
    FailureCategory,
    TestQuery,
)
from src.utils.errors import ErrorCategory


@dataclass
class EvaluationResults:
    """Container for evaluation results.

    Attributes:
        results: List of individual evaluation results
        summary: Aggregated summary statistics
    """

    results: list[EvaluationResult] = field(default_factory=list)
    summary: Optional[EvaluationSummary] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of all results
        """
        return {
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary.to_dict() if self.summary else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationResults:
        """Create from dictionary.

        Args:
            data: Dictionary containing evaluation results data

        Returns:
            EvaluationResults instance
        """
        return cls(
            results=[EvaluationResult.from_dict(r) for r in data.get("results", [])],
            summary=EvaluationSummary.from_dict(data["summary"]) if data.get("summary") else None,
        )


class GenieEvaluator:
    """Evaluator for Genie query performance.

    Executes test queries against a Genie Space and evaluates the results
    for accuracy, comparing generated SQL against expected patterns.

    Example:
        >>> config = Config(genie_space_id="abc123", mock_mode=True)
        >>> evaluator = GenieEvaluator(config)
        >>> results = evaluator.evaluate(test_queries)
        >>> print(f"Accuracy: {results.summary.overall_accuracy:.1f}%")
    """

    def __init__(
        self,
        config: Config,
        genie_agent: Optional[GenieDataAgent] = None,
    ) -> None:
        """Initialize the evaluator.

        Args:
            config: Configuration instance with Genie settings
            genie_agent: Optional pre-configured GenieDataAgent (creates one if not provided)
        """
        self.config = config
        self._genie = genie_agent or GenieDataAgent(config)

    def evaluate(
        self,
        test_queries: list[TestQuery],
        progress_callback: Optional[Callable[[int, int, TestQuery], None]] = None,
        fresh: bool = True,
    ) -> EvaluationResults:
        """Evaluate a list of test queries.

        Args:
            test_queries: List of test queries to evaluate
            progress_callback: Optional callback(current, total, query) for progress updates
            fresh: If True, bypass cache for each query (recommended for evaluation)

        Returns:
            EvaluationResults containing individual results and summary
        """
        started_at = datetime.now().isoformat()
        results: list[EvaluationResult] = []

        for idx, test_query in enumerate(test_queries):
            if progress_callback:
                progress_callback(idx + 1, len(test_queries), test_query)

            result = self.evaluate_single(test_query, fresh=fresh)
            results.append(result)

        completed_at = datetime.now().isoformat()

        # Build summary
        summary = self._build_summary(results)
        summary.started_at = started_at
        summary.completed_at = completed_at
        summary.space_id = self.config.genie_space_id

        return EvaluationResults(results=results, summary=summary)

    def evaluate_single(
        self,
        test_query: TestQuery,
        fresh: bool = True,
    ) -> EvaluationResult:
        """Evaluate a single test query.

        CRITICAL: Resets conversation before each query to ensure clean state.

        Args:
            test_query: The test query to evaluate
            fresh: If True, bypass cache (recommended for evaluation)

        Returns:
            EvaluationResult for the query
        """
        # Reset conversation to ensure clean state
        self._genie.reset_conversation()

        start_time = time.time()

        try:
            # Execute the query
            genie_result = self._genie.query(
                test_query.question,
                fresh=fresh,
            )

            execution_time_ms = (time.time() - start_time) * 1000

            # Compare results
            accuracy, failure_type, comparison = self._compare_results(
                test_query, genie_result
            )

            # Build raw response for debugging
            raw_response = {
                "success": genie_result.success,
                "sql": genie_result.sql,
                "description": genie_result.description,
                "columns": genie_result.columns,
                "data_count": len(genie_result.data) if genie_result.data else 0,
                "error": genie_result.error,
                "from_cache": genie_result.from_cache,
            }

            return EvaluationResult(
                test_query=test_query,
                accuracy=accuracy,
                failure_type=failure_type,
                comparison=comparison,
                execution_time_ms=execution_time_ms,
                genie_response_raw=raw_response,
                error_message=genie_result.error if not genie_result.success else None,
                error_category=(
                    genie_result.error_details.category.value
                    if genie_result.error_details
                    else None
                ),
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000

            return EvaluationResult(
                test_query=test_query,
                accuracy=AccuracyScore.FAILED,
                failure_type=EvaluationFailureType.API_ERROR,
                comparison=ComparisonDetails(
                    comparison_notes=f"Exception during evaluation: {e}"
                ),
                execution_time_ms=execution_time_ms,
                error_message=str(e),
            )

    def _compare_results(
        self,
        test_query: TestQuery,
        genie_result: GenieResult,
    ) -> tuple[AccuracyScore, EvaluationFailureType, ComparisonDetails]:
        """Compare Genie result against expected values.

        Args:
            test_query: The test query with expectations
            genie_result: The result from Genie

        Returns:
            Tuple of (accuracy_score, failure_type, comparison_details)
        """
        # Handle failed queries
        if not genie_result.success:
            failure_type = self._classify_error_failure(genie_result)
            return (
                AccuracyScore.FAILED,
                failure_type,
                ComparisonDetails(
                    expected_columns=test_query.expected_columns,
                    expected_tables=test_query.expected_tables,
                    comparison_notes=f"Query failed: {genie_result.error}",
                ),
            )

        # Handle cases where no SQL was generated
        if genie_result.sql is None:
            return (
                AccuracyScore.FAILED,
                EvaluationFailureType.NO_SQL_GENERATED,
                ComparisonDetails(
                    expected_columns=test_query.expected_columns,
                    expected_tables=test_query.expected_tables,
                    comparison_notes="No SQL was generated by Genie",
                ),
            )

        # Extract columns and tables from generated SQL
        actual_columns = self._extract_columns_from_sql(genie_result.sql)
        actual_tables = self._extract_tables_from_sql(genie_result.sql)

        # Build comparison details
        comparison = ComparisonDetails(
            expected_columns=test_query.expected_columns,
            actual_columns=list(actual_columns),
            expected_tables=test_query.expected_tables,
            actual_tables=list(actual_tables),
            sql_generated=genie_result.sql,
        )

        # Check column presence (case-insensitive, partial matching)
        expected_cols_lower = {c.lower() for c in test_query.expected_columns}
        actual_cols_lower = {c.lower() for c in actual_columns}

        # Semantic column matching - check if any expected column is present
        # (allowing for variations like "total_revenue" matching "revenue")
        columns_matched = 0
        columns_expected = len(expected_cols_lower)

        for expected_col in expected_cols_lower:
            for actual_col in actual_cols_lower:
                if expected_col in actual_col or actual_col in expected_col:
                    columns_matched += 1
                    break

        # Check table presence (case-insensitive, partial matching)
        expected_tables_lower = {t.lower() for t in test_query.expected_tables}
        actual_tables_lower = {t.lower() for t in actual_tables}

        tables_matched = 0
        tables_expected = len(expected_tables_lower)

        for expected_table in expected_tables_lower:
            for actual_table in actual_tables_lower:
                if expected_table in actual_table or actual_table in expected_table:
                    tables_matched += 1
                    break

        # Calculate match percentages
        col_match_pct = columns_matched / columns_expected if columns_expected > 0 else 1.0
        table_match_pct = tables_matched / tables_expected if tables_expected > 0 else 1.0

        # Determine accuracy score
        # CORRECT: >= 80% of expected columns and tables are present
        # PARTIAL: >= 50% of expected columns and tables are present
        # WRONG: < 50%

        avg_match = (col_match_pct + table_match_pct) / 2

        if avg_match >= 0.8:
            accuracy = AccuracyScore.CORRECT
            failure_type = EvaluationFailureType.NONE
        elif avg_match >= 0.5:
            accuracy = AccuracyScore.PARTIAL
            failure_type = self._classify_failure(test_query, comparison)
        else:
            accuracy = AccuracyScore.WRONG
            failure_type = self._classify_failure(test_query, comparison)

        # Update comparison notes
        comparison.comparison_notes = (
            f"Column match: {columns_matched}/{columns_expected} ({col_match_pct:.0%}), "
            f"Table match: {tables_matched}/{tables_expected} ({table_match_pct:.0%})"
        )

        # Update missing/extra lists
        comparison.missing_columns = [
            c for c in test_query.expected_columns
            if not any(c.lower() in ac.lower() or ac.lower() in c.lower() for ac in actual_columns)
        ]
        comparison.extra_columns = [
            c for c in actual_columns
            if not any(c.lower() in ec.lower() or ec.lower() in c.lower() for ec in test_query.expected_columns)
        ]
        comparison.missing_tables = [
            t for t in test_query.expected_tables
            if not any(t.lower() in at.lower() or at.lower() in t.lower() for at in actual_tables)
        ]
        comparison.extra_tables = [
            t for t in actual_tables
            if not any(t.lower() in et.lower() or et.lower() in t.lower() for et in test_query.expected_tables)
        ]

        return accuracy, failure_type, comparison

    def _extract_columns_from_sql(self, sql: str) -> set[str]:
        """Extract column names from SQL query (case-insensitive).

        Args:
            sql: The SQL query string

        Returns:
            Set of column names found in SELECT clause and elsewhere
        """
        columns: set[str] = set()

        # Normalize SQL
        sql_upper = sql.upper()

        # Extract from SELECT clause
        select_match = re.search(
            r'SELECT\s+(.*?)\s+FROM',
            sql_upper,
            re.IGNORECASE | re.DOTALL
        )

        if select_match:
            select_clause = select_match.group(1)

            # Handle SELECT *
            if '*' in select_clause:
                columns.add('*')

            # Extract column names and aliases
            # Pattern matches: column_name, table.column, column AS alias, etc.
            col_patterns = [
                r'(\w+)\s+AS\s+(\w+)',  # column AS alias
                r'(\w+)\.(\w+)',  # table.column
                r'\b(\w+)\b',  # simple column name
            ]

            for pattern in col_patterns:
                matches = re.findall(pattern, select_clause, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        for part in match:
                            if part.lower() not in {'as', 'from', 'select', 'distinct', 'all'}:
                                columns.add(part.lower())
                    else:
                        if match.lower() not in {'as', 'from', 'select', 'distinct', 'all'}:
                            columns.add(match.lower())

        # Also extract from GROUP BY, ORDER BY clauses
        for clause in ['GROUP BY', 'ORDER BY']:
            clause_match = re.search(
                rf'{clause}\s+([\w\s,\.]+?)(?:HAVING|ORDER|LIMIT|$)',
                sql_upper,
                re.IGNORECASE
            )
            if clause_match:
                clause_content = clause_match.group(1)
                words = re.findall(r'\b(\w+)\b', clause_content)
                for word in words:
                    if word.lower() not in {'by', 'asc', 'desc', 'nulls', 'first', 'last'}:
                        columns.add(word.lower())

        # Remove SQL keywords that might have been captured
        sql_keywords = {
            'select', 'from', 'where', 'and', 'or', 'not', 'in', 'is', 'null',
            'between', 'like', 'case', 'when', 'then', 'else', 'end', 'as',
            'sum', 'count', 'avg', 'min', 'max', 'distinct', 'group', 'by',
            'order', 'having', 'limit', 'offset', 'join', 'left', 'right',
            'inner', 'outer', 'on', 'using', 'union', 'intersect', 'except',
            'true', 'false', 'over', 'partition', 'row_number', 'rank',
        }

        columns = {c for c in columns if c not in sql_keywords}

        return columns

    def _extract_tables_from_sql(self, sql: str) -> set[str]:
        """Extract table names from SQL query (case-insensitive).

        Args:
            sql: The SQL query string

        Returns:
            Set of table names found in FROM and JOIN clauses
        """
        tables: set[str] = set()

        # Pattern for FROM clause tables (including schema.table)
        from_pattern = r'FROM\s+([\w\.]+)'
        matches = re.findall(from_pattern, sql, re.IGNORECASE)
        for match in matches:
            # Handle schema.table format
            parts = match.split('.')
            tables.add(parts[-1].lower())  # Add just the table name

        # Pattern for JOIN clause tables
        join_pattern = r'JOIN\s+([\w\.]+)'
        matches = re.findall(join_pattern, sql, re.IGNORECASE)
        for match in matches:
            parts = match.split('.')
            tables.add(parts[-1].lower())

        # Also check for subquery aliases (just in case)
        # Skip common SQL keywords
        sql_keywords = {
            'select', 'from', 'where', 'and', 'or', 'not', 'in', 'is', 'null',
            'join', 'left', 'right', 'inner', 'outer', 'on', 'using',
        }

        tables = {t for t in tables if t not in sql_keywords}

        return tables

    def _classify_error_failure(self, genie_result: GenieResult) -> EvaluationFailureType:
        """Classify failure type based on error details.

        Args:
            genie_result: The failed Genie result

        Returns:
            The appropriate EvaluationFailureType
        """
        if genie_result.error_details:
            category = genie_result.error_details.category

            if category == ErrorCategory.TIMEOUT:
                return EvaluationFailureType.TIMEOUT
            elif category == ErrorCategory.PARSE:
                return EvaluationFailureType.PARSE_ERROR
            elif category in {ErrorCategory.AUTH, ErrorCategory.NETWORK, ErrorCategory.SPACE_UNAVAILABLE}:
                return EvaluationFailureType.API_ERROR

        # Check error message for hints
        error_lower = (genie_result.error or "").lower()

        if "timeout" in error_lower:
            return EvaluationFailureType.TIMEOUT
        elif "parse" in error_lower or "syntax" in error_lower:
            return EvaluationFailureType.PARSE_ERROR

        return EvaluationFailureType.API_ERROR

    def _classify_failure(
        self,
        test_query: TestQuery,
        comparison: ComparisonDetails,
    ) -> EvaluationFailureType:
        """Classify the type of failure based on comparison results.

        Args:
            test_query: The test query
            comparison: The comparison details

        Returns:
            The most likely EvaluationFailureType
        """
        # Check what's missing
        has_missing_columns = len(comparison.missing_columns) > 0
        has_missing_tables = len(comparison.missing_tables) > 0

        # Map failure categories to likely failure types
        category = test_query.failure_category

        if category == FailureCategory.AMBIGUOUS_COLUMNS:
            if has_missing_columns:
                return EvaluationFailureType.WRONG_COLUMNS
        elif category == FailureCategory.AGGREGATION_AMBIGUITY:
            return EvaluationFailureType.WRONG_AGGREGATION
        elif category == FailureCategory.JOIN_COMPLEXITY:
            if has_missing_tables:
                return EvaluationFailureType.WRONG_JOIN
            return EvaluationFailureType.WRONG_JOIN
        elif category == FailureCategory.TEMPORAL_CONFUSION:
            return EvaluationFailureType.WRONG_FILTER
        elif category == FailureCategory.BUSINESS_LOGIC:
            return EvaluationFailureType.WRONG_FILTER
        elif category == FailureCategory.CRYPTIC_CODES:
            return EvaluationFailureType.WRONG_FILTER

        # Default based on what's missing
        if has_missing_columns:
            return EvaluationFailureType.WRONG_COLUMNS
        elif has_missing_tables:
            return EvaluationFailureType.WRONG_TABLES

        return EvaluationFailureType.UNKNOWN

    def _build_summary(self, results: list[EvaluationResult]) -> EvaluationSummary:
        """Build summary statistics from evaluation results.

        Args:
            results: List of evaluation results

        Returns:
            EvaluationSummary with aggregated statistics
        """
        summary = EvaluationSummary(
            total_queries=len(results),
        )

        # Initialize counters
        accuracy_by_type: dict[str, dict[str, int]] = {}
        accuracy_by_complexity: dict[str, dict[str, int]] = {}
        accuracy_by_category: dict[str, dict[str, int]] = {}
        failure_counts: dict[str, int] = {}

        total_time = 0.0

        for result in results:
            # Count accuracy scores
            if result.accuracy == AccuracyScore.CORRECT:
                summary.correct_count += 1
            elif result.accuracy == AccuracyScore.PARTIAL:
                summary.partial_count += 1
            elif result.accuracy == AccuracyScore.WRONG:
                summary.wrong_count += 1
            elif result.accuracy == AccuracyScore.FAILED:
                summary.failed_count += 1

            # Track by query type
            type_key = result.test_query.query_type.value
            if type_key not in accuracy_by_type:
                accuracy_by_type[type_key] = {"correct": 0, "partial": 0, "wrong": 0, "failed": 0, "total": 0}
            accuracy_by_type[type_key][result.accuracy.value] += 1
            accuracy_by_type[type_key]["total"] += 1

            # Track by complexity
            comp_key = result.test_query.complexity.value
            if comp_key not in accuracy_by_complexity:
                accuracy_by_complexity[comp_key] = {"correct": 0, "partial": 0, "wrong": 0, "failed": 0, "total": 0}
            accuracy_by_complexity[comp_key][result.accuracy.value] += 1
            accuracy_by_complexity[comp_key]["total"] += 1

            # Track by failure category
            cat_key = result.test_query.failure_category.value
            if cat_key not in accuracy_by_category:
                accuracy_by_category[cat_key] = {"correct": 0, "partial": 0, "wrong": 0, "failed": 0, "total": 0}
            accuracy_by_category[cat_key][result.accuracy.value] += 1
            accuracy_by_category[cat_key]["total"] += 1

            # Track failure types
            if result.failure_type != EvaluationFailureType.NONE:
                failure_key = result.failure_type.value
                failure_counts[failure_key] = failure_counts.get(failure_key, 0) + 1

            # Track timing
            total_time += result.execution_time_ms

        # Set summary fields
        summary.accuracy_by_query_type = accuracy_by_type
        summary.accuracy_by_complexity = accuracy_by_complexity
        summary.accuracy_by_failure_category = accuracy_by_category
        summary.failure_type_counts = failure_counts
        summary.total_execution_time_ms = total_time
        summary.average_execution_time_ms = total_time / len(results) if results else 0.0

        return summary
