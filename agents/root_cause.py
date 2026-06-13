from utils.llm import llm

def root_cause_agent(state: dict):
    # Logic to find root cause based on parsed_data
    response = llm.invoke(f"Analyze root cause for: {state['parsed_data']}")
    return {"root_cause": response.content}