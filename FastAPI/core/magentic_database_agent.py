from dotenv import load_dotenv
load_dotenv()

import os
import traceback
import json, os, inspect
from typing import Dict, List, Literal

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage, BaseMessage

from FastAPI.core.state import AgentState
from FastAPI.core.database_tools import (
    parts_summary, top_5_parts_by_price, top_5_part_distribution_by_country, 
    bottom_quartile_average_price, total_component_price, top_5_suppliers_by_articles, calculator
)
from FastAPI.core.utils import _json_dump_safe

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports_and_graphs")

# Models for different roles
planner_model = ChatOpenAI(model="o4-mini")
executor_model = ChatOpenAI(model="o4-mini")
critic_model = ChatOpenAI(model="o4-mini")
coordinator_model = ChatOpenAI(model="o4-mini")

# Available database tools
tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    bottom_quartile_average_price,
    total_component_price,
    top_5_suppliers_by_articles
]

db_executor_model = ChatOpenAI(model="o4-mini").bind_tools(tools)
db_analyst_model = ChatOpenAI(model="o4-mini").bind_tools([calculator])
tools_by_name = {tool.name: tool for tool in tools}

# =============================================================================
# MAGENTIC-ONE AGENT NODES
# =============================================================================

def db_planner_node(state: AgentState):
    """
    OUTER LOOP: Plans the data analysis strategy based on the overall task and plan.
    Determines what insights are needed and creates an execution strategy.
    """
    plan = state.get('plan', 'No plan provided')
    task = state.get('task', 'No task provided')
    
    # Check if we have existing analysis to build upon
    existing_analysis = state.get("db_content", [])
    analysis_context = ""
    if existing_analysis:
        analysis_context = f"\n\nExisting analysis results:\n{str(existing_analysis[-3:])}"  # Last 3 messages
    
    planning_prompt = f"""
    You are a Data Analysis Planner for automotive supply chain reports. Your role is to create a strategic 
    data analysis plan based on the overall report requirements.

    REPORT TASK: {task}
    REPORT PLAN: {plan}
    {analysis_context}

    Your job is to determine what data insights are needed to support this report. Consider:
    1. What key metrics and KPIs would be most valuable?
    2. Which suppliers, parts, or countries should be analyzed?
    3. What cost analysis would support decision-making?
    4. What comparisons or distributions would provide insights?
    
    Available tools for analysis:
    - parts_summary: Get overall parts statistics
    - top_5_parts_by_price: Find most expensive parts
    - top_5_part_distribution_by_country: Analyze geographic distribution
    - bottom_quartile_average_price: Find cost-effective options
    - total_component_price: Calculate total costs
    - top_5_suppliers_by_articles: Analyze supplier landscape
    
    Create a strategic plan with 2-4 specific analysis steps. Be concrete about what insights each step will provide.
    Format as a clear, numbered list.
    """
    
    response = planner_model.invoke([SystemMessage(content=planning_prompt)])
    
    # Store the analysis plan in the trajectory for coordination
    trajectory = state.get("trajectory", [])
    trajectory.append(f"PLANNING: {response.content}")
    
    return {
        "trajectory": trajectory,
        "db_content": state.get("db_content", []) + [response]
    }

def db_executor_node(state: AgentState):
    """
    INNER LOOP: Executes the planned database queries and tool calls.
    This is the "hands-on" agent that actually runs the analysis.
    """
    msgs = state.get("db_content", [])
    trajectory = state.get("trajectory", [])
    
    # Get the latest plan/instruction from planner or coordinator
    latest_instruction = msgs[-1].content if msgs else "Perform general data analysis"
    
    # Check if we already have tool results and should wrap up execution
    recent_tool_outputs = [msg for msg in msgs[-5:] if getattr(msg, 'name', None)]
    
    if len(recent_tool_outputs) >= 2:  # If we have enough tool outputs, summarize instead of calling more tools
        execution_prompt = f"""
        You are a Database Executor. You have gathered data from tools. Now summarize your findings concisely.
        
        ORIGINAL INSTRUCTION: {latest_instruction}
        
        Based on the tool outputs you have received, provide a clear summary of what you found.
        Do NOT call more tools. Just summarize the results in 2-3 sentences.
        """
    else:
        execution_prompt = f"""
        You are a Database Executor for automotive supply chain analysis. Execute the analysis plan using available tools.
        
        CURRENT INSTRUCTION: {latest_instruction}
        
        Use 1-2 database tools to gather the required data. Focus on the most relevant analysis.
        
        Available tools:
        - parts_summary: Get overall parts statistics  
        - top_5_parts_by_price: Find most expensive parts
        - top_5_part_distribution_by_country: Analyze geographic distribution  
        - bottom_quartile_average_price: Find cost-effective options
        - total_component_price: Calculate total costs
        - top_5_suppliers_by_articles: Analyze supplier landscape
        """
    
    # Use only the latest instruction for context to avoid message order issues
    context_msg = HumanMessage(content=f"Execute this analysis plan: {latest_instruction}")
    
    response = db_executor_model.invoke([SystemMessage(content=execution_prompt), context_msg])
    
    # Update trajectory to track execution
    trajectory.append(f"EXECUTE: Generated response ({'with tools' if getattr(response, 'tool_calls', None) else 'summary only'})")
    
    return {
        "db_content": msgs + [response],
        "trajectory": trajectory
    }

