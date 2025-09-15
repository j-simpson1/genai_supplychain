from dotenv import load_dotenv
load_dotenv()

import os
import traceback
import json, os, inspect
from datetime import datetime
from typing import Dict, List, Literal

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage, BaseMessage

from FastAPI.core.state import AgentState, TaskLedger, ProgressEntry
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
# MAGENTIC-ONE LEDGER UTILITIES
# =============================================================================

def log_progress(progress_ledger: List[ProgressEntry], agent: str, action: str,
                success: bool, details: str, artifacts: List[str] = None,
                stall_reason: str = None) -> List[ProgressEntry]:
    """Add an entry to the progress ledger."""
    entry: ProgressEntry = {
        "agent": agent,
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "details": details,
        "artifacts": artifacts,
        "stall_reason": stall_reason
    }
    return progress_ledger + [entry]

def update_task_ledger(task_ledger: TaskLedger, facts: List[str] = None,
                      hypotheses: List[str] = None, plan: Dict = None) -> TaskLedger:
    """Update the task ledger with new information."""
    updated_ledger = task_ledger.copy()

    if facts:
        updated_ledger["facts"] = list(set(updated_ledger.get("facts", []) + facts))

    if hypotheses:
        updated_ledger["hypotheses"] = list(set(updated_ledger.get("hypotheses", []) + hypotheses))

    if plan:
        updated_ledger["current_plan"] = plan

    return updated_ledger

def get_recent_failures(progress_ledger: List[ProgressEntry], limit: int = 5) -> List[ProgressEntry]:
    """Get recent failed actions to avoid repeating mistakes."""
    return [entry for entry in progress_ledger[-limit:] if not entry["success"]]

