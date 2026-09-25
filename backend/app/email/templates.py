"""Plain-text emails. Production would move these to HTML templates with a text fallback."""

from app.config import get_settings
from app.models.lead import Lead


def prospect_confirmation(lead: Lead) -> tuple[str, str]:
    subject = "We received your information"
    body = (
        f"Hi {lead.first_name},\n\n"
        "Thanks for reaching out. We received your details and resume, and an attorney will "
        "review them and get back to you soon.\n\n"
        "No need to reply to this email.\n"
    )
    return subject, body


def attorney_notification(lead: Lead) -> tuple[str, str]:
    subject = f"New lead: {lead.first_name} {lead.last_name}"
    body = (
        "A new lead was submitted.\n\n"
        f"Name:   {lead.first_name} {lead.last_name}\n"
        f"Email:  {lead.email}\n"
        f"Resume: {lead.resume_filename}\n\n"
        f"Open it in the dashboard: {get_settings().public_base_url}/dashboard/leads/{lead.id}\n"
    )
    return subject, body
