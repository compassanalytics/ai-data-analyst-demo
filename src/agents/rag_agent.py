"""RAG Agent - Document retrieval and question answering.

This module provides a RAG (Retrieval Augmented Generation) agent for
answering questions based on document/policy content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.config import Config
from src.utils.errors import AgentError, classify_error


@dataclass
class Document:
    """A retrieved document chunk.

    Attributes:
        content: The document text content
        source: Source identifier (file name, URL, etc.)
        score: Relevance score (0-1)
        metadata: Additional document metadata
    """

    content: str
    source: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResult:
    """Result from a RAG query.

    Attributes:
        success: Whether the query completed successfully
        answer: The generated answer
        documents: Retrieved documents used to generate the answer
        error: Error message if query failed
        error_details: Structured error information for classification
    """

    success: bool
    answer: str = ""
    documents: list[Document] = field(default_factory=list)
    error: str | None = None
    error_details: AgentError | None = None

    @property
    def is_retryable(self) -> bool:
        """Check if the error is retryable.

        Returns:
            True if the error is retryable, False otherwise
        """
        if self.error_details is not None:
            return self.error_details.retryable
        return False

    def get_user_message(self) -> str:
        """Get a user-friendly error message.

        Returns:
            User-friendly message if error_details available, else raw error
        """
        if self.error_details is not None:
            return self.error_details.to_user_message()
        return self.error or "Unknown error"

    def format_sources(self) -> str:
        """Format the source documents as a citation list.

        Returns:
            Formatted string of sources
        """
        if not self.documents:
            return "_No sources_"

        lines = ["**Sources:**"]
        for i, doc in enumerate(self.documents, 1):
            score_str = f" (relevance: {doc.score:.2f})" if doc.score else ""
            lines.append(f"{i}. {doc.source}{score_str}")

        return "\n".join(lines)


class RAGAgent:
    """Agent for document retrieval and question answering.

    Provides RAG capabilities using Databricks Vector Search (when available)
    or mock responses for demonstration.

    Example:
        >>> config = Config(mock_mode=True)
        >>> agent = RAGAgent(config)
        >>> result = agent.query("What is our refund policy?")
        >>> print(result.answer)
    """

    def __init__(self, config: Config):
        """Initialize the RAG Agent.

        Args:
            config: Configuration instance with Vector Search settings
        """
        self.config = config
        self._client = None
        self._vs_client = None
        self._llm = None
        self._index = None

    @property
    def client(self):
        """Lazy-load the Databricks SDK client."""
        if self._client is None and not self.config.mock_mode:
            from databricks.sdk import WorkspaceClient

            self._client = WorkspaceClient(
                host=self.config.databricks_host or None,
                token=self.config.databricks_token,
            )
        return self._client

    @property
    def vs_client(self):
        """Lazy-load the VectorSearchClient for VS operations."""
        if self._vs_client is None and not self.config.mock_mode:
            from databricks.vector_search.client import VectorSearchClient

            self._vs_client = VectorSearchClient(
                workspace_url=self.config.databricks_host,
                personal_access_token=self.config.databricks_token,
            )
        return self._vs_client

    @property
    def llm(self):
        """Lazy-load ChatDatabricks for answer generation."""
        if self._llm is None and not self.config.mock_mode:
            from databricks_langchain import ChatDatabricks

            self._llm = ChatDatabricks(
                endpoint=self.config.model_endpoint,
                temperature=0.1,
            )
        return self._llm

    def query(
        self,
        question: str,
        num_results: int = 3,
    ) -> RAGResult:
        """Query documents with a natural language question.

        Args:
            question: Natural language question
            num_results: Number of documents to retrieve

        Returns:
            RAGResult with answer and source documents
        """
        if self.config.mock_mode:
            return self._mock_query(question, num_results)

        return self._real_query(question, num_results)

    def _real_query(self, question: str, num_results: int) -> RAGResult:
        """Execute a real query against Vector Search.

        Args:
            question: Natural language question
            num_results: Number of documents to retrieve

        Returns:
            RAGResult with actual data from Vector Search
        """
        try:
            if not self.config.vector_search_endpoint or not self.config.vector_search_index:
                return RAGResult(
                    success=False,
                    error="Vector Search endpoint or index not configured. "
                    "Set VECTOR_SEARCH_ENDPOINT and VECTOR_SEARCH_INDEX environment variables.",
                )

            # Get the Vector Search index
            index = self.vs_client.get_index(
                endpoint_name=self.config.vector_search_endpoint,
                index_name=self.config.vector_search_index,
            )

            # Query the index using similarity search
            results = index.similarity_search(
                query_text=question,
                columns=["id", "content", "source", "metadata"],
                num_results=num_results,
            )

            # Parse results into Document objects
            # VectorSearchClient returns: {"result": {"data_array": [[col1, col2, ...], ...], "row_count": N}}
            documents = []
            data_array = results.get("result", {}).get("data_array", [])

            for row in data_array:
                # Row format: [id, content, source, metadata, score]
                # Score is typically the last column
                doc = Document(
                    content=row[1] if len(row) > 1 else "",
                    source=row[2] if len(row) > 2 else "Unknown",
                    score=float(row[-1]) if len(row) > 0 and isinstance(row[-1], (int, float)) else 0.0,
                    metadata=self._parse_metadata(row[3] if len(row) > 3 else None),
                )
                documents.append(doc)

            # Generate answer using LLM with retrieved context
            answer = self._generate_answer(question, documents)

            return RAGResult(
                success=True,
                answer=answer,
                documents=documents,
            )

        except Exception as e:
            # Classify the error while the exception is intact
            classified_error = classify_error(
                e,
                context={"question": question, "num_results": num_results},
            )
            return RAGResult(
                success=False,
                error=str(e),
                error_details=classified_error,
            )

    def _parse_metadata(self, metadata_value: Any) -> dict[str, Any]:
        """Parse metadata from Vector Search result.

        Args:
            metadata_value: Raw metadata value (could be dict, JSON string, or None)

        Returns:
            Parsed metadata dictionary
        """
        if metadata_value is None:
            return {}
        if isinstance(metadata_value, dict):
            return metadata_value
        if isinstance(metadata_value, str):
            try:
                return json.loads(metadata_value)
            except (json.JSONDecodeError, ValueError):
                return {"raw": metadata_value}
        return {}

    def _generate_answer(self, question: str, documents: list[Document]) -> str:
        """Generate an answer using ChatDatabricks with retrieved context.

        Args:
            question: The user's question
            documents: Retrieved documents to use as context

        Returns:
            Generated answer grounded in the retrieved documents
        """
        if not documents:
            return "No relevant documents found to answer your question."

        # Build context from retrieved documents
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source_info = f"[Document {i}: {doc.source}]"
            context_parts.append(f"{source_info}\n{doc.content}")

        context = "\n\n---\n\n".join(context_parts)

        # RAG prompt template
        prompt = f"""You are a helpful assistant answering questions based on company documents.

