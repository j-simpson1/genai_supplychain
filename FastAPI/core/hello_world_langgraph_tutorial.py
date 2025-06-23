from typing import Dict, TypedDict
from langgraph.graph import StateGraph

class AgentState(TypedDict): # Our state schema
    message : str

def greeting_node(state: AgentState) -> AgentState:
    """Simple node that adds a greeting message to the state"""

    state['message'] = "Hey " + state["message"] + ", how is your day going?"

    return state

graph = StateGraph(AgentState)

graph.add_node("greeter", greeting_node)

graph.set_entry_point("greeter")

graph.set_finish_point("greeter")

app = graph.compile()

# Replace the display code with:
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os

# Save the image - corrected method call
png_data = app.get_graph().draw_mermaid_png()

# Write binary data to file
with open("graph.png", "wb") as f:
    f.write(png_data)

# Display the image
img = mpimg.imread("graph.png")
plt.imshow(img)
plt.axis('off')
plt.show()

result = app.invoke({"message": "Bob"})

print(result["message"])
