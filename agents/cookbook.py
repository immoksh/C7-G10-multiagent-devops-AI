# agents/cookbook.py
from utils.llm import llm

def cookbook_agent(state: dict):  # <--- Ensure this name matches exactly
    # Your logic here
    response = llm.invoke(f"Find relevant SOPs for: {state.get('root_cause', '')}")
    return {"cookbook_ref": response.content}