def db_tool_node(state: AgentState):
    """
    Executes the actual database tools called by the executor.
    Enhanced with better error handling and context awareness.
    """
    outputs = []
    msgs = state.get("db_content") or []
    if not msgs:
        return {"db_content": outputs}
    
    last = msgs[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if not tool_calls:
        return {"db_content": outputs}

    # Get file paths from state
    state_articles = state.get("articles_path")
    state_parts = state.get("parts_path")

    for call in tool_calls:
        tool_name = (call or {}).get("name")
        tool_id = (call or {}).get("id") or ""
        tool_obj = tools_by_name.get(tool_name)

        if tool_obj is None:
            outputs.append(ToolMessage(
                content=json.dumps({"error": "unknown_tool", "tool": tool_name}),
                name=tool_name or "unknown",
                tool_call_id=tool_id,
            ))
            continue

        # Prepare arguments
        model_args = dict((call or {}).get("args") or {})
        model_args.pop("articles_path", None)
        model_args.pop("parts_path", None)

        # Filter to accepted params
        fn = getattr(tool_obj, "func", None) or getattr(tool_obj, "coroutine", None)
        accepted = set(inspect.signature(fn).parameters.keys()) if fn else set()

        args = {k: v for k, v in model_args.items() if k in accepted}
        if "articles_path" in accepted and isinstance(state_articles, str):
            args["articles_path"] = state_articles
        if "parts_path" in accepted and isinstance(state_parts, str):
            args["parts_path"] = state_parts

        # File existence check
        for p in ("articles_path", "parts_path"):
            if p in args and not os.path.isfile(args[p]):
                outputs.append(ToolMessage(
                    content=json.dumps({"error": "path_not_found", p+"_exists": False}),
                    name=tool_name,
                    tool_call_id=tool_id,
                ))
                break
        else:
            # Execute tool
            try:
                raw = tool_obj.invoke(args)
                content_str = _json_dump_safe(raw)
                outputs.append(ToolMessage(
                    content=content_str,
                    name=tool_name,
                    tool_call_id=tool_id,
                ))
            except Exception as e:
                outputs.append(ToolMessage(
                    content=json.dumps({"error": "tool_execution_failed", "tool": tool_name, "message": str(e)}),
                    name=tool_name,
                    tool_call_id=tool_id,
                ))

    return {"db_content": outputs}

def db_critic_node(state: AgentState):
    """
    OUTER LOOP: Evaluates the quality and completeness of the analysis.
    Decides if more data gathering is needed or if we can proceed to synthesis.
    """
    db_content = state.get("db_content", [])
    plan = state.get('plan', 'No plan provided')
    trajectory = state.get("trajectory", [])
    
    # Get recent analysis results
    analysis_content = "\n\n".join(str(msg.content) for msg in db_content[-5:])
    
    critique_prompt = f"""
    You are a Data Analysis Critic for automotive supply chain reports. Evaluate the completeness and quality 
    of the data analysis performed so far.

    ORIGINAL PLAN: {plan}
    
    ANALYSIS PERFORMED:
    {analysis_content}
    
    ANALYSIS TRAJECTORY:
    {str(trajectory[-3:]) if trajectory else "No trajectory"}

    Evaluate:
    1. **Completeness**: Does the analysis cover the key aspects needed for the report?
    2. **Quality**: Are the data points meaningful and actionable?
    3. **Gaps**: What critical information is missing?
    4. **Actionability**: Can decision-makers use these insights?

    Respond with one of:
    - "SUFFICIENT": Analysis is complete, proceed to synthesis
    - "NEEDS_MORE": Analysis needs improvement, specify what's missing
    - "REFOCUS": Analysis went off-track, needs redirection

    If NEEDS_MORE or REFOCUS, provide specific guidance for what to analyze next.
    """
    
    response = critic_model.invoke([SystemMessage(content=critique_prompt)])
    
    # Update trajectory
    trajectory.append(f"CRITIQUE: {response.content}")
    
    return {
        "trajectory": trajectory,
        "db_content": db_content + [response]
    }

def db_coordinator_node(state: AgentState):
    """
    MAGENTIC-ONE COORDINATOR: Routes between planning, execution, and critique based on progress.
    This is the "brain" that decides what to do next.
    """
    db_content = state.get("db_content", [])
    trajectory = state.get("trajectory", [])
    
    # Force proper workflow progression based on trajectory
    recent_actions = [t.split(":")[0] for t in trajectory[-10:] if ":" in t]
    
    # Count different types of actions
    planning_count = sum(1 for action in recent_actions if "PLANNING" in action)
    execution_count = sum(1 for action in recent_actions if "EXECUTE" in action or "TOOLS" in action)
    critique_count = sum(1 for action in recent_actions if "CRITIQUE" in action)
    coordination_count = sum(1 for action in recent_actions if "COORDINATION" in action)
    
    # Prevent infinite loops - if we've coordinated too much, force synthesis
    if coordination_count > 8:
        decision = "SYNTHESIZE"
    # Progressive workflow: Plan -> Execute -> Critique -> Synthesize
    elif planning_count == 0:
        decision = "PLAN"
    elif planning_count > 0 and execution_count == 0:
        decision = "EXECUTE"
    elif execution_count > 0 and critique_count == 0:
        decision = "CRITIQUE"
    elif critique_count > 0:
        # Check critique result
        last_message = db_content[-1] if db_content else None
        if last_message and hasattr(last_message, 'content'):
            content = last_message.content.upper()
            if "NEEDS_MORE" in content and execution_count < 3:  # Limit re-execution
                decision = "EXECUTE"
            elif "REFOCUS" in content and planning_count < 2:  # Limit re-planning
                decision = "PLAN"
            else:
                decision = "SYNTHESIZE"
        else:
            decision = "SYNTHESIZE"
    else:
        decision = "SYNTHESIZE"  # Default fallback
    
    # Map decisions to node names
    decision_mapping = {
        "PLAN": "planner",
        "EXECUTE": "executor", 
        "CRITIQUE": "critic",
        "SYNTHESIZE": "synthesizer"
    }
    
    # Update trajectory
    trajectory.append(f"COORDINATION: {decision} (P:{planning_count}, E:{execution_count}, C:{critique_count}, Coord:{coordination_count})")
    
    return {
        "trajectory": trajectory,
        "coordination_decision": decision_mapping.get(decision, "synthesizer")
    }

def db_synthesizer_node(state: AgentState):
    """
    FINAL SYNTHESIS: Creates the executive summary and actionable insights.
    Enhanced with calculator for any needed computations.
    """
    db_content_text = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))
    trajectory = state.get("trajectory", [])
    
    synthesis_prompt = f"""
    You are a Database Analysis Synthesizer. Create a comprehensive executive summary of the supply chain 
    data analysis performed.

    ANALYSIS RESULTS:
    {db_content_text}
    
    ANALYSIS JOURNEY:
    {str(trajectory)}

    Create a synthesis that includes:
    1. **Key Findings**: Most important insights from the data
    2. **Critical Metrics**: Essential numbers and KPIs  
    3. **Risk Factors**: Supply chain vulnerabilities identified
    4. **Opportunities**: Cost optimization or efficiency gains
    5. **Recommendations**: Actionable next steps

    Use the calculator tool for any arithmetic (totals, percentages, averages) needed.
    Be concise but comprehensive - this will inform strategic decisions.
    """

    response = db_analyst_model.invoke([SystemMessage(content=synthesis_prompt)])
    
    # Handle calculator tool calls if any
    tool_msgs = []
    while getattr(response, "tool_calls", None):
        for call in (response.tool_calls or []):
            if call.get("name") == "calculator":
                args = (call.get("args") or {})
                expression = args.get("expression") or args.get("expr") or ""
                tool_output = calculator.invoke({"expression": expression})
                tool_msgs.append(ToolMessage(
                    content=_json_dump_safe(tool_output),
                    name="calculator",
                    tool_call_id=call.get("id", "")
                ))
            else:
                tool_msgs.append(ToolMessage(
                    content=_json_dump_safe({"error": "unknown_tool", "tool": call.get("name")}),
                    name=call.get("name") or "unknown",
                    tool_call_id=call.get("id", "")
                ))

        if tool_msgs:
            messages = [SystemMessage(content=synthesis_prompt), response] + tool_msgs
            response = db_analyst_model.invoke(messages)
            tool_msgs = []

    return {"db_summary": response.content}

# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def should_continue_execution(state: AgentState):
    """
    Determine if we should continue with tool execution or return to coordination.
    This prevents infinite loops while allowing proper tool usage.
    """
    db_content = state.get("db_content", [])
    
    if not db_content:
        return "coordinate"
    
    last_message = db_content[-1]
    
    # If the last message has tool calls, continue to tools
    has_tool_calls = hasattr(last_message, "tool_calls") and last_message.tool_calls
    
    # Count recent tool calls to prevent loops - look at last 10 messages
    recent_tool_calls = sum(1 for msg in db_content[-10:] if getattr(msg, "tool_calls", None))
    
    # Limit consecutive tool calls - after 3 tool calls, go to coordination
    if has_tool_calls and recent_tool_calls < 3:
        return "tools"
    else:
        return "coordinate"

def coordination_router(state: AgentState):
    """Routes based on coordinator's decision."""
    decision = state.get("coordination_decision", "synthesizer")
    return decision

# =============================================================================
# GRAPH CONSTRUCTION  
# =============================================================================

def build_magentic_database_agent():
    """Builds the Magentic-One style database agent graph."""
    
    subgraph = StateGraph(AgentState)
    
    # Add all agent nodes
    subgraph.add_node("planner", db_planner_node)
    subgraph.add_node("executor", db_executor_node) 
    subgraph.add_node("tools", db_tool_node)
    subgraph.add_node("critic", db_critic_node)
    subgraph.add_node("coordinator", db_coordinator_node)
    subgraph.add_node("synthesizer", db_synthesizer_node)
    
    # Entry point
    subgraph.add_edge(START, "coordinator")
    
    # Executor flow (inner loop)
    subgraph.add_edge("tools", "executor")
    subgraph.add_conditional_edges(
        "executor",
        should_continue_execution,
        {
            "tools": "tools",
            "coordinate": "coordinator"
        }
    )
    
    # Coordinator routing (outer loop - Magentic-One style)
    subgraph.add_conditional_edges(
        "coordinator", 
        coordination_router,
        {
            "planner": "planner",
            "executor": "executor", 
            "critic": "critic",
            "synthesizer": "synthesizer"
        }
    )
    
    # All agents route back to coordinator (except synthesizer)
    subgraph.add_edge("planner", "coordinator")
    subgraph.add_edge("critic", "coordinator")
    
    # End point
    subgraph.add_edge("synthesizer", END)
    
    return subgraph.compile()

