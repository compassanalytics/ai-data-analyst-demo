"""Agent modules for the AI Data Analyst demo."""

from src.agents.genie_agent import GenieDataAgent
from src.agents.multi_genie_orchestrator import (
    GenieSpaceConfig,
    MultiGenieOrchestrator,
    MultiGenieResult,
    ResultMetadata,
)
from src.agents.planner_agent import Plan, PlannerAgent, SubQuery
from src.agents.rag_agent import RAGAgent
from src.agents.report_writer import ReportConfig, ReportWriter
from src.agents.supervisor import AgentState, create_supervisor_agent
from src.agents.synthesizer_agent import (
    Anomaly,
    Correlation,
    Insight,
    SynthesisResult,
    SynthesizerAgent,
)

__all__ = [
    "GenieDataAgent",
    "RAGAgent",
    "create_supervisor_agent",
    "AgentState",
    "MultiGenieOrchestrator",
    "GenieSpaceConfig",
    "MultiGenieResult",
    "ResultMetadata",
    "PlannerAgent",
    "Plan",
    "SubQuery",
    "SynthesizerAgent",
    "SynthesisResult",
    "Insight",
    "Correlation",
    "Anomaly",
    "ReportWriter",
    "ReportConfig",
]
