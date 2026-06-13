def notification_agent(state: dict):
    # Simulates sending a message
    print(f"Sending to Slack: {state['ticket_details']}")
    return {"notification_status": "SENT"}