def get_successful_actions(progress_ledger: List[ProgressEntry], agent: str = None) -> List[str]:
    """Get list of successful actions, optionally filtered by agent."""
    successful = [entry["action"] for entry in progress_ledger if entry["success"]]
    if agent:
        successful = [entry["action"] for entry in progress_ledger
                     if entry["success"] and entry["agent"] == agent]
    return successful

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

    # Get ledgers
    task_ledger = state.get("task_ledger", {"facts": [], "hypotheses": [], "current_plan": {}})
    progress_ledger = state.get("progress_ledger", [])

    # Check recent failures to avoid repeating mistakes
    recent_failures = get_recent_failures(progress_ledger)
    failure_context = ""
    if recent_failures:
        failure_context = f"\n\nRecent failures to avoid:\n" + "\n".join(
            f"- {entry['action']}: {entry['stall_reason']}" for entry in recent_failures
        )

    # Check existing facts and hypotheses
    existing_facts = task_ledger.get("facts", [])
    existing_hypotheses = task_ledger.get("hypotheses", [])
    ledger_context = ""
    if existing_facts or existing_hypotheses:
        ledger_context = f"\n\nKnown facts: {existing_facts}\nWorking hypotheses: {existing_hypotheses}"

    # Check if we have existing analysis to build upon
    existing_analysis = state.get("db_content", [])
    analysis_context = ""
    if existing_analysis:
        analysis_context = f"\n\nExisting analysis results:\n{str(existing_analysis[-3:])}"  # Last 3 messages
    
    planning_prompt = f"""
    You are a Data Analysis Planner for automotive supply chain reports. Create a comprehensive execution plan.

    REPORT TASK: {task}
    REPORT PLAN: {plan}
    {ledger_context}
    {analysis_context}
    {failure_context}

    Based on the detailed report requirements, create a systematic data collection plan that covers ALL required components.

    Available tools for analysis:
    - parts_summary: Get parts count, VAT breakdown, origin countries, component costs
    - top_5_parts_by_price: Identify most expensive parts and their cost share
    - top_5_part_distribution_by_country: Analyze geographic distribution (key for Japan exposure)
    - bottom_quartile_average_price: Find cost-effective alternatives
    - total_component_price: Calculate total system costs with VAT
    - top_5_suppliers_by_articles: Identify supplier concentration and volumes

    Create a SPECIFIC execution plan with 4-5 steps, each specifying:
    1. EXACT TOOL(S) to use
    2. SPECIFIC DATA to extract
    3. HOW this supports the report requirements

    Format as: "Step X: Use [TOOL_NAME] to get [SPECIFIC_DATA] for [REPORT_SECTION]"

    Also identify 2-3 key hypotheses to test during analysis (e.g., "Japan suppliers dominate brake components", "Cost concentration in specific part types").

    Focus on the Component Analysis requirements: parts count, most expensive part, VAT breakdown, country origins, top suppliers.
    """
    
    response = planner_model.invoke([SystemMessage(content=planning_prompt)])

    # Extract steps and hypotheses from the response
    import re
    steps = re.findall(r'Step \d+:.*?(?=Step \d+:|$)', response.content, re.DOTALL)
    total_steps = len(steps)

    # Extract hypotheses if mentioned
    hypotheses_match = re.search(r'hypotheses?.*?:(.*?)(?:\n\n|\Z)', response.content, re.IGNORECASE | re.DOTALL)
    new_hypotheses = []
    if hypotheses_match:
        hypothesis_text = hypotheses_match.group(1)
        # Extract bullet points or numbered items
        hypothesis_items = re.findall(r'[•\-\*]\s*(.+)', hypothesis_text)
        if not hypothesis_items:
            hypothesis_items = re.findall(r'\d+\.\s*(.+)', hypothesis_text)
        new_hypotheses = [h.strip().strip('"') for h in hypothesis_items]

    # Update ledgers
    plan_dict = {
        "steps": [step.strip() for step in steps],
        "total_steps": total_steps,
        "rationale": f"Analysis plan for {task}",
        "created_at": datetime.now().isoformat()
    }

    updated_task_ledger = update_task_ledger(
        task_ledger,
        hypotheses=new_hypotheses,
        plan=plan_dict
    )

    updated_progress_ledger = log_progress(
        progress_ledger,
        agent="planner",
        action="create_analysis_plan",
        success=True,
        details=f"Created {total_steps}-step analysis plan with {len(new_hypotheses)} hypotheses",
        artifacts=["analysis_plan"]
    )

    # Store the analysis plan in the trajectory for coordination
    trajectory = state.get("trajectory", [])
    trajectory.append(f"PLANNING: {response.content}")

    return {
        "trajectory": trajectory,
        "db_content": state.get("db_content", []) + [response],
        "total_db_steps": total_steps,
        "current_db_step": 0,  # Reset step counter when new plan is created
        "db_plan_complete": False,  # Reset completion flag
        "task_ledger": updated_task_ledger,
        "progress_ledger": updated_progress_ledger
    }

