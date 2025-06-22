from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers

def handle_actions(action: dict) -> str:
    action_type = action.get("type")
    params = action.get("params", {})

    if action_type == "retrieve_manufacturers":
        response = fetch_manufacturers(**params)
        manufacturers_list = response.get("manufacturers", [])

        names = [m["brand"] for m in manufacturers_list]
        return "\n".join(f"- {name}" for name in names[:10])
    else:
        return f"Unknown action: {action_type}"