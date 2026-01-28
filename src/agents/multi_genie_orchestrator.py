"""Multi-Genie Orchestrator - Parallel query execution across multiple Genie Spaces.

This module provides orchestration capabilities for querying multiple Databricks Genie Spaces
in parallel, with support for retries, timeouts, and progress tracking.
"""

from __future__ import annotations

import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.config import Config
from src.agents.genie_agent import GenieDataAgent, GenieResult


@dataclass
class GenieSpaceConfig:
    """Configuration for a single Genie Space.

    Attributes:
        space_id: The Genie Space ID
        name: Human-readable name for this space
        domain: Comma-separated keywords describing the data domain
        timeout_seconds: Maximum time to wait for query completion
        retry_count: Number of retries on failure
        retry_delay: Base delay between retries (with jitter)
    """

    space_id: str
    name: str
    domain: str = ""
    timeout_seconds: int = 120
    retry_count: int = 2
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.space_id or not self.space_id.strip():
            raise ValueError("space_id is required and cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("name is required and cannot be empty")
        self.space_id = self.space_id.strip()
        self.name = self.name.strip()


@dataclass
class ResultMetadata:
    """Metadata about a query execution.

    Attributes:
        space_id: The Genie Space ID that was queried
        space_name: Human-readable name of the space
        domain: The domain keywords for this space
        query_time_seconds: Total time taken for the query
        success: Whether the query succeeded
        retries_used: Number of retries that were needed
    """

    space_id: str
    space_name: str
    domain: str
    query_time_seconds: float
    success: bool
    retries_used: int = 0


@dataclass
class MultiGenieResult:
    """Aggregated results from querying multiple Genie Spaces.

    Attributes:
        results: Query results keyed by space name
        metadata: Query metadata keyed by space name
        errors: List of error messages encountered
    """

    results: dict[str, GenieResult] = field(default_factory=dict)
    metadata: dict[str, ResultMetadata] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def overall_success(self) -> bool:
        """Check if all queries succeeded."""
        if not self.results:
            return False
        return all(r.success for r in self.results.values())

    @property
    def partial_success(self) -> bool:
        """Check if some but not all queries succeeded."""
        if not self.results:
            return False
        successes = [r.success for r in self.results.values()]
        return any(successes) and not all(successes)

    @property
    def any_success(self) -> bool:
        """Check if at least one query succeeded."""
        return any(r.success for r in self.results.values())

    def get_by_name(self, name: str) -> Optional[GenieResult]:
        """Get result by space name.

        Args:
            name: The space name to look up

        Returns:
            GenieResult if found, None otherwise
        """
        return self.results.get(name)

    def get_by_domain(self, domain_keyword: str) -> list[GenieResult]:
        """Get results by domain keyword.

        Args:
            domain_keyword: Keyword to match against space domains

        Returns:
            List of matching GenieResults
        """
        keyword_lower = domain_keyword.lower()
        matching_results = []
        for name, meta in self.metadata.items():
            if keyword_lower in meta.domain.lower():
                result = self.results.get(name)
                if result:
                    matching_results.append(result)
        return matching_results

    def successful_results(self) -> dict[str, GenieResult]:
        """Get only the successful results.

        Returns:
            Dictionary of successful results keyed by space name
        """
        return {name: result for name, result in self.results.items() if result.success}

    def to_combined_markdown(self, max_rows_per_space: int = 5) -> str:
        """Combine all results into a single markdown document.

        Args:
            max_rows_per_space: Maximum rows to show per space

        Returns:
            Combined markdown string
        """
        sections = []

        for name, result in self.results.items():
            meta = self.metadata.get(name)
            domain_info = f" ({meta.domain})" if meta and meta.domain else ""
            timing = f" - {meta.query_time_seconds:.2f}s" if meta else ""

            section = f"## {name}{domain_info}{timing}\n\n"

            if result.success:
                if result.description:
                    section += f"*{result.description}*\n\n"
                section += result.to_markdown_table(max_rows=max_rows_per_space)
                if result.sql:
                    section += f"\n\n<details><summary>SQL</summary>\n\n```sql\n{result.sql}\n```\n\n</details>"
            else:
                section += f"**Error:** {result.error}"

            sections.append(section)

        if self.errors:
            error_section = "## Errors\n\n"
            for error in self.errors:
                error_section += f"- {error}\n"
            sections.append(error_section)

        return "\n\n---\n\n".join(sections)


class MultiGenieOrchestrator:
    """Orchestrator for parallel queries across multiple Genie Spaces.

    Supports querying multiple Genie Spaces concurrently with configurable
    retries, timeouts, and progress tracking.

    Example:
        >>> configs = [
        ...     GenieSpaceConfig(space_id="abc123", name="Sales", domain="sales, revenue"),
        ...     GenieSpaceConfig(space_id="def456", name="Customers", domain="customers"),
        ... ]
        >>> orchestrator = MultiGenieOrchestrator(configs)
        >>> result = orchestrator.query_all("What is the total count?")
        >>> print(result.to_combined_markdown())
    """

    def __init__(
        self,
        space_configs: list[GenieSpaceConfig],
        base_config: Optional[Config] = None,
        max_concurrency: int = 3,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ):
        """Initialize the Multi-Genie Orchestrator.

        Args:
            space_configs: List of Genie Space configurations
            base_config: Base configuration (uses Config.from_env() if not provided)
            max_concurrency: Maximum number of parallel queries
            progress_callback: Optional callback for progress updates (space_name, status)

        Raises:
            ValueError: If no space configurations are provided
        """
        if not space_configs:
            raise ValueError("At least one GenieSpaceConfig is required")

        self._configs: dict[str, GenieSpaceConfig] = {c.name: c for c in space_configs}
        self._base_config = base_config or Config.from_env()
        self._max_concurrency = max_concurrency
        self._progress_callback = progress_callback
        self._agents: dict[str, GenieDataAgent] = {}

    def _get_agent(self, space_config: GenieSpaceConfig) -> GenieDataAgent:
        """Get or create a GenieDataAgent for a space.

        Args:
            space_config: Configuration for the space

        Returns:
            GenieDataAgent instance for the space
        """
        if space_config.name not in self._agents:
            # Create a config copy with this space's ID
            config = Config(
                databricks_host=self._base_config.databricks_host,
                databricks_token=self._base_config.databricks_token,
                genie_space_id=space_config.space_id,
                warehouse_id=self._base_config.warehouse_id,
                model_endpoint=self._base_config.model_endpoint,
                mock_mode=self._base_config.mock_mode,
                vector_search_endpoint=self._base_config.vector_search_endpoint,
                vector_search_index=self._base_config.vector_search_index,
                embedding_endpoint=self._base_config.embedding_endpoint,
            )
            self._agents[space_config.name] = GenieDataAgent(config)

        return self._agents[space_config.name]

    def _notify_progress(self, space_name: str, status: str) -> None:
        """Send progress notification via callback.

        Args:
            space_name: Name of the space
            status: Status message
        """
        if self._progress_callback:
            try:
                self._progress_callback(space_name, status)
            except Exception:
                # Swallow callback errors to avoid disrupting queries
                pass

    def _query_space_with_retry(
        self,
        space_config: GenieSpaceConfig,
        question: str,
    ) -> tuple[GenieResult, float, int]:
        """Query a single space with retry logic.

        Args:
            space_config: Configuration for the space
            question: The natural language question

        Returns:
            Tuple of (result, elapsed_seconds, retries_used)
        """
        start_time = time.time()
        timeout_deadline = start_time + space_config.timeout_seconds
        agent = self._get_agent(space_config)
        retries_used = 0
        last_result: Optional[GenieResult] = None

        for attempt in range(space_config.retry_count + 1):
            # Check if we've exceeded the overall timeout
            elapsed = time.time() - start_time
            remaining_time = timeout_deadline - time.time()

            if remaining_time <= 0:
                elapsed = time.time() - start_time
                return GenieResult(
                    success=False,
                    error=f"Timeout after {elapsed:.2f}s"
                ), elapsed, retries_used

            self._notify_progress(space_config.name, f"Querying (attempt {attempt + 1})")

            try:
                # Use the remaining time as the query timeout
                effective_timeout = min(
                    int(remaining_time),
                    space_config.timeout_seconds
                )
                result = agent.query(
                    question,
                    timeout_seconds=effective_timeout,
                )

                if result.success:
                    elapsed = time.time() - start_time
                    self._notify_progress(space_config.name, "Complete")
                    return result, elapsed, retries_used

                last_result = result

            except Exception as e:
                last_result = GenieResult(success=False, error=str(e))

            # Retry logic (if not the last attempt)
            if attempt < space_config.retry_count:
                retries_used += 1
                # Add jitter to retry delay
                delay = space_config.retry_delay * (1 + random.uniform(-0.1, 0.1))
                self._notify_progress(space_config.name, f"Retrying in {delay:.1f}s")
                time.sleep(delay)

        elapsed = time.time() - start_time
        self._notify_progress(space_config.name, "Failed")
        return last_result or GenieResult(success=False, error="Unknown error"), elapsed, retries_used

    def query_all(self, question: str) -> MultiGenieResult:
        """Query all configured spaces in parallel.

        Args:
            question: Natural language question to ask all spaces

        Returns:
            MultiGenieResult with results from all spaces
        """
        return self._execute_parallel_queries(question, list(self._configs.values()))

    def query_spaces(
        self,
        question: str,
        space_names: Optional[list[str]] = None,
        space_ids: Optional[list[str]] = None,
    ) -> MultiGenieResult:
        """Query specific spaces by name or ID.

        Args:
            question: Natural language question
            space_names: List of space names to query (optional)
            space_ids: List of space IDs to query (optional)

        Returns:
            MultiGenieResult with results from matching spaces
        """
        configs_to_query = []

        if space_names:
            for name in space_names:
                if name in self._configs:
                    configs_to_query.append(self._configs[name])

        if space_ids:
            for config in self._configs.values():
                if config.space_id in space_ids and config not in configs_to_query:
                    configs_to_query.append(config)

        if not configs_to_query:
            result = MultiGenieResult()
            result.errors.append("No matching spaces found for the given names or IDs")
            return result

        return self._execute_parallel_queries(question, configs_to_query)

    def query_by_domain(self, question: str, domain_keywords: list[str]) -> MultiGenieResult:
        """Query spaces matching domain keywords.

        Args:
            question: Natural language question
            domain_keywords: Keywords to match against space domains

        Returns:
            MultiGenieResult with results from matching spaces
        """
        configs_to_query = []
        keywords_lower = [kw.lower() for kw in domain_keywords]

        for config in self._configs.values():
            domain_lower = config.domain.lower()
            if any(kw in domain_lower for kw in keywords_lower):
                configs_to_query.append(config)

        if not configs_to_query:
            result = MultiGenieResult()
            result.errors.append(f"No spaces found matching domains: {', '.join(domain_keywords)}")
            return result

        return self._execute_parallel_queries(question, configs_to_query)

    def _execute_parallel_queries(
        self,
        question: str,
        configs: list[GenieSpaceConfig],
    ) -> MultiGenieResult:
        """Execute queries in parallel across multiple spaces.

        Args:
            question: Natural language question
            configs: List of space configurations to query

        Returns:
            MultiGenieResult with all results
        """
        result = MultiGenieResult()

        with ThreadPoolExecutor(max_workers=self._max_concurrency) as executor:
            # Submit all queries
            future_to_config = {
                executor.submit(
                    self._query_space_with_retry,
                    config,
                    question,
                ): config
                for config in configs
            }

            # Collect results as they complete
            for future in as_completed(future_to_config):
                config = future_to_config[future]

                try:
                    query_result, elapsed, retries = future.result(
                        timeout=config.timeout_seconds
                    )

                    result.results[config.name] = query_result
                    result.metadata[config.name] = ResultMetadata(
                        space_id=config.space_id,
                        space_name=config.name,
                        domain=config.domain,
                        query_time_seconds=elapsed,
                        success=query_result.success,
                        retries_used=retries,
                    )

                except FuturesTimeoutError:
                    error_msg = f"Space '{config.name}' timed out after {config.timeout_seconds}s"
                    result.errors.append(error_msg)
                    result.results[config.name] = GenieResult(
                        success=False,
                        error=error_msg,
                    )
                    result.metadata[config.name] = ResultMetadata(
                        space_id=config.space_id,
                        space_name=config.name,
                        domain=config.domain,
                        query_time_seconds=config.timeout_seconds,
                        success=False,
                        retries_used=0,
                    )

                except Exception as e:
                    error_msg = f"Space '{config.name}' failed: {e}"
                    result.errors.append(error_msg)
                    result.results[config.name] = GenieResult(
                        success=False,
                        error=str(e),
                    )
                    result.metadata[config.name] = ResultMetadata(
                        space_id=config.space_id,
                        space_name=config.name,
                        domain=config.domain,
                        query_time_seconds=0,
                        success=False,
                        retries_used=0,
                    )

        return result

    def get_space_status(self) -> dict[str, dict[str, Any]]:
        """Get status information for all configured spaces.

        Returns:
            Dictionary of space status keyed by name
        """
        status = {}
        for name, config in self._configs.items():
            has_agent = name in self._agents
            agent = self._agents.get(name)

            status[name] = {
                "space_id": config.space_id,
                "domain": config.domain,
                "timeout_seconds": config.timeout_seconds,
                "retry_count": config.retry_count,
                "agent_initialized": has_agent,
                "conversation_id": agent.get_conversation_id() if agent else None,
            }

        return status

    def reset_all_conversations(self) -> None:
        """Reset conversation state for all cached agents."""
        for agent in self._agents.values():
            agent.reset_conversation()
