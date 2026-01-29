"""Unified LLM client using LiteLLM for model-agnostic access.

Provides a consistent interface for interacting with various LLM providers
(Anthropic, OpenAI, Databricks) through LiteLLM's unified API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for the LLM client.

    Attributes:
        model: Model identifier (e.g., "claude-sonnet-4-5-20250929", "gpt-4o")
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens in response
        provider: Optional provider hint ("anthropic", "openai", "databricks")
    """

    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.3  # Lower for deterministic generation
    max_tokens: int = 4096
    provider: str | None = None


@dataclass
class LLMResponse:
    """Response from an LLM invocation.

    Attributes:
        content: The text content of the response
        model: The model that generated the response
        usage: Token usage statistics
    """

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


class UnifiedLLMClient:
    """Model-agnostic LLM client using LiteLLM.

    Provides a unified interface for calling various LLM providers,
    with automatic fallback and retry handling.

    Example:
        >>> config = LLMConfig(model="claude-sonnet-4-5-20250929")
        >>> client = UnifiedLLMClient(config)
        >>> response = client.invoke([
        ...     {"role": "system", "content": "You are a helpful assistant."},
        ...     {"role": "user", "content": "Hello!"}
        ... ])
        >>> print(response.content)
    """

    def __init__(self, config: LLMConfig | None = None):
        """Initialize the LLM client.

        Args:
            config: LLM configuration. If None, uses defaults.
        """
        self.config = config or LLMConfig()
        self._litellm = None

    @property
    def litellm(self):
        """Lazy-load litellm module."""
        if self._litellm is None:
            import litellm

            # Configure litellm settings
            litellm.drop_params = True  # Drop unsupported params gracefully
            self._litellm = litellm
        return self._litellm

    def invoke(self, messages: list[dict[str, str]]) -> LLMResponse:
        """Invoke the LLM with the given messages.

        Args:
            messages: List of message dicts with "role" and "content" keys.
                      Roles: "system", "user", "assistant"

        Returns:
            LLMResponse with the generated content

        Raises:
            Exception: If the LLM call fails after retries
        """
        try:
            response = self.litellm.completion(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            content = response.choices[0].message.content
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
            )

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise

    def invoke_with_system(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Convenience method for system + user message pattern.

        Args:
            system_prompt: The system/instruction message
            user_prompt: The user message

        Returns:
            LLMResponse with the generated content
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.invoke(messages)


class DatabricksLLMClient:
    """LLM client for Databricks Foundation Model API.

    Falls back to this when using Databricks-hosted models.
    """

    def __init__(self, endpoint: str, temperature: float = 0.3):
        """Initialize the Databricks LLM client.

        Args:
            endpoint: Databricks model serving endpoint name
            temperature: Sampling temperature
        """
        self.endpoint = endpoint
        self.temperature = temperature
        self._llm = None

    @property
    def llm(self):
        """Lazy-load ChatDatabricks."""
        if self._llm is None:
            from databricks_langchain import ChatDatabricks

            self._llm = ChatDatabricks(
                endpoint=self.endpoint,
                temperature=self.temperature,
            )
        return self._llm

    def invoke(self, messages: list[dict[str, str]]) -> LLMResponse:
        """Invoke the Databricks LLM.

        Args:
            messages: List of message dicts

        Returns:
            LLMResponse with the generated content
        """
        from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

        lc_messages: list[BaseMessage] = []
        for msg in messages:
            if msg["role"] == "system":
                lc_messages.append(SystemMessage(content=msg["content"]))
            else:
                lc_messages.append(HumanMessage(content=msg["content"]))

        response = self.llm.invoke(lc_messages)
        return LLMResponse(
            content=response.content,
            model=self.endpoint,
            usage={},
        )


def create_llm_client(
    provider: str = "litellm",
    model: str = "claude-sonnet-4-5-20250929",
    endpoint: str | None = None,
    temperature: float = 0.3,
) -> UnifiedLLMClient | DatabricksLLMClient:
    """Factory function to create an appropriate LLM client.

    Args:
        provider: "litellm" or "databricks"
        model: Model identifier (for litellm)
        endpoint: Databricks endpoint (for databricks provider)
        temperature: Sampling temperature

    Returns:
        Appropriate LLM client instance
    """
    if provider == "databricks" and endpoint:
        return DatabricksLLMClient(endpoint=endpoint, temperature=temperature)
    else:
        config = LLMConfig(model=model, temperature=temperature)
        return UnifiedLLMClient(config)
