"""Email notifications via SMTP (Gmail app password)."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def send_email(subject: str, body: str) -> None:
    to_addr = _env("ALERT_EMAIL_TO")
    from_addr = _env("ALERT_EMAIL_FROM") or _env("SMTP_USER")
    host = _env("SMTP_HOST", "smtp.gmail.com")
    port = int(_env("SMTP_PORT", "587"))
    user = _env("SMTP_USER")
    password = _env("SMTP_PASSWORD").replace(" ", "")

    if not all([to_addr, from_addr, user, password]):
        raise RuntimeError(
            "Set ALERT_EMAIL_TO, ALERT_EMAIL_FROM, SMTP_USER, SMTP_PASSWORD in environment."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
