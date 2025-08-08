import numpy as np
import json
from langchain_core.messages import ToolMessage

def summarize_simulation_content(sim: dict) -> dict:
    summary = sim.get("summary", {})
    scenarios = sim.get("scenarios", [])
    recommendations = sim.get("recommendations", [])
    cost_analysis = sim.get("current_cost_analysis", {})

    return {
        "target_country": sim.get("target_country"),
        "total_suppliers": summary.get("total_suppliers"),
        "affected_suppliers": summary.get("affected_suppliers"),
        "tariff_rates_tested": summary.get("tariff_rates_tested", []),
        "base_total_cost": round(cost_analysis.get("total_cost", 0), 2),
        "cost_increase_range_pct": [
            round(summary.get("cost_range", {}).get("min_increase", 0), 2),
            round(summary.get("cost_range", {}).get("max_increase", 0), 2)
        ],
        "scenarios": [
            {
                "tariff_rate": scenario["tariff_rate"],
                "cost_increase_pct": round(scenario["cost_analysis"]["percentage_increase"], 2),
                "final_cost": round(scenario["cost_analysis"]["final_cost"], 2),
                "key_suppliers": [
                    {
                        "supplier_name": s["supplier_name"],
                        "original_price": round(s["original_price"], 2),
                        "final_price": round(s["shock_final_price"], 2),
                        "price_increase": round(s["price_increase"], 2)
                    }
                    for s in scenario.get("affected_suppliers", [])[:2]
                ]
            }
            for scenario in scenarios
        ],
        "recommendations": [r["message"] for r in recommendations]
    }

import numpy as np

def convert_numpy(obj):
    """Recursively convert NumPy and pandas types to native Python types."""
    if isinstance(obj, dict):
        return {str(k): convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, "item"):
        return obj.item()
    else:
        return obj

def serialize_state(state):
    def serialize(obj):
        # Convert message objects to dict
        from langchain_core.messages import BaseMessage
        if isinstance(obj, BaseMessage):
            return {"type": obj.type, "content": obj.content}
        elif isinstance(obj, list):
            return [serialize(x) for x in obj]
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        else:
            return obj
    return serialize(state)


def get_last_tool_result(messages, tool_name: str) -> dict | None:
    """
    Find the last ToolMessage for the given tool_name in a list of messages.
    Returns the parsed dict content if JSON, or raw string if not JSON.
    """
    for msg in reversed(messages):
        # Only check ToolMessages
        if isinstance(msg, ToolMessage) and msg.name == tool_name:
            try:
                return json.loads(msg.content)
            except json.JSONDecodeError:
                return {"raw_content": msg.content}
    return None