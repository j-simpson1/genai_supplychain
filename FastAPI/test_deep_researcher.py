from dotenv import load_dotenv
load_dotenv()

#!/usr/bin/env python3
"""
Test script for open_deep_research functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the FastAPI directory to Python path to enable imports
sys.path.append(str(Path(__file__).parent))

from langchain_core.messages import HumanMessage, SystemMessage
from open_deep_research.deep_researcher import deep_researcher
from langchain_openai import ChatOpenAI
from open_deep_research.configuration import Configuration
from open_deep_research.state import AgentInputState

RESEARCH_PLAN_PROMPT = """
You are a research planning assistant. Create a focused research query based on the user's task.
Provide a clear, specific research question that will yield actionable insights.
"""

async def test_deep_researcher():
    """Test the deep researcher functionality"""

    # Example task/query
    task = "Research alternative suppliers of brake components for the Toyota RAV-4"

    print(f"Testing deep researcher with task: {task}")
    print("-" * 80)

    try:
        # Create the research query (similar to your example)
        from langchain.chat_models import init_chat_model

        model = ChatOpenAI(model="gpt-4o")

        query_response = await model.ainvoke([
            SystemMessage(content=RESEARCH_PLAN_PROMPT),
            HumanMessage(content=task)
        ])

        query = query_response.content
        print(f"Generated research query: {query}")
        print("-" * 80)

        # Run the deep researcher
        response = await deep_researcher.ainvoke({
            "messages": [HumanMessage(content=query)],
        })

        # Extract the output
        output = response['messages'][-1].content
        print("Research Results:")
        print("=" * 80)
        print(output)
        print("=" * 80)

        # Simulate your content accumulation pattern
        content = []  # original content
        content.append(output)

        print(f"\nContent accumulated. Total items: {len(content)}")
        return content

    except Exception as e:
        print(f"Error during research: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def main():
    """Main function to run the test"""
    print("Starting Deep Researcher Test")
    print("=" * 80)

    content = await test_deep_researcher()

    if content:
        print(f"\nTest completed successfully. Generated {len(content)} content items.")
    else:
        print("\nTest failed - no content generated.")

if __name__ == "__main__":
    # Run the async test
    asyncio.run(main())