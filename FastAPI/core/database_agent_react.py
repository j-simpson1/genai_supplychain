from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from data_tools import (
    parts_summary, top_5_parts_by_price, top_5_part_distribution_by_country,
    bottom_quartile_average_price, total_component_price, top_5_suppliers_by_articles,
    calculator
)

class ReActDatabaseAgent:
    def __init__(self, model_name: str = "o4-mini"):
        self.model = ChatOpenAI(model=model_name)
        self.conversation_history = []

        # Available tools mapped by name
        self.tools = {
            "parts_summary": parts_summary,
            "top_5_parts_by_price": top_5_parts_by_price,
            "top_5_part_distribution_by_country": top_5_part_distribution_by_country,
            "bottom_quartile_average_price": bottom_quartile_average_price,
            "total_component_price": total_component_price,
            "top_5_suppliers_by_articles": top_5_suppliers_by_articles,
            "calculator": calculator
        }

        # Regex pattern for parsing actions
        self.action_pattern = re.compile(r'^Action: (\w+): (.*)$', re.MULTILINE)

        # ReAct system prompt
        self.system_prompt = """
You are a database analysis agent that runs in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer.

Use Thought to describe your reasoning about the data query you have been asked.
Use Action to run one of the database tools available to you - then return PAUSE.
Observation will be the result of running those tools.

Your available actions are:

parts_summary:
e.g. parts_summary: analyze all parts with pricing and country data
Returns comprehensive summary of parts with bottom-quartile pricing, quantities, and country origins

top_5_parts_by_price:
e.g. top_5_parts_by_price: find most expensive parts
Returns the 5 most expensive parts by bottom-quartile average price

top_5_part_distribution_by_country:
e.g. top_5_part_distribution_by_country: analyze geographic distribution
Returns top 5 countries by number of unique parts

bottom_quartile_average_price:
e.g. bottom_quartile_average_price: get conservative pricing estimates
Returns bottom-quartile average prices for all parts with descriptions and totals

total_component_price:
e.g. total_component_price: 20
Calculate total component cost with VAT rate (use rate like 20 for 20% or 0.2)

top_5_suppliers_by_articles:
e.g. top_5_suppliers_by_articles: find major suppliers
Returns suppliers with the most unique articles

calculator:
e.g. calculator: sum([47.02, 130.76])
Evaluates arithmetic expressions, supports sum, mean, round, percentages

Always use the most relevant tool for the question asked.
Only perform ONE action per turn, then return PAUSE.

Example session:

Question: What are the top 5 most expensive parts?
Thought: I need to find the parts with the highest prices. The top_5_parts_by_price tool is perfect for this.
Action: top_5_parts_by_price: find most expensive parts
PAUSE

You will be called again with this:

Observation: [{"productId": 123, "partDescription": "Brake Pad", "bottomQuartileAvgPrice": 45.20, ...}]

You then output:

Answer: The top 5 most expensive parts are: 1) Brake Pad ($45.20), 2) ...
""".strip()

    def _execute_tool(self, tool_name: str, tool_input: str, articles_path: str, parts_path: str) -> str:
        """Execute a tool and return the result"""
        try:
            if tool_name not in self.tools:
                return json.dumps({"error": "unknown_tool", "tool": tool_name})

            tool = self.tools[tool_name]

            # Prepare arguments based on tool requirements
            if tool_name == "calculator":
                result = tool.invoke({"expression": tool_input.strip()})
            elif tool_name == "top_5_suppliers_by_articles":
                result = tool.invoke({"articles_path": articles_path})
            elif tool_name == "total_component_price":
                # Extract VAT rate from input
                vat_rate = 0.2  # default
                try:
                    # Look for numbers in the input
                    numbers = re.findall(r'\d+\.?\d*', tool_input)
                    if numbers:
                        vat_rate = float(numbers[0])
                        if vat_rate > 1:
                            vat_rate = vat_rate / 100.0
                except:
                    pass
                result = tool.invoke({
                    "articles_path": articles_path,
                    "parts_path": parts_path,
                    "vat_rate": vat_rate
                })
            else:
                # Most tools need both paths
                result = tool.invoke({
                    "articles_path": articles_path,
                    "parts_path": parts_path
                })

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"error": "tool_execution_failed", "tool": tool_name, "message": str(e)})

    def query(self, question: str, articles_path: str, parts_path: str, max_turns: int = 5) -> str:
        """
        Execute a ReAct query loop
        """
        # Reset conversation for new query
        self.conversation_history = [SystemMessage(content=self.system_prompt)]

        next_prompt = question

        for turn in range(max_turns):
            # Get response from model
            self.conversation_history.append(HumanMessage(content=next_prompt))
            response = self.model.invoke(self.conversation_history)
            self.conversation_history.append(AIMessage(content=response.content))

            print(f"\n--- Turn {turn + 1} ---")
            print(response.content)

            # Check for actions in the response
            actions = self.action_pattern.findall(response.content)

            if actions:
                # Execute the first action found
                action_name, action_input = actions[0]
                print(f"\n -- running {action_name}: {action_input}")

                # Execute the tool
                observation = self._execute_tool(action_name, action_input, articles_path, parts_path)
                print(f"Observation: {observation}")

                # Set up next prompt
                next_prompt = f"Observation: {observation}"

            else:
                # No more actions, we have our final answer
                return response.content

        # If we hit max turns, return the last response
        return self.conversation_history[-1].content if self.conversation_history else "No response generated"

    def get_available_tools(self) -> Dict[str, str]:
        """Return a dictionary of available tools and their descriptions"""
        return {name: tool.description for name, tool in self.tools.items()}


# Convenience function matching original interface
def query_database_react(question: str, articles_path: str, parts_path: str, max_turns: int = 5) -> str:
    """
    Simple function interface for ReAct database queries
    """
    agent = ReActDatabaseAgent()
    return agent.query(question, articles_path, parts_path, max_turns)


if __name__ == "__main__":
    # Test the ReAct agent
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Use existing test data paths
    articles_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    parts_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

    # Create and test the agent
    agent = ReActDatabaseAgent()

    # Test questions
    test_questions = [
        "What are the top 5 most expensive parts?",
        "What is the total component cost with 20% VAT?",
        "Which countries have the most parts distribution?"
    ]

    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"QUESTION: {question}")
        print('='*60)

        try:
            answer = agent.query(question, articles_path, parts_path)
            print(f"\nFINAL ANSWER: {answer}")
        except Exception as e:
            print(f"Error: {e}")