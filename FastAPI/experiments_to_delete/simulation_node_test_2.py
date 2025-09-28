import os
import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# ---- Load environment variables ----
load_dotenv()

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")
articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")

# ---- STATE ----
class AgentState(TypedDict):
    task: str
    plan: List[str]
    target_csv: str
    results: Dict[str, Any]
    retries: int
    critique: str

# ---- SUPERVISOR NODE ----
def supervisor_node(state: AgentState):
    """Decides datasets & steps"""
    llm = ChatOpenAI(model="gpt-4o")
    prompt = f"""
    Task: {state['task']}
    Available datasets:
    - parts: brake parts (productGroupId, partDescription, quantity, taxable)
    - articles: brake articles (productGroupId, articleNo, articleProductName, price, countryOfOrigin, supplierId, supplierName)

    Decide:
    1. Which dataset(s) to use (parts / articles / both)
    2. High-level steps to accomplish the task
    """
    response = llm.invoke([HumanMessage(content=prompt)]).content

    dataset = "both"
    if "parts" in response.lower() and "articles" not in response.lower():
        dataset = "parts"
    elif "articles" in response.lower() and "parts" not in response.lower():
        dataset = "articles"

    steps = [s.strip() for s in response.split("\n") if s.strip()]
    return {"target_csv": dataset, "plan": steps}

# ---- CSV AGENT NODE ----
def csv_agent_node(state: AgentState):
    """Executes CSV operations including join and aggregation for parts summary"""
    # Load CSVs
    df_parts = pd.read_csv(parts_path)
    df_articles = pd.read_csv(articles_path)

    # --- Merge datasets on productGroupId ---
    merged = df_parts.merge(df_articles, on="productGroupId", how="left")

    # --- Compute per productGroupId summary ---
    def summarize_group(g):
        avg_price = g["price"].mean() if "price" in g else None
        num_articles = g["articleNo"].nunique() if "articleNo" in g else 0
        country_mode = g["countryOfOrigin"].mode()[0] if "countryOfOrigin" in g and not g["countryOfOrigin"].mode().empty else None
        quantity = g["quantity"].iloc[0] if "quantity" in g else None
        return pd.Series({
            "averagePrice": avg_price,
            "numArticles": num_articles,
            "mostCommonCountryOfOrigin": country_mode,
            "quantity": quantity
        })

    group_summary = (
        merged.groupby(["productGroupId", "partDescription"], as_index=False)
        .apply(summarize_group)
    )

    # --- Percentage of total cost ---
    group_summary["cost"] = group_summary["quantity"] * group_summary["averagePrice"]
    total_cost = group_summary["cost"].sum()
    group_summary["percentageOfTotalCost"] = (
        (group_summary["cost"] / total_cost * 100) if total_cost > 0 else 0
    )
    group_summary.drop(columns=["cost"], inplace=True)

    # Convert to list of dicts for serialization
    results = {"parts_summary": group_summary.to_dict(orient="records")}
    return {"results": results}

# ---- CRITIQUE NODE ----
def critique_node(state: AgentState):
    """LLM checks if results meet the task requirements"""
    llm = ChatOpenAI(model="gpt-4o")
    prompt = f"""
    Task: {state['task']}
    Results: {state['results']}

    Are all requested fields present and correctly computed?
    If something is missing, explain what and why.
    """
    critique = llm.invoke([HumanMessage(content=prompt)]).content
    return {"critique": critique}

# ---- REFLECTION NODE ----
def reflection_node(state: AgentState):
    """Fix missing results if possible"""
    critique = state["critique"].lower()
    results = dict(state["results"])  # copy
    retries = state.get("retries", 0) + 1

    # Basic reflection logic: if summary missing, recompute
    if "missing" in critique and "parts_summary" not in results:
        # Force recompute
        df_parts = pd.read_csv(parts_path)
        df_articles = pd.read_csv(articles_path)
        merged = df_parts.merge(df_articles, on="productGroupId", how="left")
        group_summary = (
            merged.groupby(["productGroupId", "partDescription"], as_index=False)
            .apply(lambda g: pd.Series({
                "averagePrice": g["price"].mean() if "price" in g else None,
                "numArticles": g["articleNo"].nunique() if "articleNo" in g else 0,
                "mostCommonCountryOfOrigin": g["countryOfOrigin"].mode()[0]
                    if "countryOfOrigin" in g and not g["countryOfOrigin"].mode().empty else None,
                "quantity": g["quantity"].iloc[0] if "quantity" in g else None
            }))
        )
        group_summary["cost"] = group_summary["quantity"] * group_summary["averagePrice"]
        total_cost = group_summary["cost"].sum()
        group_summary["percentageOfTotalCost"] = (
            (group_summary["cost"] / total_cost * 100) if total_cost > 0 else 0
        )
        group_summary.drop(columns=["cost"], inplace=True)
        results["parts_summary"] = group_summary.to_dict(orient="records")

    return {"results": results, "retries": retries}

# ---- GRAPH ----
graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("csv_agent", csv_agent_node)
graph.add_node("critique", critique_node)
graph.add_node("reflection", reflection_node)

graph.add_edge("supervisor", "csv_agent")
graph.add_edge("csv_agent", "critique")

# If critique finds issues and retries < 2 → reflection
graph.add_conditional_edges(
    "critique",
    lambda s: "reflection" if "missing" in s["critique"].lower() and s["retries"] < 2 else END
)
graph.add_edge("reflection", END)

graph.set_entry_point("supervisor")
app = graph.compile()

# ---- RUN (example) ----
if __name__ == "__main__":
    initial_state = {
        "task": "Get a parts summary with the following fields: productGroupId, partDescription, averagePrice, numArticles, mostCommonCountryOfOrigin, quantity and percentageOfTotalCost.",
        "plan": [],
        "target_csv": "",
        "results": {},
        "retries": 0,
        "critique": ""
    }
    for s in app.stream(initial_state):
        print(s)