import io
import json
import urllib.request
import uuid

import pytest

from app.config import get_settings
from app.email import templates
from app.email.smtp import SmtpEmailSender
from app.models.lead import Lead
from app.storage.base import ObjectNotFound
from app.storage.s3 import S3Storage

MAILPIT_API = "http://mailpit:8025/api/v1"


def make_lead() -> Lead:
    return Lead(
        id=uuid.uuid4(),
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        resume_filename="ada.pdf",
    )


def test_prospect_email_is_addressed_by_first_name():
    subject, body = templates.prospect_confirmation(make_lead())

    assert "received" in subject
    assert body.startswith("Hi Ada,")


def test_attorney_email_has_contact_details_and_a_dashboard_link():
    lead = make_lead()
    subject, body = templates.attorney_notification(lead)

    assert subject == "New lead: Ada Lovelace"
    assert "ada@example.com" in body
    assert f"/dashboard/leads/{lead.id}" in body


@pytest.mark.integration
def test_s3_storage_round_trip_against_minio():
    storage = S3Storage(get_settings())
    storage.ensure_bucket()
    storage.ensure_bucket()  # idempotent
    key = f"test/{uuid.uuid4()}"

    storage.put(key, io.BytesIO(b"%PDF-1.7 hello"), "application/pdf")
    assert b"".join(storage.open(key)) == b"%PDF-1.7 hello"

    storage.delete(key)
    # Raises on the call itself, before any iteration, so B4 can 404 before streaming.
    with pytest.raises(ObjectNotFound):
        storage.open(key)


@pytest.mark.integration
def test_smtp_sender_delivers_to_mailpit():
    to = f"{uuid.uuid4()}@example.com"

    SmtpEmailSender(get_settings()).send(to, "Integration test", "hello from pytest")

    with urllib.request.urlopen(f"{MAILPIT_API}/search?query=to:{to}") as response:
        messages = json.load(response)["messages"]
    assert [m["Subject"] for m in messages] == ["Integration test"]
