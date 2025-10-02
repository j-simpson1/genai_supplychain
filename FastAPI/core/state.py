"""
State definitions for the document generation workflow.

This module defines the state schema for the multi-agent document generation system,
including structured critique models and the main agent state.
"""

from typing import TypedDict, List, Dict, Annotated
from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class ReportCritique(BaseModel):
    """Structured critique of the report with quality metrics."""
    quality_score: int = Field(ge=1, le=10, description="Overall quality score (1-10)")
    completeness: int = Field(ge=1, le=10, description="Completeness score (1-10)")
    issues: List[str] = Field(default_factory=list, description="Specific issues to address")
    recommendations: str = Field(description="Detailed recommendations for improvement")


class AgentState(TypedDict):
    """Shared state for the document generation workflow."""

    # Task and planning
    task: str
    plan: str

    # Draft and revision control
    draft: str
    draft_number: int
    max_revisions: int
    critique: str
    critique_score: float  # Average quality score (1-10)

    # Research content
    web_content: List[str]
    deep_research_content: List[str]
    deep_research_summary: str  # 200-word summary with citations

    # Database content
    db_content: Annotated[List[AnyMessage], add_messages]
    db_summary: str

    # Simulation results
    raw_simulation: Annotated[List[BaseMessage], add_messages]
    clean_simulation: str

    # Chart generation state
    chart_plan: List[Dict[str, str]]
    chart_metadata: List[Dict[str, str]]
    current_chart_index: int
    chart_code: str
    chart_generation_success: bool
    chart_generation_error: str
    chart_retry_count: int
    max_chart_retries: int

    # Data file paths
    articles_path: str
    parts_path: str
    tariff_path: str

    # Agent-to-agent messages
    messages: Annotated[List[AnyMessage], add_messages]