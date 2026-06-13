import sys
import os

from langgraph.graph import StateGraph, END
from schemas.state import AgentState
from agents.log_reader import log_reader_agent
from agents.root_cause import root_cause_agent
from agents.remediation import remediation_agent
from agents.cookbook import cookbook_agent
from agents.ticket import ticket_agent
from agents.notification import notification_agent

# Adds the root directory (one level up) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now the imports will work
from schemas.state import AgentState
# ... rest of your code

# Initialize Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("reader", log_reader_agent)
workflow.add_node("root_cause", root_cause_agent)
workflow.add_node("remediation", remediation_agent)
workflow.add_node("cookbook", cookbook_agent)
workflow.add_node("ticket", ticket_agent)
workflow.add_node("notify", notification_agent)

# Set Flow
workflow.set_entry_point("reader")
workflow.add_edge("reader", "root_cause")
workflow.add_edge("root_cause", "remediation")
workflow.add_edge("remediation", "cookbook")
workflow.add_edge("cookbook", "ticket")
workflow.add_edge("ticket", "notify")
workflow.add_edge("notify", END)

# Compile
app = workflow.compile()