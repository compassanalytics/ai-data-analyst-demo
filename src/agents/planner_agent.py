"""Planner Agent for query decomposition into domain-specific sub-queries.

This module provides a PlannerAgent that analyzes complex user questions and
decomposes them into domain-specific sub-queries targeting appropriate Genie Spaces.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.config import Config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.agents.multi_genie_orchestrator import GenieSpaceConfig, MultiGenieOrchestrator, MultiGenieResult


@dataclass
class SubQuery:
    """A domain-specific sub-query targeting a specific Genie Space.

    Attributes:
        id: Unique identifier for dependency references
        target_space: Exact Genie Space name (must match configured space names)
        query: The question to ask this space
        priority: Execution priority (1 = highest, higher numbers run later)
        depends_on: List of SubQuery IDs this query depends on
    """

    id: str
    target_space: str
    query: str
    priority: int = 1
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all SubQuery fields
        """
        return {
            "id": self.id,
            "target_space": self.target_space,
            "query": self.query,
            "priority": self.priority,
            "depends_on": self.depends_on,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubQuery:
        """Create SubQuery from dictionary.

        Args:
            data: Dictionary with SubQuery fields

        Returns:
            SubQuery instance
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            target_space=data["target_space"],
            query=data["query"],
            priority=data.get("priority", 1),
            depends_on=data.get("depends_on", []),
        )


@dataclass
class Plan:
    """A decomposed query plan with sub-queries and synthesis instructions.

    Attributes:
        original_question: The original user question
        sub_queries: List of domain-specific sub-queries
        synthesis_instructions: Instructions for combining results
        metadata: Additional metadata about the plan
    """

    original_question: str
    sub_queries: list[SubQuery]
    synthesis_instructions: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def target_spaces(self) -> list[str]:
        """Get unique target space names in priority order.

        Returns:
            List of unique space names sorted by priority
        """
        seen = set()
        spaces = []
        for sq in sorted(self.sub_queries, key=lambda x: x.priority):
            if sq.target_space not in seen:
                seen.add(sq.target_space)
                spaces.append(sq.target_space)
        return spaces

    @property
    def is_single_space(self) -> bool:
        """Check if plan targets only one space.

        Returns:
            True if all sub-queries target the same space
        """
        return len(set(sq.target_space for sq in self.sub_queries)) == 1

    def get_queries_for_space(self, space_name: str) -> list[SubQuery]:
        """Get all sub-queries targeting a specific space.

        Args:
            space_name: Name of the space to filter by

        Returns:
            List of SubQueries targeting the specified space
        """
        return [sq for sq in self.sub_queries if sq.target_space == space_name]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all Plan fields
        """
        return {
            "original_question": self.original_question,
            "sub_queries": [sq.to_dict() for sq in self.sub_queries],
            "synthesis_instructions": self.synthesis_instructions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        """Create Plan from dictionary.

        Args:
            data: Dictionary with Plan fields

        Returns:
            Plan instance
        """
        return cls(
            original_question=data["original_question"],
            sub_queries=[SubQuery.from_dict(sq) for sq in data.get("sub_queries", [])],
            synthesis_instructions=data.get("synthesis_instructions", ""),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            JSON representation of the Plan
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> Plan:
        """Create Plan from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            Plan instance
        """
        return cls.from_dict(json.loads(json_str))


class PlannerAgent:
    """Agent that decomposes complex questions into space-specific sub-queries.

    Uses an LLM to analyze user questions and route them to appropriate
    Genie Spaces based on their domains. Supports mock mode for demos.

    Example:
        >>> config = Config(mock_mode=True)
        >>> space_configs = [
        ...     GenieSpaceConfig(space_id="abc123", name="Sales", domain="sales, revenue"),
        ...     GenieSpaceConfig(space_id="def456", name="Customers", domain="customers"),
        ... ]
        >>> planner = PlannerAgent(config, space_configs)
        >>> plan = planner.decompose("Compare revenue with customer growth")
        >>> print(plan.target_spaces)
        ['Sales', 'Customers']
    """

    def __init__(
        self,
        config: Config,
        space_configs: list[GenieSpaceConfig],
        temperature: float = 0.1,
    ):
        """Initialize the Planner Agent.

        Args:
            config: Configuration instance
            space_configs: List of available Genie Space configurations
            temperature: LLM temperature for decomposition (lower = more deterministic)
        """
        self.config = config
        self.space_configs = space_configs
        self.temperature = temperature
        self._llm = None
        self._space_names = [c.name for c in space_configs]

    @property
    def llm(self):
        """Lazy-load ChatDatabricks LLM."""
        if self._llm is None and not self.config.mock_mode:
            from databricks_langchain import ChatDatabricks

            self._llm = ChatDatabricks(
                endpoint=self.config.model_endpoint,
                temperature=self.temperature,
            )
        return self._llm

    def decompose(self, question: str) -> Plan:
        """Decompose a question into space-specific sub-queries.

        Args:
            question: Natural language question to decompose

        Returns:
            Plan with sub-queries targeting appropriate spaces
        """
        if not question or not question.strip():
            return Plan(
                original_question=question,
                sub_queries=[],
                synthesis_instructions="",
                metadata={"error": "Empty question provided"},
            )

        if self.config.mock_mode:
            return self._mock_decompose(question)

        return self._llm_decompose(question)

    def execute_plan(self, plan: Plan, orchestrator: MultiGenieOrchestrator) -> MultiGenieResult:
        """Execute a plan using the MultiGenieOrchestrator.

        Sends each Genie Space its domain-specific sub-query from the plan
        rather than the original broad question.

        Args:
            plan: The decomposed query plan
            orchestrator: MultiGenieOrchestrator instance to execute queries

        Returns:
            MultiGenieResult with results from all targeted spaces
        """
        return orchestrator.query_from_plan(plan)

    def _build_system_prompt(self) -> str:
        """Build system prompt with available space context.

        Returns:
            System prompt string for the LLM
        """
        space_descriptions = []
        for config in self.space_configs:
            desc = f"- **{config.name}**: {config.domain or 'General data queries'}"
            space_descriptions.append(desc)

        spaces_text = "\n".join(space_descriptions)

        return f"""You are a query planner that decomposes complex business questions into space-specific sub-queries.

Available Genie Spaces:
{spaces_text}

Your task: Analyze the user's question and create a plan with sub-queries for relevant spaces.

Output ONLY valid JSON (no markdown, no explanation) with this structure:
{{
  "sub_queries": [
    {{
      "id": "sq1",
      "target_space": "EXACT space name from list above",
      "query": "specific question for this space",
      "priority": 1,
      "depends_on": []
    }}
  ],
  "synthesis_instructions": "How to combine results"
}}

Rules:
- target_space MUST be an exact name from the Available Genie Spaces list
- Use concise, specific queries for each space
- Set priority 1 for independent queries, higher numbers for dependent ones
- Use depends_on with SubQuery IDs when a query needs results from another"""

    def _build_few_shot_examples(self) -> str:
        """Build few-shot examples using actual space names.

        Returns:
            Examples string for the LLM prompt
        """
        if not self._space_names:
            return ""

        first_space = self._space_names[0]
        examples = []

        # Single-space example
        examples.append(
            f"""Example 1 - Single space query:
User: "What is the total revenue?"
{{"sub_queries": [{{"id": "sq1", "target_space": "{first_space}", "query": "What is the total revenue?", "priority": 1, "depends_on": []}}], "synthesis_instructions": "Report the revenue directly"}}"""
        )

        # Multi-space example (if multiple spaces)
        if len(self._space_names) >= 2:
            second_space = self._space_names[1]
            examples.append(
                f"""Example 2 - Multi-space query:
User: "Compare sales performance across regions with customer segments"
{{"sub_queries": [{{"id": "sq1", "target_space": "{first_space}", "query": "What is sales performance by region?", "priority": 1, "depends_on": []}}, {{"id": "sq2", "target_space": "{second_space}", "query": "What is customer distribution by segment?", "priority": 1, "depends_on": []}}], "synthesis_instructions": "Cross-reference regional sales with customer segment data"}}"""
            )

        return "\n\n".join(examples)

    def _llm_decompose(self, question: str) -> Plan:
        """Use LLM to decompose the question.

        Args:
            question: The question to decompose

        Returns:
            Plan with LLM-generated sub-queries
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            system_prompt = self._build_system_prompt()
            examples = self._build_few_shot_examples()

            user_content = f'{examples}\n\nNow decompose this question:\nUser: "{question}"'

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content),
            ]

            response = self.llm.invoke(messages)
            content = response.content

            plan_data = self._parse_llm_response(content)
            validated_subqueries = self._validate_subqueries(plan_data.get("sub_queries", []))

            return Plan(
                original_question=question,
                sub_queries=validated_subqueries,
                synthesis_instructions=plan_data.get("synthesis_instructions", ""),
                metadata={"reasoning": plan_data.get("reasoning", "")},
            )

        except Exception as e:
            # Fallback: route to all spaces with original question
            logger.warning(f"LLM decomposition failed, using fallback: {e}")
            return self._create_fallback_plan(question, str(e))

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """Extract and parse JSON from LLM response.

        Handles common LLM output patterns like markdown code blocks
        and preamble text before JSON.

        Args:
            content: Raw LLM response content

        Returns:
            Parsed JSON as dictionary

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        content = content.strip()

        # Remove markdown code blocks
        if "```" in content:
            # Find content between code blocks
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if match:
                content = match.group(1)

        # Find JSON object (first { to last })
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            content = content[start:end]

        return json.loads(content)

    def _validate_subqueries(self, subqueries_data: list[dict]) -> list[SubQuery]:
        """Validate and filter sub-queries to only include valid space names.

        Args:
            subqueries_data: List of sub-query dictionaries from LLM

        Returns:
            List of validated SubQuery objects
        """
        valid_subqueries = []
        valid_space_names = set(self._space_names)

        for sq_data in subqueries_data:
            target = sq_data.get("target_space", "")
            if target in valid_space_names:
                valid_subqueries.append(SubQuery.from_dict(sq_data))

        return valid_subqueries

    def _create_fallback_plan(self, question: str, error: str = "") -> Plan:
        """Create fallback plan routing to all spaces.

        Used when LLM decomposition fails or in error scenarios.

        Args:
            question: The original question
            error: Optional error message to include in metadata

        Returns:
            Plan that routes the original question to all spaces
        """
        sub_queries = []
        for i, space_name in enumerate(self._space_names):
            sub_queries.append(
                SubQuery(
                    id=f"fallback_{i + 1}",
                    target_space=space_name,
                    query=question,
                    priority=1,
                )
            )

        return Plan(
            original_question=question,
            sub_queries=sub_queries,
            synthesis_instructions="Combine results from all spaces",
            metadata={"fallback": True, "error": error} if error else {"fallback": True},
        )

    def _mock_decompose(self, question: str) -> Plan:
        """Simple mock: route original question to all configured spaces.

        Args:
            question: The question to decompose

        Returns:
            Plan routing to all spaces (for demo/testing)
        """
        return self._create_fallback_plan(question)