# =============================================================================
# MAIN AGENT INSTANCE
# =============================================================================

magentic_database_agent = build_magentic_database_agent()

# Save graph visualization
output_graph_path = os.path.join(REPORTS_DIR, "magentic_database_agent_langgraph.png")
with open(output_graph_path, "wb") as f:
    f.write(magentic_database_agent.get_graph().draw_mermaid_png())

# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def run_test():
        # Test file paths 
        articles_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        # Test state
        initial_state: AgentState = {
            "task": "Write a supply chain analysis report on Toyota RAV4 braking system with tariff shock simulation for Japan",
            "plan": "Analyze the cost structure, supplier dependencies, and geographic risks in the RAV4 brake system supply chain. Focus on identifying vulnerable suppliers and cost optimization opportunities.",
            "articles_path": articles_path,
            "parts_path": parts_path,
            "db_content": [],
            "trajectory": [],
            "coordination_decision": "",
            "db_summary": "",
            "revision_number": 0,
            "max_revisions": 1,
            "chart_plan": [],
            "chart_metadata": [],
            "current_chart_index": 0,
            "chart_code": "",
            "chart_generation_success": False,
            "chart_generation_error": "",
            "chart_retry_count": 0,
            "max_chart_retries": 1,
            "raw_simulation": [],
            "clean_simulation": "",
            "web_content": [],
            "messages": [],
            "remaining_steps": 10
        }

        print("\n--- Running Magentic-One Database Agent Test ---\n")
        try:
            async for step in magentic_database_agent.astream(initial_state):
                print("Step Output:", step)
            print("\n--- Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_test())