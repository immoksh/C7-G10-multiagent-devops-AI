import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

def send_slack_message(message):
    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    client.chat_postMessage(
        channel=os.getenv("SLACK_CHANNEL_ID"),
        text=message
    )