CONTEXT (Retrieved Documents):
{context}

USER QUESTION: {question}

INSTRUCTIONS:
- Answer the question based ONLY on the provided context above
- If the context doesn't contain enough information to fully answer, acknowledge what you can answer and what's missing
- Be concise but thorough
- When referencing specific information, mention which document it came from

ANSWER:"""

        try:
            from langchain_core.messages import HumanMessage

            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            # Fallback to simple concatenation if LLM fails
            return f"Based on the retrieved documents:\n\n{documents[0].content}\n\n(Note: LLM answer generation failed: {e})"

    def _mock_query(self, question: str, num_results: int) -> RAGResult:
        """Return mock data for demonstration purposes.

        Args:
            question: The question (used to determine mock response)
            num_results: Number of mock documents to return

        Returns:
            RAGResult with mock data
        """
        question_lower = question.lower()

        # Mock responses based on question patterns
        if "refund" in question_lower or "return" in question_lower:
            return RAGResult(
                success=True,
                answer="""Our refund policy allows customers to request a full refund within 30 days of purchase for any reason.

Key points:
- **30-day window**: Full refunds available within 30 days
- **Partial refunds**: 50% refund available between 30-60 days
- **Process**: Submit refund request through customer portal or contact support
- **Processing time**: Refunds are processed within 5-7 business days

