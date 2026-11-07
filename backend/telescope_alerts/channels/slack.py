"""Slack incoming webhook; message shape from HyperDX transports/slack.ts (MIT)."""

from telescope_alerts.channels import net


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def payload(message: dict) -> dict:
    title = escape(message["title"])
    heading = f"*<{message['link']}|{title}>*" if message.get("link") else f"*{title}*"
    return {
        "text": message["title"],
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{heading}\n{escape(message['body'])}",
                },
            }
        ],
    }


def send(config: dict, message: dict, allow_private: bool):
    net.post(config["url"], payload(message), {}, allow_private)
