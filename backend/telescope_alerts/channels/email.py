"""Email through Django's mail API; SMTP comes from alerts.email or Django's EMAIL_* settings."""

from django.core.mail import get_connection, send_mail


def connection(smtp: dict):
    if not smtp.get("host"):
        return get_connection()
    return get_connection(
        "django.core.mail.backends.smtp.EmailBackend",
        host=smtp["host"],
        port=smtp.get("port") or 25,
        username=smtp.get("username") or None,
        password=smtp.get("password") or None,
        use_tls=bool(smtp.get("use_tls")),
        use_ssl=bool(smtp.get("use_ssl")),
        timeout=10,
    )


def text(message: dict) -> str:
    parts = [message["body"]]
    if message.get("link"):
        parts.append(f"Open in Telescope: {message['link']}")
    return "\n\n".join(parts)


def send(config: dict, message: dict, smtp: dict):
    send_mail(
        # Group keys come from log data; a line break in a header is refused by Django.
        subject=" ".join(message["title"].split())[:250],
        message=text(message),
        from_email=smtp.get("from_email") or None,
        recipient_list=config["recipients"],
        connection=connection(smtp),
    )
