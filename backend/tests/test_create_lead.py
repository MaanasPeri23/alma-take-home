import re

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.models.lead import Lead
from app.services.uploads import MAX_BYTES
from tests.test_uploads import DOC, DOCX, EXE, PDF, make_zip

pytestmark = pytest.mark.integration

FIELDS = {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"}


def submit(client, data=None, filename="resume.pdf", content=PDF, content_type="application/pdf"):
    return client.post(
        "/api/leads",
        data=FIELDS if data is None else data,
        files={"resume": (filename, content, content_type)},
    )


def error_locs(response):
    return [tuple(item["loc"]) for item in response.json()["detail"]]


def test_valid_pdf_creates_pending_lead_stores_file_and_sends_two_emails(
    client, db_session, storage, email_sender
):
    response = submit(client)

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "PENDING"
    assert body["resume_content_type"] == "application/pdf"

    lead = db_session.scalars(select(Lead)).one()
    assert re.fullmatch(r"resumes/[0-9a-f-]{36}", lead.resume_key)
    assert storage.objects[lead.resume_key][0] == PDF

    recipients = sorted(email.to for email in email_sender.sent)
    assert recipients == ["ada@example.com", "attorney@example.com"]


@pytest.mark.parametrize(("content", "filename"), [(DOC, "cv.doc"), (DOCX, "cv.docx")])
def test_word_documents_are_accepted(client, content, filename):
    assert submit(client, filename=filename, content=content).status_code == 201


@pytest.mark.parametrize(
    ("content", "filename"),
    [(EXE, "resume.pdf"), (make_zip("notes.txt"), "resume.docx"), (b"", "resume.pdf")],
    ids=["exe-renamed-pdf", "zip-renamed-docx", "empty"],
)
def test_bad_file_is_422_on_resume_and_nothing_is_saved(
    client, db_session, storage, email_sender, content, filename
):
    response = submit(client, filename=filename, content=content)

    assert response.status_code == 422
    assert error_locs(response) == [("body", "resume")]
    assert db_session.scalars(select(Lead)).all() == []
    assert storage.objects == {}
    assert email_sender.sent == []


def test_file_over_5_mb_is_rejected(client):
    response = submit(client, content=PDF + b"0" * MAX_BYTES)

    assert response.status_code == 422
    assert error_locs(response) == [("body", "resume")]
    assert "5 MB" in response.json()["detail"][0]["msg"]


@pytest.mark.parametrize(
    ("fields", "bad_field"),
    [
        ({"last_name": "Lovelace", "email": "ada@example.com"}, "first_name"),
        ({**FIELDS, "email": "not-an-email"}, "email"),
        ({**FIELDS, "first_name": "Ada\r\nBcc: someone@example.com"}, "first_name"),
        ({**FIELDS, "last_name": "   "}, "last_name"),
        ({**FIELDS, "first_name": "Ada\x00"}, "first_name"),
    ],
    ids=["missing", "bad-email", "newline-in-name", "blank-name", "nul-in-name"],
)
def test_bad_fields_are_422_naming_the_field(client, fields, bad_field):
    response = submit(client, data=fields)

    assert response.status_code == 422
    assert ("body", bad_field) in error_locs(response)


def test_email_failure_still_saves_the_lead(client, db_session, email_sender):
    email_sender.fail = True

    response = submit(client)

    assert response.status_code == 201
    assert len(db_session.scalars(select(Lead)).all()) == 1


def test_one_failed_email_does_not_stop_the_other_or_leak_pii(client, email_sender, caplog):
    email_sender.fail_for = {"ada@example.com"}

    assert submit(client).status_code == 201

    assert [email.to for email in email_sender.sent] == ["attorney@example.com"]
    assert "Failed to send" in caplog.text
    for pii in ("Ada", "Lovelace", "ada@example.com"):
        assert pii not in caplog.text


def test_file_of_exactly_5_mb_is_accepted(client):
    content = PDF + b"0" * (MAX_BYTES - len(PDF))

    assert submit(client, content=content).status_code == 201


def test_db_failure_deletes_the_uploaded_file(client, db_session, storage, monkeypatch):
    def broken_commit():
        raise OperationalError("INSERT", {}, Exception("database is down"))

    monkeypatch.setattr(db_session, "commit", broken_commit)

    with pytest.raises(OperationalError):
        submit(client)

    assert storage.objects == {}


def test_path_in_filename_is_stripped_and_never_used_as_the_key(client, db_session):
    response = submit(client, filename="../../etc/passwd.pdf")

    assert response.status_code == 201
    assert response.json()["resume_filename"] == "passwd.pdf"
    lead = db_session.scalars(select(Lead)).one()
    assert "passwd" not in lead.resume_key
