"""
Document Generation Agent using LangGraph

This module implements a multi-agent workflow for generating comprehensive supply chain reports.
The workflow includes research, data analysis, chart generation, simulation, and document creation.

References:
- LangGraph workflow design influenced by:
  "AI Agents in LangGraph" - DeepLearning.AI Course
  https://learn.deeplearning.ai/courses/ai-agents-in-langgraph/lesson/qyrpc/introduction
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import os
import re
import tempfile
from datetime import datetime
from typing import Dict, Any, List

import matplotlib
import pandas as pd
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, END
from langsmith import Client

from FastAPI.core.CoT_prompting import chain_of_thought_writing_examples
from FastAPI.core.code_editor_agent import code_editor_agent
from FastAPI.core.data_agent import data_agent
from FastAPI.core.prompts import (
    plan_prompt,
    reflection_prompt,
    writers_prompt,
    revision_writers_prompt,
    chart_planning_prompt
)
from FastAPI.core.research_agent import research_agent
from FastAPI.core.research_critique import research_critique_agent
from FastAPI.core.simulation_agent import simulation_agent
from FastAPI.core.deep_research_agent import deep_research_agent
from FastAPI.core.state import AgentState, ReportCritique
from FastAPI.core.utils import serialize_state
from FastAPI.document_builders.pdf_creator import save_to_pdf
from FastAPI.document_builders.word_creator import save_to_word


matplotlib.use("Agg")

# Configuration constants
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CHARTS_DIR = os.path.join(PROJECT_ROOT, "output", "charts")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "output", "reports")
MAX_REVISIONS = 2
MAX_CHART_RETRIES = 2
RECURSION_LIMIT = 500

# Ensure directories exist
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Initialize clients and model
client = Client()
from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="o4-mini")

DATABASE_PLAN_INSTRUCTIONS = """ You are a supply chain data analyst with access to several \
database tools. Your role is to extract relevant automotive part insights that will inform a \
detailed written report. Do not hallucinate numbers. Only use tool outputs. Pick tools one at a time, \
picking the most appropriate tool.
"""

# Prompt templates
RESEARCH_PLAN_PROMPT = """You are a researcher charged with providing information that can \
be used when writing the following essay. Generate a list of search queries that will gather \
any relevant information. Only generate 4 queries max."""
RESEARCH_CRITIQUE_PROMPT = """You are a researcher charged with providing information that can \
be used when making any requested revisions (as outlined below). \
Generate a list of search queries that will gather any relevant information. Only generate 3 queries max."""

# take in the state and create list of messages, one of them is going to be the planning prompt
# then create a human message which is what we want system to do
def plan_node(state: AgentState) -> Dict[str, str]:
    """Generate a plan based on the task."""
    messages = [
        SystemMessage(content=plan_prompt),
        HumanMessage(content=state['task'])
    ]
    response = model.invoke(messages)
    return {"plan": response.content}

def chart_planning_node(state: AgentState) -> Dict[str, List[Dict[str, str]]]:
    """Decide what charts to generate based on DB summary and content."""
    db_summary = state.get("db_summary", "")
    db_content = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))

    formatted_chart_planning_prompt = chart_planning_prompt.format(
        db_summary=db_summary,
        db_content=db_content
    )

    response = model.invoke([SystemMessage(content=formatted_chart_planning_prompt)])
    raw = response.content.strip()

    # Clean up JSON formatting
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw).strip()

    try:
        chart_plan = json.loads(raw)
        if isinstance(chart_plan, dict):
            chart_plan = [chart_plan]
    except json.JSONDecodeError:
        chart_plan = [{"chart_id": "chart1", "chart_description": raw}]

    return {"chart_plan": chart_plan}

def writer_node(state: AgentState) -> Dict[str, Any]:
    """Generate the report draft based on collected data."""
    print("\n=== WRITER NODE STARTED ===")
    draft_num = state.get("draft_number", 0) + 1
    print(f"Draft number: {draft_num}")

    db_analyst = state.get("db_summary", "")
    db_content = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))
    web = "\n\n".join(state.get("web_content", []))
    deep_research = state.get("deep_research_summary", "")  # Use summary instead of raw content
    chart_metadata = state.get("chart_metadata", [])
    simulation_messages = state.get("clean_simulation", [])

    charts = "\n\n".join(
        [f"\n[[FIGURE:{item['id']}]]" for item in chart_metadata])

    # Check if this is a revision (has previous draft and critique)
    previous_draft = state.get("draft", "")
    critique = state.get("critique", "")

    print(f"Is revision: {bool(previous_draft and critique)}")

    if previous_draft and critique:
        # Revision mode - use revision prompt with feedback
        print("Using revision prompt...")
        formatted_writers_prompt = revision_writers_prompt.format(
            CoT_writing_examples=chain_of_thought_writing_examples,
            previous_draft=previous_draft,
            critique=critique,
            task=state['task'],
            plan=state['plan'],
            db=f"Analyst:\n{db_analyst}\n\nFull Content:\n{db_content}",
            web=web,
            deep_research=deep_research,
            charts=charts,
            simulation=simulation_messages
        )
    else:
        # Initial draft mode - use standard prompt
        print("Using initial draft prompt...")
        formatted_writers_prompt = writers_prompt.format(
            CoT_writing_examples=chain_of_thought_writing_examples,
            task=state['task'],
            plan=state['plan'],
            db=f"Analyst:\n{db_analyst}\n\nFull Content:\n{db_content}",
            web=web,
            deep_research=deep_research,
            charts=charts,
            simulation=simulation_messages
        )

    print(f"Prompt length: {len(formatted_writers_prompt)} characters")
    print("Invoking model (this may take a while with o4-mini reasoning)...")

    import time
    start_time = time.time()
    response = model.invoke([HumanMessage(content=formatted_writers_prompt)])
    elapsed = time.time() - start_time

    print(f"✓ Model response received in {elapsed:.1f}s")
    print(f"Response length: {len(response.content)} characters")

    return {
        "draft": response.content,
        "draft_number": draft_num
    }

def reflection_node(state: AgentState) -> Dict[str, Any]:
    """Generate critique of the current draft with structured quality assessment."""
    print("\n=== REFLECTION NODE STARTED ===")
    draft_num = state.get("draft_number", 0)
    print(f"Reflection for draft: {draft_num}")

    db_analyst = state.get("db_summary", "")
    db_content = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))
    web = "\n\n".join(state.get("web_content", []))
    deep_research = state.get("deep_research_summary", "")  # Use summary instead of raw content
    chart_metadata = state.get("chart_metadata", [])
    simulation_messages = state.get("clean_simulation", [])

    charts = "\n\n".join(
        [f"\n[[FIGURE:{item['id']}]]" for item in chart_metadata])

    formatted_reflection_prompt = reflection_prompt.format(
        task=state['task'],
        plan=state['plan'],
        draft=state['draft'],
        charts=charts
    )

    # Use structured output for critique with fallback
    print("Invoking critique model with structured output...")
    try:
        import time
        start_time = time.time()

        critique_model = model.with_structured_output(ReportCritique)
        critique_obj = critique_model.invoke([HumanMessage(content=formatted_reflection_prompt)])

        elapsed = time.time() - start_time
        print(f"✓ Critique received in {elapsed:.1f}s")

        # Calculate average quality score
        avg_score = (
            critique_obj.quality_score +
            critique_obj.completeness
        ) / 2.0

        print(f"Scores - Quality: {critique_obj.quality_score}/10, Completeness: {critique_obj.completeness}/10")
        print(f"Average score: {avg_score:.1f}/10")

        # Format issues as bullet points for readability
        issues_text = "\n".join([f"- {issue}" for issue in critique_obj.issues]) if critique_obj.issues else "None"

        critique_text = f"""Quality Score: {critique_obj.quality_score}/10
