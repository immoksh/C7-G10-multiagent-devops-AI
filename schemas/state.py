from typing import TypedDict, Annotated, List, Optional
import operator

class AgentState(TypedDict):
    raw_logs: str
    parsed_data: Optional[dict]
    root_cause: Optional[str]
    remediation_plan: Optional[str]
    cookbook_ref: Optional[str]
    ticket_details: Optional[str]
    notification_status: Optional[str]