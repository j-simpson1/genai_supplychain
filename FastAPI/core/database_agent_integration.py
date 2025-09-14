"""
Integration guide for replacing the existing database agent with Magentic-One version.

This file shows how to update your document_generator.py to use the new Magentic-One database agent.
"""

# STEP 1: Update imports in document_generator.py
# Replace:
# from FastAPI.core.database_agent import database_agent

# With:
# from FastAPI.core.magentic_database_agent import magentic_database_agent

# STEP 2: Update the node in the StateGraph (line ~190 in document_generator.py)
# Replace:
# builder.add_node("db_agent", database_agent)

# With:
# builder.add_node("db_agent", magentic_database_agent)

# STEP 3: (Optional) Add state fields to track coordination
# Add to AgentState in state.py:
"""
    # Magentic-One coordination fields
    trajectory: List[str] = []
    coordination_decision: str = ""
"""

# STEP 4: Test the integration
def test_integration():
    """
    Test script to validate the Magentic-One database agent works with your existing workflow.
    Run this before making the full integration.
    """
    import asyncio
    import os
    from FastAPI.core.magentic_database_agent import magentic_database_agent
    from FastAPI.core.state import AgentState
    
    async def run_integration_test():
        # Use your existing test data paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        articles_path = os.path.join(base_dir, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(base_dir, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        # State matching your existing document_generator format
        state: AgentState = {
            "task": "Write a supply chain analysis report on Toyota RAV4 braking system",
            "plan": "Analyze cost structure, supplier dependencies, and identify optimization opportunities in the RAV4 brake supply chain.",
            "draft": "",
            "critique": "",
            "web_content": [],
            "db_content": [],
            "db_summary": "",
            "trajectory": [],
            "raw_simulation": [],
            "clean_simulation": "",
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
            "articles_path": articles_path,
            "parts_path": parts_path,
            "messages": [],
            "remaining_steps": 10,
            "coordination_decision": ""  # New field for Magentic-One
        }

        print("🔄 Testing Magentic-One Database Agent Integration...")
        
        try:
            result_state = await magentic_database_agent.ainvoke(state)
            
            print("✅ Integration test successful!")
            print(f"📊 DB Summary length: {len(result_state.get('db_summary', ''))}")
            print(f"🛤️  Trajectory steps: {len(result_state.get('trajectory', []))}")
            print(f"📝 DB Content messages: {len(result_state.get('db_content', []))}")
            
            # Preview the results
            db_summary = result_state.get('db_summary', '')
            if db_summary:
                print(f"\n📋 Sample DB Summary (first 200 chars):\n{db_summary[:200]}...")
            
            trajectory = result_state.get('trajectory', [])
            if trajectory:
                print(f"\n🛤️  Analysis Trajectory:")
                for i, step in enumerate(trajectory[-3:], 1):  # Last 3 steps
                    print(f"   {i}. {step}")
                    
            return True
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    return asyncio.run(run_integration_test())

# STEP 5: Rollback plan (if needed)
def rollback_to_original():
    """
    Instructions to rollback to original database agent if issues occur.
    """
    print("""
    🔄 ROLLBACK INSTRUCTIONS:
    
    1. In document_generator.py, change import back to:
       from FastAPI.core.database_agent import database_agent
    
    2. Change the node back to:
       builder.add_node("db_agent", database_agent)
    
    3. Remove any new state fields if added:
       - trajectory
       - coordination_decision
    
    4. Restart your FastAPI server
    """)

if __name__ == "__main__":
    print("🚀 Starting Magentic-One Database Agent Integration Test...\n")
    
    success = test_integration()
    
    if success:
        print("""
        ✅ INTEGRATION READY!
        
        Next steps:
        1. Update FastAPI/core/document_generator.py imports
        2. Replace the database_agent node with magentic_database_agent  
        3. Restart your FastAPI server
        4. Test with your existing /run_simulation endpoint
        
        The Magentic-One agent will provide:
        • Strategic analysis planning
        • Intelligent tool execution
        • Quality critique and iteration
        • Comprehensive synthesis
        """)
    else:
        print("""
        ❌ INTEGRATION ISSUES DETECTED
        
        Please check:
        1. File paths to CSV data
        2. Database tools are working
        3. All dependencies are installed
        
        Fix issues before integrating into main workflow.
        """)