def db_executor_node(state: AgentState):
    """
    INNER LOOP: Executes the planned database queries and tool calls.
    This is the "hands-on" agent that actually runs the analysis.
    """
    msgs = state.get("db_content", [])
    trajectory = state.get("trajectory", [])

    # Get ledgers
    task_ledger = state.get("task_ledger", {"facts": [], "hypotheses": [], "current_plan": {}})
    progress_ledger = state.get("progress_ledger", [])

    # Check recent failures to avoid repeating them
    recent_failures = get_recent_failures(progress_ledger)
    successful_tools = get_successful_actions(progress_ledger, "executor")

    # Get the next step from the plan rather than the entire plan
    latest_instruction = "Perform general data analysis"

    # Find the most recent planning message
    plan_content = None
    for msg in reversed(msgs):
        if (hasattr(msg, 'content') and
            not getattr(msg, 'name', None) and  # Not a tool response
            not getattr(msg, 'tool_calls', None)):  # Not an executor with tool calls

            content = msg.content
            if any(keyword in content.lower() for keyword in ['step 1:', 'step 2:', 'step 3:', 'step 4:', 'step 5:']):
                plan_content = content
                break

    if plan_content:
        # Extract individual steps from the plan
        import re
        steps = re.findall(r'Step \d+:.*?(?=Step \d+:|$)', plan_content, re.DOTALL)
        if steps:
            # Use explicit step tracking from state
            current_step = state.get('current_db_step', 0)
            plan_complete = state.get('db_plan_complete', False)
            total_steps = state.get('total_db_steps', 0)

            if not plan_complete and (total_steps == 0 or current_step < total_steps):
                # Normal execution - use current step
                step_index = min(current_step, len(steps) - 1)
                latest_instruction = steps[step_index].strip()
            else:
                # Plan complete OR exceeded steps - no more tool calls
                latest_instruction = "Plan complete: no more tool calls required, just print \"PLAN STEPS COMPLETE\""

    # Fallback: if no structured plan found AND not already set from plan completion
    if latest_instruction == "Perform general data analysis":
        for msg in reversed(msgs):
            if (hasattr(msg, 'content') and
                not getattr(msg, 'name', None) and
                not getattr(msg, 'tool_calls', None)):
                content = msg.content
                # Be more specific - only look for non-step planning content
                if any(keyword in content.lower() for keyword in ['available tools', 'execute systematic', 'comprehensive analysis']) and 'step' not in content.lower():
                    latest_instruction = "Continue systematic data analysis using available tools"
                    break
    
    # Simplified execution - only call tools, let coordinator handle summaries
    tools_used = set()
    for msg in msgs:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for call in msg.tool_calls:
                tools_used.add(call.get('name', ''))

    # Identify which tools haven't been used yet
    available_tools = [
        'parts_summary', 'top_5_parts_by_price', 'top_5_part_distribution_by_country',
        'bottom_quartile_average_price', 'total_component_price', 'top_5_suppliers_by_articles'
    ]
    unused_tools = [t for t in available_tools if t not in tools_used]

    # Always try to call tools - let coordinator decide when to summarize
    execution_prompt = f"""
    You are a Database Executor for automotive supply chain analysis. Execute the analysis plan systematically by calling tools.

    CURRENT INSTRUCTION: {latest_instruction}

    Tools already used: {', '.join(tools_used) if tools_used else 'None'}
    Available tools to use: {', '.join(unused_tools) if unused_tools else 'All tools have been used'}

    Your job is to CALL TOOLS to gather data. Use 1-3 DIFFERENT tools from the available set:
    - parts_summary(): Get parts count, VAT breakdown, country origins, component costs
    - top_5_parts_by_price(): Identify most expensive parts and their cost share
    - top_5_part_distribution_by_country(): Analyze geographic distribution (CRITICAL for Japan exposure)
    - bottom_quartile_average_price(): Find cost-effective alternatives
    - total_component_price(): Calculate total system costs with VAT
    - top_5_suppliers_by_articles(): Identify supplier concentration and volumes

    CRITICAL:
    - ALWAYS call tools with empty parameters - the system handles file paths automatically
    - Focus on calling tools you haven't used yet
    - Do NOT provide summaries - just call the tools to gather data
    - If all tools have been used, call the most relevant tools again for the current step
    """
    
    # Use only the latest instruction for context to avoid message order issues
    context_msg = HumanMessage(content=f"Execute this analysis plan: {latest_instruction}")
    
    response = db_executor_model.invoke([SystemMessage(content=execution_prompt), context_msg])

    # Get current state for progress tracking and increment step if tool calls made
    current_step = state.get('current_db_step', 0)
    plan_complete = state.get('db_plan_complete', False)
    total_steps = state.get('total_db_steps', 0)

    # Determine execution success and type
    has_tool_calls = getattr(response, 'tool_calls', None) is not None
    execution_type = "tool_execution" if has_tool_calls else "step_execution"

    # Increment step counter when executor generates tool calls (indicates step progress)
    if has_tool_calls and not plan_complete:
        current_step = current_step + 1
        # Check if plan is now complete
        if total_steps > 0 and current_step > total_steps:
            plan_complete = True

    # Extract potential facts from response (only for non-tool responses)
    response_content = response.content if hasattr(response, 'content') else str(response)
    new_facts = []

    # Simple fact extraction from non-tool responses (look for numbers, concrete statements)
    import re
    if not has_tool_calls and response_content:
        # Extract quantitative facts
        number_facts = re.findall(r'(\d+(?:\.\d+)?\s*(?:parts|components|suppliers|countries|%|percent|\$))', response_content, re.IGNORECASE)
        new_facts.extend([f"Analysis found: {fact}" for fact in number_facts[:3]])  # Limit to prevent noise

    # Update ledgers
    updated_task_ledger = task_ledger
    if new_facts:
        updated_task_ledger = update_task_ledger(task_ledger, facts=new_facts)

    updated_progress_ledger = log_progress(
        progress_ledger,
        agent="executor",
        action=execution_type,
        success=True,
        details=f"Generated response for step {current_step + 1}: {'Called tools' if has_tool_calls else 'Executed step'}",
        artifacts=["tool_calls"] if has_tool_calls else ["step_execution"]
    )

    # Update trajectory to track execution
    trajectory.append(f"EXECUTE: Generated response ({'with tools' if has_tool_calls else 'execution only'})")

    # Extract total steps from plan if not already set
    if total_steps == 0 and plan_content:
        import re
        steps = re.findall(r'Step \d+:.*?(?=Step \d+:|$)', plan_content, re.DOTALL)
        total_steps = len(steps)

    return {
        "db_content": msgs + [response],
        "trajectory": trajectory,
        "current_db_step": current_step,
        "db_plan_complete": plan_complete,
        "total_db_steps": total_steps,
        "task_ledger": updated_task_ledger,
        "progress_ledger": updated_progress_ledger
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

    # Get ledgers
    task_ledger = state.get("task_ledger", {"facts": [], "hypotheses": [], "current_plan": {}})
    progress_ledger = state.get("progress_ledger", [])

    last = msgs[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if not tool_calls:
        return {"db_content": outputs}

    # Get file paths from state
    state_articles = state.get("articles_path")
    state_parts = state.get("parts_path")

    # Track tool execution results
    tool_results = []
    new_facts = []

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
        
        # Remove any file path arguments (including empty strings) - we'll inject correct ones
        model_args.pop("articles_path", None)
        model_args.pop("parts_path", None)
        
        # Filter to accepted params (excluding file paths which we handle separately)
        fn = getattr(tool_obj, "func", None) or getattr(tool_obj, "coroutine", None)
        accepted = set(inspect.signature(fn).parameters.keys()) if fn else set()

        args = {k: v for k, v in model_args.items() if k in accepted and k not in ("articles_path", "parts_path")}
        
        # Always inject correct file paths if tool expects them
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
                tool_message = ToolMessage(
                    content=content_str,
                    name=tool_name,
                    tool_call_id=tool_id,
                )
                outputs.append(tool_message)

                # Track successful tool execution
                tool_results.append({
                    "tool": tool_name,
                    "success": True,
                    "result_length": len(content_str)
                })

                # Extract facts from tool results
                import re
                # Look for key-value pairs and numbers in the result
                if "total" in content_str.lower():
                    totals = re.findall(r'"total[^"]*":\s*([^,}\]]+)', content_str, re.IGNORECASE)
                    for total in totals[:2]:  # Limit to prevent noise
                        new_facts.append(f"Tool {tool_name} found total: {total.strip('\"')}")

                if "count" in content_str.lower():
                    counts = re.findall(r'"count[^"]*":\s*([^,}\]]+)', content_str, re.IGNORECASE)
                    for count in counts[:2]:
                        new_facts.append(f"Tool {tool_name} found count: {count.strip('\"')}")

            except Exception as e:
                error_message = ToolMessage(
                    content=json.dumps({"error": "tool_execution_failed", "tool": tool_name, "message": str(e)}),
                    name=tool_name,
                    tool_call_id=tool_id,
                )
                outputs.append(error_message)

                # Track failed tool execution
                tool_results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": str(e)
                })

    # Update ledgers with tool execution results
    updated_task_ledger = task_ledger
    if new_facts:
        updated_task_ledger = update_task_ledger(task_ledger, facts=new_facts)

    # Log progress for each tool executed
    updated_progress_ledger = progress_ledger
    for result in tool_results:
        updated_progress_ledger = log_progress(
            updated_progress_ledger,
            agent="tool_executor",
            action=f"execute_{result['tool']}",
            success=result["success"],
            details=f"Tool {result['tool']} executed" +
                   (f", returned {result.get('result_length', 0)} chars" if result["success"]
                    else f", failed with error: {result.get('error', 'unknown')}"),
            artifacts=[f"{result['tool']}_data"] if result["success"] else None,
            stall_reason=result.get('error') if not result["success"] else None
        )

    # Append tool results to existing db_content instead of overwriting
    existing_content = msgs or []
    return {
        "db_content": existing_content + outputs,
        "task_ledger": updated_task_ledger,
        "progress_ledger": updated_progress_ledger
    }

