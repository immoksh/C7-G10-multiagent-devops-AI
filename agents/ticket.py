from utils.llm import llm

def ticket_agent(state: dict):
    # Formats for Jira/Ticket
    summary = f"Issue: {state['root_cause']}\nPlan: {state['remediation_plan']}"
    return {"ticket_details": summary}