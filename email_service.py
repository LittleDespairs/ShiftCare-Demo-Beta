from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate
from html import escape
from typing import Any

from app_config import AppConfig, get_app_config


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSendResult:
    status: str
    detail: str = ""

    @property
    def sent(self) -> bool:
        return self.status == "sent"

    def as_public_dict(self) -> dict[str, str]:
        payload = {"status": self.status}
        if self.detail:
            payload["detail"] = self.detail
        return payload


def email_delivery_is_enabled(config: AppConfig | None = None) -> bool:
    config = config or get_app_config()
    return bool(config.email_enabled and config.email_from and config.smtp_host and config.smtp_port)


def _send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    config: AppConfig | None = None,
    reply_to: str | None = None,
) -> EmailSendResult:
    config = config or get_app_config()
    if not email_delivery_is_enabled(config):
        return EmailSendResult("disabled", "Email delivery is not configured.")

    message = EmailMessage()
    message["From"] = config.email_from
    message["To"] = to_email
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    effective_reply_to = (reply_to or config.email_reply_to or "").strip()
    if effective_reply_to:
        message["Reply-To"] = effective_reply_to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        if config.smtp_use_ssl:
            with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=15) as smtp:
                _login_if_needed(smtp, config)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as smtp:
                if config.smtp_use_tls:
                    smtp.starttls()
                _login_if_needed(smtp, config)
                smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - exact SMTP failures depend on provider/runtime.
        LOGGER.warning("Email delivery failed for %s: %s", to_email, exc)
        return EmailSendResult("failed", "Email delivery failed.")
    return EmailSendResult("sent")


def _login_if_needed(smtp: smtplib.SMTP, config: AppConfig) -> None:
    if config.smtp_username or config.smtp_password:
        smtp.login(config.smtp_username, config.smtp_password)


def _button_html(label: str, url: str) -> str:
    safe_label = escape(label)
    safe_url = escape(url, quote=True)
    return (
        '<p style="margin:24px 0">'
        f'<a href="{safe_url}" '
        'style="background:#2563eb;color:#ffffff;padding:12px 18px;border-radius:6px;'
        'text-decoration:none;display:inline-block;font-weight:600">'
        f"{safe_label}</a></p>"
    )


def _layout_html(title: str, paragraphs: list[str], button_label: str, button_url: str) -> str:
    paragraph_html = "\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
    return f"""<!doctype html>
<html>
<body style="font-family:Arial,sans-serif;color:#111827;line-height:1.5">
  <h1 style="font-size:20px;margin:0 0 16px">{escape(title)}</h1>
  {paragraph_html}
  {_button_html(button_label, button_url)}
  <p style="color:#6b7280;font-size:13px">If the button does not work, copy and paste this link into your browser:</p>
  <p style="word-break:break-all;color:#374151;font-size:13px">{escape(button_url)}</p>
</body>
</html>"""


def _message_html(title: str, sections: list[tuple[str, str]]) -> str:
    section_html = "\n".join(
        (
            '<section style="margin:16px 0">'
            f'<h2 style="font-size:14px;margin:0 0 6px;color:#374151">{escape(label)}</h2>'
            f'<pre style="white-space:pre-wrap;font-family:Arial,sans-serif;'
            f'background:#f8fafc;border:1px solid #e5e7eb;border-radius:6px;'
            f'padding:10px;color:#111827">{escape(value or "-")}</pre>'
            "</section>"
        )
        for label, value in sections
    )
    return f"""<!doctype html>
<html>
<body style="font-family:Arial,sans-serif;color:#111827;line-height:1.5">
  <h1 style="font-size:20px;margin:0 0 16px">{escape(title)}</h1>
  {section_html}
</body>
</html>"""