def db_critic_node(state: AgentState):
    """
    OUTER LOOP: Evaluates the quality and completeness of the analysis.
    Decides if more data gathering is needed or if we can proceed to synthesis.
    """
    db_content = state.get("db_content", [])
    plan = state.get('plan', 'No plan provided')
    trajectory = state.get("trajectory", [])

    # Get ledgers
    task_ledger = state.get("task_ledger", {"facts": [], "hypotheses": [], "current_plan": {}})
    progress_ledger = state.get("progress_ledger", [])

    # Analyze progress and failures
    recent_failures = get_recent_failures(progress_ledger, limit=3)
    successful_tools = get_successful_actions(progress_ledger, "tool_executor")
    total_actions = len(progress_ledger)

    # Get facts and hypotheses for evaluation
    known_facts = task_ledger.get("facts", [])
    hypotheses = task_ledger.get("hypotheses", [])
    current_plan = task_ledger.get("current_plan", {})

    # Get recent analysis results
    analysis_content = "\n\n".join(str(msg.content) for msg in db_content[-5:])
    
    critique_prompt = f"""
    You are a Data Analysis Critic for automotive supply chain reports. Evaluate the completeness and quality
    of the data analysis performed so far using the Magentic-One framework.

    ORIGINAL PLAN: {plan}

    TASK LEDGER STATUS:
    - Facts discovered: {len(known_facts)} ({', '.join(known_facts[:3]) + '...' if len(known_facts) > 3 else ', '.join(known_facts)})
    - Hypotheses tested: {len(hypotheses)} ({', '.join(hypotheses[:2]) + '...' if len(hypotheses) > 2 else ', '.join(hypotheses)})
    - Current plan steps: {current_plan.get('total_steps', 0)}

    PROGRESS LEDGER STATUS:
    - Total actions: {total_actions}
    - Successful tools used: {len(successful_tools)} ({', '.join(successful_tools[:4])})
    - Recent failures: {len(recent_failures)} ({'None' if not recent_failures else ', '.join([f['action'] for f in recent_failures])})

    ANALYSIS PERFORMED:
    {analysis_content}

    ANALYSIS TRAJECTORY:
    {str(trajectory[-3:]) if trajectory else "No trajectory"}

    Evaluate based on Magentic-One criteria:
    1. **Facts Sufficiency**: Are there enough concrete facts for decision-making?
    2. **Hypothesis Coverage**: Have key hypotheses been tested?
    3. **Tool Diversity**: Have different analysis tools been used effectively?
    4. **Progress Quality**: Is the agent making effective progress or stalling?
    5. **Actionability**: Can decision-makers use these insights?

    Respond with one of:
    - "SUFFICIENT": Analysis is complete, proceed to synthesis
    - "NEEDS_MORE": Analysis needs improvement, specify what's missing
    - "REFOCUS": Analysis went off-track, needs redirection

    If NEEDS_MORE or REFOCUS, provide specific guidance for what to analyze next based on the ledger gaps.
    """
    
    response = critic_model.invoke([SystemMessage(content=critique_prompt)])

    # Determine critique decision
    critique_content = response.content.upper()
    if "SUFFICIENT" in critique_content:
        decision = "sufficient"
    elif "NEEDS_MORE" in critique_content:
        decision = "needs_more"
    elif "REFOCUS" in critique_content:
        decision = "refocus"
    else:
        decision = "unclear"

    # Log critique progress
    updated_progress_ledger = log_progress(
        progress_ledger,
        agent="critic",
        action="evaluate_analysis",
        success=decision != "unclear",
        details=f"Critique decision: {decision}. Facts: {len(known_facts)}, Tools: {len(successful_tools)}",
        artifacts=["critique_evaluation"],
        stall_reason="Unclear critique response" if decision == "unclear" else None
    )

    # Update trajectory
    trajectory.append(f"CRITIQUE: {response.content}")

    return {
        "trajectory": trajectory,
        "db_content": db_content + [response],
        "progress_ledger": updated_progress_ledger
    }