For enterprise customers, custom refund terms may apply based on your contract.""",
                documents=[
                    Document(
                        content="Refund Policy v2.3: Customers may request a full refund within 30 days of purchase...",
                        source="policies/refund-policy.md",
                        score=0.95,
                    ),
                    Document(
                        content="Enterprise Terms: Custom refund terms may be negotiated as part of enterprise agreements...",
                        source="policies/enterprise-terms.md",
                        score=0.82,
                    ),
                ][:num_results],
            )

        elif "security" in question_lower or "compliance" in question_lower:
            return RAGResult(
                success=True,
                answer="""Our platform maintains SOC 2 Type II compliance and implements industry-standard security practices:

- **Data encryption**: AES-256 encryption at rest, TLS 1.3 in transit
- **Access control**: Role-based access control (RBAC) with SSO integration
- **Audit logging**: Comprehensive audit logs retained for 7 years
- **Certifications**: SOC 2 Type II, ISO 27001, GDPR compliant

Security assessments and penetration testing are conducted quarterly.""",
                documents=[
                    Document(
                        content="Security Overview: Our platform implements defense-in-depth security architecture...",
                        source="docs/security-overview.md",
                        score=0.93,
                    ),
                    Document(
                        content="Compliance Certifications: SOC 2 Type II audit completed annually...",
                        source="docs/compliance.md",
                        score=0.88,
                    ),
                    Document(
                        content="Data Protection: All customer data is encrypted using AES-256...",
                        source="docs/data-protection.md",
                        score=0.85,
                    ),
                ][:num_results],
            )

        elif "pricing" in question_lower or "cost" in question_lower:
            return RAGResult(
                success=True,
                answer="""Our pricing tiers are designed to scale with your needs:

| Plan | Price | Features |
|------|-------|----------|
| Starter | $29/mo | 5 users, basic features |
| Professional | $99/mo | 25 users, advanced analytics |
| Enterprise | Custom | Unlimited users, dedicated support |

Annual billing provides a 20% discount. Contact sales for enterprise pricing.""",
                documents=[
                    Document(
                        content="Pricing Guide 2024: Our tiered pricing model offers flexibility...",
                        source="sales/pricing-guide.md",
                        score=0.91,
                    ),
                ][:num_results],
            )

        elif "onboard" in question_lower or "start" in question_lower or "setup" in question_lower:
            return RAGResult(
                success=True,
                answer="""Getting started with our platform is straightforward:

1. **Account Setup**: Create your organization account via the signup page
2. **Team Invitation**: Invite team members via email or SSO directory sync
3. **Integration**: Connect your data sources using our pre-built connectors
4. **Training**: Complete the interactive onboarding tutorial (30 mins)
5. **Go Live**: Start using the platform with your team

Our customer success team is available to assist with enterprise onboarding.""",
                documents=[
                    Document(
                        content="Onboarding Guide: Welcome to the platform! This guide will walk you through...",
                        source="docs/onboarding-guide.md",
                        score=0.94,
                    ),
                    Document(
                        content="Quick Start Tutorial: Get up and running in under 30 minutes...",
                        source="docs/quick-start.md",
                        score=0.87,
                    ),
                ][:num_results],
            )

        else:
            # Generic mock response
            return RAGResult(
                success=True,
                answer=f"""I found some relevant information regarding your question about "{question}".

Based on our documentation, this topic is covered in our knowledge base. For more specific information, please refer to the source documents or contact our support team.

Key resources:
- Product documentation portal
- Support knowledge base
- Community forums""",
                documents=[
                    Document(
                        content=f"Documentation related to: {question}",
                        source="docs/general-faq.md",
                        score=0.75,
                    ),
                ][:num_results],
            )

    def search_documents(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[Document]:
        """Search for documents without generating an answer.

        Args:
            query: Search query
            num_results: Maximum number of documents to return

        Returns:
            List of relevant documents
        """
        result = self.query(query, num_results)
        return result.documents if result.success else []
