"""Outbound email — SMTP only, stdlib. Disabled when SMTP_HOST is unset."""

from __future__ import annotations

import smtplib
import ssl
import threading
from email.message import EmailMessage
from typing import Iterable

from core.config import S


def smtp_configured() -> bool:
    return bool((S.smtp_host or "").strip())


def _from_addr() -> str:
    return (S.smtp_from or S.smtp_user or "noreply@graharekha.com").strip()


def send_mail(*, to: Iterable[str], subject: str, text: str) -> None:
    """Send a plain-text email. Raises on misconfiguration or SMTP failure."""
    host = (S.smtp_host or "").strip()
    if not host:
        raise RuntimeError("SMTP_HOST is not configured")
    recipients = [a.strip() for a in to if (a or "").strip()]
    if not recipients:
        raise RuntimeError("no recipients")

    msg = EmailMessage()
    msg["From"] = _from_addr()
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(text)

    user = (S.smtp_user or "").strip()
    password = S.smtp_password or ""
    port = int(S.smtp_port or 587)
    use_tls = bool(S.smtp_use_tls)

    if port == 465:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls(context=ssl.create_default_context())
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


def send_mail_async(**kwargs) -> None:
    """Fire-and-forget; logs failures without raising to the caller."""

    def _run() -> None:
        try:
            send_mail(**kwargs)
        except Exception as exc:  # noqa: BLE001
            print(f"[mail] send failed: {exc}", flush=True)

    threading.Thread(target=_run, daemon=True).start()


def notify_new_enquiry(*, enquiry_id: str, name: str, phone: str,
                       email: str, message: str, created_at: str) -> None:
    """Email the team when a contact form is submitted."""
    if not smtp_configured():
        print("[mail] enquiry saved but SMTP_HOST unset — no notification sent",
              flush=True)
        return
    to = [a.strip() for a in (S.enquiry_notify_to or "").split(",") if a.strip()]
    if not to:
        print("[mail] ENQUIRY_NOTIFY_TO empty — no notification sent", flush=True)
        return
    admin_url = "https://www.graharekha.com/#/analysis"
    body = (
        "New consultation request on GrahaRekha\n\n"
        f"Name:    {name}\n"
        f"Phone:   {phone}\n"
        f"Email:   {email}\n"
        f"When:    {created_at}\n"
        f"ID:      {enquiry_id}\n\n"
        f"Message:\n{message}\n\n"
        f"View and update status: {admin_url}\n"
    )
    send_mail_async(
        to=to,
        subject=f"[GrahaRekha] Consultation request — {name}",
        text=body,
    )
