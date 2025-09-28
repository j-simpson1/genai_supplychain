from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# ---- STATE ----
class AgentState(TypedDict):
    task: str
    plan: str
    steps: List[str]
    results: List[str]
    critique: str
    retries: int

# ---- NODES ----
def planner_node(state: AgentState):
    llm = ChatOpenAI(model="gpt-4o")
    prompt = f"Break down this task into clear steps:\n\n{state['task']}"
    response = llm.invoke([HumanMessage(content=prompt)])
    steps = [s for s in response.content.strip().split("\n") if s]
    return {"plan": response.content, "steps": steps}

def executor_node(state: AgentState):
    results = []
    for step in state['steps']:
        if "code" in step.lower() or "python" in step.lower():
            results.append(f"Code step detected, delegating: {step}")
        else:
            results.append(f"Executed: {step}")
    return {"results": results}

def code_writer_node(state: AgentState):
    llm = ChatOpenAI(model="gpt-4o")
    code_prompt = (
        "Write Python code to perform the following task:\n\n" +
        "\n".join(state["steps"])
    )
    response = llm.invoke([
        SystemMessage(content="You are an expert software engineer."),
        HumanMessage(content=code_prompt)
    ])
    code_result = f"Generated code:\n{response.content}"
    return {"results": [code_result]}

def critique_node(state: AgentState):
    llm = ChatOpenAI(model="gpt-4o")
    prompt = f"Critique these results and suggest fixes if needed:\n\n{state['results']}"
    critique = llm.invoke([HumanMessage(content=prompt)]).content
    if "error" in critique.lower() and state["retries"] < 3:
        return {"critique": critique, "retries": state["retries"] + 1}
    return {"critique": critique}

# ---- GRAPH ----
graph = StateGraph(AgentState)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("code_writer", code_writer_node)
graph.add_node("critique", critique_node)

# Entry point
graph.add_edge("__start__", "planner")

# Flow edges
def route_after_planner(state: AgentState):
    # If any step looks like code generation, go to code_writer
    if any("code" in s.lower() or "python" in s.lower() for s in state["steps"]):
        return "code_writer"
    return "executor"

graph.add_conditional_edges("planner", route_after_planner)
graph.add_edge("executor", "critique")
graph.add_edge("code_writer", "critique")
graph.add_conditional_edges("critique", lambda s: "planner" if s["retries"] < 3 else END)

# ---- COMPILE ----
app = graph.compile()

# ---- EXECUTION ----
state = {
    "task": "Write Python code to simulate tariff changes and summarize results",
    "plan": "", "steps": [], "results": [], "critique": "", "retries": 0
}

for event in app.stream(state):
    print(event)

final_state = app.invoke(state)
print("Final state:", final_state)