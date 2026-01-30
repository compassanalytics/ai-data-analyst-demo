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
                disable_notice=True,
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
        if any(kw in question_lower for kw in ["warranty", "coverage", "bumper", "powertrain"]):
            return RAGResult(
                success=True,
                answer="""**Vehicle Warranty Coverage**

Velocity Motors provides comprehensive warranty protection on all new and certified pre-owned vehicles:

- **Bumper-to-Bumper**: 3 years / 36,000 miles covering all components except wear items
- **Powertrain Warranty**: 5 years / 60,000 miles covering engine, transmission, and drivetrain
- **CPO Extended Coverage**: Certified Pre-Owned vehicles receive an additional 1 year / 12,000 miles beyond the original warranty
- **Warranty Transfer**: All remaining warranty coverage transfers automatically to subsequent owners upon resale

Contact the service department for warranty claims or to verify coverage status on a specific vehicle.""",
                documents=[
                    Document(
                        content="Vehicle Warranty Policy: All new Velocity Motors vehicles include 3-year/36,000-mile bumper-to-bumper and 5-year/60,000-mile powertrain coverage...",
                        source="policies/vehicle-warranty.md",
                        score=0.95,
                    ),
                    Document(
                        content="CPO Program: Certified Pre-Owned vehicles undergo a 150-point inspection and receive an additional 1-year/12,000-mile extended warranty...",
                        source="policies/cpo-program.md",
                        score=0.88,
                    ),
                ][:num_results],
            )

        elif any(kw in question_lower for kw in ["service", "maintenance", "inspection", "fleet service"]):
            return RAGResult(
                success=True,
                answer="""**Service & Maintenance Policy**

Velocity Motors follows a structured maintenance schedule for all vehicles:

- **First Service**: Required at 5,000 miles — oil change, tire rotation, and multi-point inspection
- **Major Service Intervals**: Every 30,000 miles — comprehensive inspection including brakes, fluids, belts, and suspension
- **Fleet Vehicles**: Quarterly inspections required regardless of mileage, per fleet service agreement terms
- **Service Records**: All work is logged in the vehicle's digital service history accessible via the customer portal

Fleet customers should contact their dedicated service advisor for scheduling priority appointments.""",
                documents=[
                    Document(
                        content="Service & Maintenance Schedule: First service at 5,000 miles includes oil change, tire rotation, and multi-point inspection. Major services every 30,000 miles...",
                        source="policies/service-maintenance.md",
                        score=0.93,
                    ),
                    Document(
                        content="Fleet Service Agreement: Fleet vehicles require quarterly inspections regardless of mileage. Dedicated service bays and priority scheduling available...",
                        source="policies/fleet-service-agreement.md",
                        score=0.86,
                    ),
                ][:num_results],
            )

        elif any(kw in question_lower for kw in ["return", "exchange", "lemon"]):
            return RAGResult(
                success=True,
                answer="""**Return & Exchange Policy**

Velocity Motors offers a customer-friendly exchange policy with the following terms:

- **7-Day Exchange Window**: Vehicles may be exchanged within 7 days or 500 miles (whichever comes first) for a vehicle of equal or greater value
- **No Returns Post-Title**: Once the title has been transferred, the sale is final and returns are not accepted
- **Lemon Law Compliance**: All transactions comply with applicable state lemon law protections — vehicles with qualifying defects are eligible for manufacturer buyback or replacement
- **Condition Requirement**: Exchange vehicles must be returned in the same condition, free of damage beyond normal use

Speak with a sales manager for exchange eligibility questions.""",
                documents=[
                    Document(
                        content="Return & Exchange Policy: Customers may exchange a vehicle within 7 days or 500 miles. No returns accepted after title transfer...",
                        source="policies/return-exchange-policy.md",
                        score=0.94,
                    ),
                    Document(
                        content="Lemon Law Compliance: Velocity Motors complies with all applicable state lemon law statutes. Vehicles with qualifying defects are eligible for buyback...",
                        source="policies/lemon-law-compliance.md",
                        score=0.82,
                    ),
                ][:num_results],
            )

        elif any(kw in question_lower for kw in ["financing", "rate", "apr", "loan", "lease"]):
            return RAGResult(
                success=True,
                answer="""**Financing & Lease Terms**

Velocity Motors partners with multiple lenders to offer competitive financing options:

- **Standard APR**: Starting from 3.9% APR for up to 72 months on approved credit
- **Fleet Discount**: Fleet purchases qualify for an additional 0.5% rate reduction
- **Trade-In Credit**: Trade-in value is applied at the time of deal, reducing the financed amount
- **CPO Special Rates**: Certified Pre-Owned vehicles are eligible for promotional financing rates as low as 4.9% APR
- **Lease Options**: 24, 36, and 48-month lease terms available with competitive money factors

Visit the finance office or apply online to get pre-approved.""",
                documents=[
                    Document(
                        content="Financing Terms: Standard rates from 3.9% APR for up to 72 months. Fleet customers receive a 0.5% rate discount. Trade-in applied at deal time...",
                        source="policies/financing-terms.md",
                        score=0.92,
                    ),
                    Document(
                        content="Fleet Financing: Fleet purchases of 5+ vehicles qualify for volume financing discounts and dedicated account management...",
                        source="policies/fleet-financing.md",
                        score=0.85,
                    ),
                ][:num_results],
            )

        elif any(kw in question_lower for kw in ["commission", "bonus", "compensation", "pay"]):
            return RAGResult(
                success=True,
                answer="""**Employee Compensation Structure**

Velocity Motors compensation plans are designed to reward performance across departments:

- **Sales Commission**: 2% of gross vehicle margin per unit sold, paid bi-weekly
- **Quarterly Bonus**: 5% of total margin generated above quarterly quota targets
- **Service Technicians**: Hourly base rate plus certification bonuses for ASE and manufacturer credentials
- **F&I Managers**: Per-deal flat fee plus penetration bonuses on warranty and protection products
- **Management**: Base salary plus department profitability bonuses paid quarterly

Compensation details are outlined in your offer letter and the employee handbook.""",
                documents=[
                    Document(
                        content="Sales Compensation Plan: Sales associates earn 2% of gross vehicle margin per unit. Quarterly bonus of 5% on margin exceeding quota...",
                        source="policies/sales-compensation.md",
                        score=0.91,
                    ),
                    Document(
                        content="Service Technician Pay: Hourly base rate determined by experience level. Additional certification bonuses for ASE and OEM credentials...",
                        source="policies/service-tech-pay.md",
                        score=0.84,
                    ),
                ][:num_results],
            )

        elif any(kw in question_lower for kw in ["recall", "safety", "compliance", "nhtsa"]):
            return RAGResult(
                success=True,
                answer="""**Safety & Compliance Procedures**

Velocity Motors maintains rigorous safety standards across all operations:

- **NHTSA Inspection**: All vehicles undergo NHTSA-aligned safety inspection before listing for sale
- **Open Recall Resolution**: Any open manufacturer recalls must be resolved prior to customer delivery — no exceptions
- **Annual Compliance Audit**: Dealership operations are audited annually for compliance with federal, state, and manufacturer safety standards
- **Incident Reporting**: All safety incidents are documented and reported per OSHA and manufacturer requirements within 24 hours

Contact the compliance officer for questions about specific recall campaigns or safety procedures.""",
                documents=[
                    Document(
                        content="Safety & Compliance Policy: All inventory vehicles must pass NHTSA-aligned inspection. Open recalls resolved before delivery to customers...",
                        source="policies/safety-compliance.md",
                        score=0.93,
                    ),
                    Document(
                        content="Recall Procedures: Open recalls are identified during intake inspection. Parts are ordered immediately and repairs completed before vehicle is listed...",
                        source="policies/recall-procedures.md",
                        score=0.87,
                    ),
                ][:num_results],
            )

        else:
            # Generic mock response
            return RAGResult(
                success=True,
                answer=f"""I found some relevant information regarding your question about "{question}".

Based on Velocity Motors documentation, this topic is covered in our internal knowledge base. For more specific information, please refer to the source documents below or contact the appropriate department.

**Key resources:**
- Velocity Motors policy documentation
- Employee handbook and procedures
- Department-specific operating guidelines""",
                documents=[
                    Document(
                        content=f"Velocity Motors FAQ: General documentation related to: {question}",
                        source="docs/velocity-motors-faq.md",
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
