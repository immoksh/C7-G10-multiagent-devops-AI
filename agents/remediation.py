from utils.llm import llm

def remediation_agent(state: dict):
    # Generates a fix based on root cause
    response = llm.invoke(f"Propose a fix for: {state['root_cause']}")
    return {"remediation_plan": response.content}