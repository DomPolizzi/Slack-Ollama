import os
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

from agent import run_agent

load_dotenv()

# Initialize Bolt App for Socket Mode
bolt_app = App(
    token=os.environ["SLACK_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

@bolt_app.event("message")
def handle_message_events(body, say, logger):
    event = body.get("event", {})
    user = event.get("user")
    text = event.get("text", "")
    channel = event.get("channel")

    # Ignore messages from bots or without text
    if not user or not text or event.get("bot_id"):
        return

    # Generate response via our agent
    result = run_agent(text)
    response_text = result["messages"][-1]["content"]

    # If public channel, DM the user
    if channel and channel.startswith(("C", "G")):
        im = bolt_app.client.conversations_open(users=user)
        dm_channel = im["channel"]["id"]
        bolt_app.client.chat_postMessage(channel=dm_channel, text=response_text)
    else:
        # Reply in thread or DM channel
        thread_ts = event.get("thread_ts") or event.get("ts")
        bolt_app.client.chat_postMessage(
            channel=channel,
            text=response_text,
            thread_ts=thread_ts
        )

def init_slack():
    """Start the Slack Socket Mode handler in a background thread."""
    handler = SocketModeHandler(bolt_app, os.environ["SLACK_APP_TOKEN"])
    thread = threading.Thread(target=handler.start, daemon=True)
    thread.start()