def send_invitation_email(
    *,
    to_email: str,
    invitation_url: str,
    organization_name: str,
    role: str,
    expires_at: str,
    employee_name: str = "",
    config: AppConfig | None = None,
) -> EmailSendResult:
    subject = f"Invitation to join {organization_name}"
    details = [f"You have been invited to join {organization_name} as {role.replace('_', ' ')}."]
    if employee_name:
        details.append(f"This invitation is linked to employee profile: {employee_name}.")
    details.append(f"The invitation expires at {expires_at}.")
    text_body = "\n\n".join([*details, f"Accept invitation: {invitation_url}"])
    html_body = _layout_html("Accept your ShiftCare invitation", details, "Accept invitation", invitation_url)
    return _send_email(to_email, subject, text_body, html_body, config)


def send_password_reset_email(
    *,
    to_email: str,
    reset_url: str,
    config: AppConfig | None = None,
) -> EmailSendResult:
    subject = "Reset your ShiftCare password"
    paragraphs = [
        "A password reset was requested for your ShiftCare account.",
        "This link expires in 24 hours. If you did not request this, you can ignore this email.",
    ]
    text_body = "\n\n".join([*paragraphs, f"Reset password: {reset_url}"])
    html_body = _layout_html("Reset your ShiftCare password", paragraphs, "Reset password", reset_url)
    return _send_email(to_email, subject, text_body, html_body, config)


def send_email_verification_email(
    *,
    to_email: str,
    verification_url: str,
    config: AppConfig | None = None,
) -> EmailSendResult:
    subject = "Verify your ShiftCare email"
    paragraphs = [
        "Please verify this email address for your ShiftCare account.",
        "This link expires in 7 days.",
    ]
    text_body = "\n\n".join([*paragraphs, f"Verify email: {verification_url}"])
    html_body = _layout_html("Verify your ShiftCare email", paragraphs, "Verify email", verification_url)
    return _send_email(to_email, subject, text_body, html_body, config)


def send_feedback_report_email(
    *,
    report: dict[str, Any],
    config: AppConfig | None = None,
) -> EmailSendResult:
    config = config or get_app_config()
    to_email = config.support_reports_email.strip()
    if not to_email:
        return EmailSendResult("disabled", "Support reports email is not configured.")

    report_type = str(report.get("report_type") or "feedback")
    type_label = "Bug" if report_type == "bug" else "Feature request" if report_type == "feature_request" else "Feedback"
    title = str(report.get("title") or "Untitled report").strip()[:160]
    subject = f"[{type_label}] {title}"
    contact_email = str(report.get("contact_email") or "").strip()

    sections = [
        ("Summary", f"{type_label} / {report.get('severity') or '-'} / {report.get('area') or '-'}"),
        ("Title", title),
        ("Description", str(report.get("description") or "")),
        ("Steps to reproduce", str(report.get("steps_to_reproduce") or "")),
        ("Expected result", str(report.get("expected_result") or "")),
        ("Actual result", str(report.get("actual_result") or "")),
        (
            "Reporter",
            "\n".join(
                [
                    f"Name: {report.get('user_name') or '-'}",
                    f"Email: {report.get('user_email') or '-'}",
                    f"Contact: {contact_email or '-'}",
                    f"Organization: {report.get('organization_name') or '-'} ({report.get('organization_id') or '-'})",
                    f"Role: {report.get('role') or '-'}",
                ]
            ),
        ),
        (
            "Runtime",
            "\n".join(
                [
                    f"Report ID: {report.get('public_id') or '-'}",
                    f"App version: {report.get('app_version') or '-'}",
                    f"Environment: {report.get('runtime_environment') or '-'}",
                    f"Page URL: {report.get('page_url') or '-'}",
                    f"Created at: {report.get('created_at') or '-'}",
                ]
            ),
        ),
        ("Client context", str(report.get("client_context_json") or "{}")),
        ("Server context", str(report.get("server_context_json") or "{}")),
    ]
    text_body = "\n\n".join(f"{label}\n{value or '-'}" for label, value in sections)
    html_body = _message_html(subject, sections)
    return _send_email(to_email, subject, text_body, html_body, config, reply_to=contact_email or None)


def public_email_status(result: EmailSendResult | None) -> dict[str, Any]:
    if result is None:
        return EmailSendResult("not_attempted").as_public_dict()
    return result.as_public_dict()