Completeness: {critique_obj.completeness}/10
Average Score: {avg_score:.1f}/10

Issues to Address:
{issues_text}

Recommendations:
{critique_obj.recommendations}"""

        return {
            "critique": critique_text,
            "critique_score": avg_score
        }

    except Exception as e:
        print(f"Warning: Structured critique failed ({e}). Using text-based critique.")
        # Fallback to original text-based critique
        response = model.invoke([HumanMessage(content=formatted_reflection_prompt)])
        return {
            "critique": response.content,
            "critique_score": 5.0  # Neutral score - continue revising
        }


def should_continue(state: AgentState) -> str:
    """Determine whether to continue revising or finish the report based on quality metrics."""
    draft_num = state.get("draft_number", 0)
    max_revisions = state["max_revisions"]
    critique_score = state.get("critique_score", 0.0)

    # Quality threshold for early stopping (7.5/10 average score)
    QUALITY_THRESHOLD = 7.5

    # Calculate how many revisions we've done (drafts beyond the first)
    revisions_completed = draft_num - 1

    # Determine if we should stop
    hit_max_revisions = revisions_completed >= max_revisions
    quality_satisfied = (critique_score >= QUALITY_THRESHOLD and draft_num > 1)

    if hit_max_revisions or quality_satisfied:
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Determine stop reason for logging
        if quality_satisfied:
            reason = f"quality threshold met (score: {critique_score:.1f}/10)"
        else:
            reason = f"max revisions reached (score: {critique_score:.1f}/10)"

        print(f"\n✓ Report generation complete - {reason} after {draft_num} draft(s)\n")

        # Save final reports with timestamps
        print(save_to_pdf(
            content=state["draft"],
            filename=os.path.join(REPORTS_DIR, f"report_{timestamp}.pdf"),
            chart_metadata=state.get("chart_metadata", [])
        ))
        print(save_to_word(
            content=state["draft"],
            filename=os.path.join(REPORTS_DIR, f"report_{timestamp}.docx"),
            chart_metadata=state.get("chart_metadata", [])
        ))
        return END
    else:
        print(f"\n→ Continuing to draft {draft_num + 1} (score: {critique_score:.1f}/10, improvements needed)\n")
        return "continue"

def simulation_should_continue(state: AgentState) -> str:
    """Determine whether simulation should continue based on tool calls."""
    messages = state.get("raw_simulation", [])
    if not messages:
        return "end"
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None)
    return "continue" if tool_calls else "end"

def create_graph() -> StateGraph:
    """Create and configure the LangGraph workflow."""
    builder = StateGraph(AgentState)

    # Add all nodes
    builder.add_node("planning_agent", plan_node)
    builder.add_node("data_agent", data_agent)
    builder.add_node("chart_planning_node", chart_planning_node)
    builder.add_node("generate_charts", code_editor_agent)
    builder.add_node("simulation", simulation_agent)
    builder.add_node("writer", writer_node)
    builder.add_node("reflect", reflection_node)
    builder.add_node("research_agent", research_agent)
    builder.add_node("research_critique", research_critique_agent)
    builder.add_node("deep_research_agent", deep_research_agent)

    # Set entry point
    builder.set_entry_point("planning_agent")

    # Add edges
    builder.add_edge("planning_agent", "data_agent")
    builder.add_edge("data_agent", "chart_planning_node")
    builder.add_edge("chart_planning_node", "generate_charts")

    # Sequential research agents (avoids concurrent state updates)
    builder.add_edge("generate_charts", "research_agent")
    builder.add_edge("research_agent", "deep_research_agent")
    builder.add_edge("deep_research_agent", "simulation")

    builder.add_edge("simulation", "writer")
    builder.add_edge("writer", "reflect")
    builder.add_edge("research_critique", "writer")

    # Add conditional edge after reflection
    builder.add_conditional_edges(
        "reflect",
        should_continue,
        {END: END, "continue": "research_critique"}
    )

    return builder

async def run_agent(messages: str, parts_path: str, articles_path: str, tariff_path: str) -> Dict[str, Any]:
    """Run the document generation agent workflow."""
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        builder = create_graph()
        graph = builder.compile(checkpointer=checkpointer)

        # Save graph visualization
        graphs_dir = os.path.join(PROJECT_ROOT, "FastAPI", "reports_and_graphs", "langgraph_graphs")
        os.makedirs(graphs_dir, exist_ok=True)
        output_graph_path = os.path.join(graphs_dir, "main_langgraph.png")
        with open(output_graph_path, "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())

        final_state = {}

        # Initialize state for the graph
        initial_state = {
            'task': messages,
            'max_revisions': MAX_REVISIONS,
            'draft_number': 0,
            'db_content': [],
            'db_summary': '',
            'web_content': [],
            'deep_research_content': [],
            'deep_research_summary': '',
            'raw_simulation': [],
            'clean_simulation': '',
            'chart_metadata': [],
            'plan': '',
            'draft': '',
            'critique': '',
            'critique_score': 0.0,
            'chart_code': '',
            'chart_generation_success': False,
            'chart_generation_error': '',
            'chart_retry_count': 0,
            'max_chart_retries': MAX_CHART_RETRIES,
            'chart_plan': [],
            'current_chart_index': 0,
            'articles_path': articles_path,
            'parts_path': parts_path,
            'tariff_path': tariff_path,
            'messages': [],
            'remaining_steps': 5
        }

        config = {
            "recursion_limit": RECURSION_LIMIT,
            "configurable": {"thread_id": "1"}
        }

        async for s in graph.astream(initial_state, config=config):
            print(s)
            final_state = s

        return serialize_state(final_state)


def auto_supplychain_prompt_template(
    manufacturer: str,
    model: str,
    component: str,
    tariff_shock_country: str,
    rates: List[int],
    vat_rate: float,
    manufacturing_country: str
) -> str:
    rates_str = ", ".join(f"{r}%" for r in rates)
    return (
        f"Write me a professional report on the supply chain of the {manufacturer} {model} {component}. "
        f"Include a tariff shock simulation for parts imported from {tariff_shock_country} with rates of {rates_str}. "
        f"Assume VAT is {vat_rate}% and the manufacturing country is {manufacturing_country}."
    )

prompt = auto_supplychain_prompt_template(
    manufacturer="Toyota",
    model="RAV4",
    component="braking system",
    tariff_shock_country="Japan",
    rates=[10, 30, 60],
    vat_rate=20,
    manufacturing_country="United Kingdom"
)

async def target(inputs: Dict[str, Any]) -> Dict[str, str]:
    prompt = auto_supplychain_prompt_template(
        manufacturer=inputs["setup"]["manufacturer"],
        model=inputs["setup"]["model"],
        component=inputs["setup"]["component"],
        tariff_shock_country=inputs["setup"]["country"],
        rates=inputs["setup"]["rates"],
        vat_rate=inputs["setup"].get("vat_rate", 20.0),
        manufacturing_country=inputs["setup"].get("manufacturing_country", "United Kingdom")
    )

    parts_order = [
        "productGroupId",
        "partDescription",
        "quantity",
        "taxable"
    ]

    parts = inputs["parts"]
    parts_df = pd.DataFrame(parts)
    parts_df = parts_df[parts_order]

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as parts_tmp_file:
        parts_df.to_csv(parts_tmp_file.name, index=False)
        print(f"Temporary CSV file created: {parts_tmp_file.name}")

    articles_order = [
        "productGroupId",
        "articleNo",
        "articleProductName",
        "price",
        "countryOfOrigin",
        "supplierId",
        "supplierName"
    ]

    articles = inputs["articles"]
    articles_df = pd.DataFrame(articles)
    articles_df = articles_df[articles_order]

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as articles_tmp_file:
        articles_df.to_csv(articles_tmp_file.name, index=False)
        print(f"Temporary CSV file created: {articles_tmp_file.name}")

    final_state = await run_agent(prompt, parts_tmp_file.name, articles_tmp_file.name)
    draft = final_state.get("writer", {}).get("draft", "")

    return {"draft": draft}


if __name__ == "__main__":

    # dataset_name = "Toyota RAV4 Brake System"
    #
    # results = evaluate(
    #     target,
    #     data=dataset_name,
    #     evaluators=[report_quality_evaluator],
    #     experiment_prefix = "Toyota RAV4 Brake System experiment"
    # )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parts_path = os.path.join(base_dir, "test-data/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")
    articles_path = os.path.join(base_dir, "test-data/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    tariff_path = os.path.join(base_dir, "test-data/Toyota_RAV4_brake_dummy_data/RAV4_brake_tariff_data.csv")

    print(prompt)
    asyncio.run(run_agent(prompt, parts_path, articles_path, tariff_path))

    print("Done! Check results in LangSmith dashboard.")
