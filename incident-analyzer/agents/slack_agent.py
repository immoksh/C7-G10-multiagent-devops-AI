import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def send_slack_notification(classification: dict, ticket_id: str, cookbook: str) -> str:
    """
    Sends an incident notification to the configured Slack channel.
    """
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("SLACK_CHANNEL_ID")

    message = f"""
🚨 *Incident Alert: {classification.get('severity', 'Unknown').upper()}* 🚨

*Root Cause:* {classification.get('root_cause')}
*Confidence:* {classification.get('confidence')}
*Jira Ticket:* {ticket_id if ticket_id else 'None'}

*Suggested Fix Checklist:*
{cookbook}
"""

    if slack_token and channel_id:
        try:
            client = WebClient(token=slack_token)
            response = client.chat_postMessage(
                channel=channel_id,
                text=message
            )
            return f"Slack notification sent to channel {channel_id}."
        except SlackApiError as e:
            print(f"Error sending Slack notification: {e.response['error']}")
            return f"Failed to send Slack notification: {e.response['error']}"
    else:
        # Mocking slack response
        print("Slack credentials not found. Mocking notification...")
        print("------- SLACK MESSAGE PREVIEW -------")
        print(message)
        print("-------------------------------------")
        return "Mocked Slack notification (Check console output)."