def db_coordinator_node(state: AgentState):
    """
    MAGENTIC-ONE COORDINATOR: Routes between planning, execution, and critique based on progress.
    This is the "brain" that decides what to do next.
    Enhanced with step tracking based on executor-tool cycles.
    """
    db_content = state.get("db_content", [])
    trajectory = state.get("trajectory", [])

    # Get ledgers for enhanced decision making
    task_ledger = state.get("task_ledger", {"facts": [], "hypotheses": [], "current_plan": {}})
    progress_ledger = state.get("progress_ledger", [])

    # Get current step tracking state
    current_step = state.get('current_db_step', 0)
    total_steps = state.get('total_db_steps', 0)
    plan_complete = state.get('db_plan_complete', False)

    # Analyze progress ledger for intelligent routing and step tracking
    recent_failures = get_recent_failures(progress_ledger, limit=5)
    successful_tools = get_successful_actions(progress_ledger, "tool_executor")
    total_facts = len(task_ledger.get("facts", []))
    total_hypotheses = len(task_ledger.get("hypotheses", []))

    # Count agent activity from progress ledger (more accurate than trajectory parsing)
    agent_activity = {}
    for entry in progress_ledger[-15:]:  # Look at recent activity
        agent = entry["agent"]
        agent_activity[agent] = agent_activity.get(agent, 0) + 1

    planning_count = agent_activity.get("planner", 0)
    execution_count = agent_activity.get("executor", 0) + agent_activity.get("tool_executor", 0)
    critique_count = agent_activity.get("critic", 0)
    coordination_count = agent_activity.get("coordinator", 0)

    # Step tracking is now handled in the executor node
    # Just get the current values from state

    # Force proper workflow progression based on trajectory
    recent_actions = [t.split(":")[0] for t in trajectory[-10:] if ":" in t]

    # Enhanced decision logic using ledger intelligence
    if coordination_count > 8:
        decision = "SYNTHESIZE"
    elif plan_complete:
        decision = "SYNTHESIZE"
    # Check for stalling patterns (repeated failures without progress)
    elif len(recent_failures) >= 3 and total_facts < 3:
        decision = "PLAN"
    # Check for lack of initial planning
    elif planning_count == 0:
        decision = "PLAN"
    # Check for planning without execution
    elif planning_count > 0 and execution_count == 0:
        decision = "EXECUTE"
    # Check for sufficient facts without critique (coordinator requests summary via synthesis)
    elif total_facts >= 5 and critique_count == 0:
        decision = "CRITIQUE"
    # Check for execution without critique
    elif execution_count > 0 and critique_count == 0:
        decision = "CRITIQUE"
    # Handle critique results intelligently
    elif critique_count > 0:
        last_message = db_content[-1] if db_content else None
        if last_message and hasattr(last_message, 'content'):
            content = last_message.content.upper()
            if "NEEDS_MORE" in content and execution_count < 8:  # Allow more re-execution
                decision = "EXECUTE"
            elif "REFOCUS" in content and planning_count < 3:  # Allow re-planning
                decision = "PLAN"
            elif "SUFFICIENT" in content or total_facts >= 8:  # Good threshold of facts
                decision = "SYNTHESIZE"
            else:
                decision = "SYNTHESIZE"
        else:
            decision = "SYNTHESIZE"
    # Check for good coverage without critique (coordinator requests summary)
    elif total_facts >= 8 and len(successful_tools) >= 3:
        decision = "SYNTHESIZE"
    # Check if executor is not producing tools (possible summary mode)
    elif execution_count >= 3:
        recent_executions = [entry for entry in progress_ledger[-5:] if entry["agent"] == "executor"]
        tool_executions = [entry for entry in recent_executions if "tool_execution" in entry["action"]]
        if len(tool_executions) == 0 and len(recent_executions) >= 2:
            # Executor is not calling tools, move to synthesis
            decision = "SYNTHESIZE"
        else:
            decision = "EXECUTE"
    else:
        decision = "EXECUTE"  # Default to execution to gather more data
    
    # Map decisions to node names
    decision_mapping = {
        "PLAN": "planner",
        "EXECUTE": "executor", 
        "CRITIQUE": "critic",
        "SYNTHESIZE": "synthesizer"
    }
    
    # Log coordination decision
    updated_progress_ledger = log_progress(
        progress_ledger,
        agent="coordinator",
        action="route_decision",
        success=True,
        details=f"Decision: {decision}. Facts: {total_facts}, Tools: {len(successful_tools)}, Failures: {len(recent_failures)}",
        artifacts=["routing_decision"]
    )

    # Update trajectory with enhanced information
    completion_note = " [PLAN_COMPLETE]" if plan_complete else ""
    ledger_stats = f" [Facts:{total_facts}, Tools:{len(successful_tools)}, Failures:{len(recent_failures)}]"
    trajectory.append(f"COORDINATION: {decision} (P:{planning_count}, E:{execution_count}, C:{critique_count}, Coord:{coordination_count}){completion_note}{ledger_stats}")

    return {
        "trajectory": trajectory,
        "coordination_decision": decision_mapping.get(decision, "synthesizer"),
        "progress_ledger": updated_progress_ledger,
        "current_db_step": current_step,
        "db_plan_complete": plan_complete,
        "total_db_steps": total_steps
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

    # CRITICAL: Check if plan is complete - always go to coordinator
    plan_complete = state.get('db_plan_complete', False)
    if plan_complete:
        return "coordinate"

    last_message = db_content[-1]

    # If the last message has tool calls, continue to tools
    has_tool_calls = hasattr(last_message, "tool_calls") and last_message.tool_calls

    # Count recent tool calls to prevent loops - look at last 10 messages
    recent_tool_calls = sum(1 for msg in db_content[-10:] if getattr(msg, "tool_calls", None))

    # Limit consecutive tool calls - after 6 tool calls, go to coordination
    if has_tool_calls and recent_tool_calls < 6:
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
            "draft": "",
            "critique": "",
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
            "remaining_steps": 10,
            "current_db_step": 0,
            "total_db_steps": 0,
            "db_plan_complete": False,
            # Magentic-One Ledgers
            "task_ledger": {
                "facts": [],
                "hypotheses": [],
                "current_plan": {}
            },
            "progress_ledger": []
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