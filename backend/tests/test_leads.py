import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.lead import Lead, LeadState, LeadStateEvent
from app.services.lead_service import ALLOWED
from scripts.seed_attorneys import seed
from tests.test_uploads import PDF

pytestmark = pytest.mark.integration

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def attorney(db_session):
    return seed(db_session, "attorney@example.com", "password", name="Jane Counsel")


@pytest.fixture
def signed_in(client, attorney):
    response = client.post(
        "/api/auth/login", json={"email": "attorney@example.com", "password": "password"}
    )
    assert response.status_code == 200
    return client


def add_lead(db_session, storage, *, minutes=0, state=LeadState.PENDING, name="Ada", body=PDF):
    """A lead created `minutes` after BASE_TIME, with its resume in the fake storage."""
    key = f"resumes/{uuid.uuid4()}"
    storage.put(key, io.BytesIO(body), "application/pdf")
    lead = Lead(
        first_name=name,
        last_name="Lovelace",
        email=f"{name.lower()}@example.com",
        resume_key=key,
        resume_filename="Ada Lovelace – CV.pdf",
        resume_content_type="application/pdf",
        resume_size_bytes=len(body),
        state=state,
        created_at=BASE_TIME + timedelta(minutes=minutes),
    )
    db_session.add(lead)
    db_session.commit()
    return lead


# --- list -----------------------------------------------------------------------------------


def test_list_is_newest_first_with_total(signed_in, db_session, storage):
    for minutes, name in [(0, "Oldest"), (2, "Newest"), (1, "Middle")]:
        add_lead(db_session, storage, minutes=minutes, name=name)

    body = signed_in.get("/api/leads").json()

    assert [lead["first_name"] for lead in body["items"]] == ["Newest", "Middle", "Oldest"]
    assert body["total"] == 3
    assert (body["limit"], body["offset"]) == (20, 0)


def test_list_filters_by_state(signed_in, db_session, storage):
    add_lead(db_session, storage, name="Waiting")
    add_lead(db_session, storage, name="Called", state=LeadState.REACHED_OUT)

    body = signed_in.get("/api/leads", params={"state": "REACHED_OUT"}).json()

    assert [lead["first_name"] for lead in body["items"]] == ["Called"]
    assert body["total"] == 1


def test_list_pages_with_limit_and_offset(signed_in, db_session, storage):
    for minutes in range(5):
        add_lead(db_session, storage, minutes=minutes, name=f"L{minutes}")

    page = signed_in.get("/api/leads", params={"limit": 2, "offset": 2}).json()
    past_end = signed_in.get("/api/leads", params={"limit": 2, "offset": 10}).json()

    assert [lead["first_name"] for lead in page["items"]] == ["L2", "L1"]
    assert page["total"] == 5
    assert past_end["items"] == []
    assert past_end["total"] == 5


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"state": "BOGUS"}],
    ids=["limit-0", "limit-101", "offset-negative", "unknown-state"],
)
def test_list_rejects_out_of_range_params(signed_in, params):
    assert signed_in.get("/api/leads", params=params).status_code == 422


# --- detail ---------------------------------------------------------------------------------


def test_detail_has_every_submitted_field_and_empty_history(signed_in, db_session, storage):
    lead = add_lead(db_session, storage)

    body = signed_in.get(f"/api/leads/{lead.id}").json()

    assert body["first_name"] == "Ada"
    assert body["email"] == "ada@example.com"
    assert body["resume_filename"] == "Ada Lovelace – CV.pdf"
    assert body["state"] == "PENDING"
    assert body["history"] == []


def test_detail_unknown_lead_is_404(signed_in):
    response = signed_in.get(f"/api/leads/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead not found"}


def test_detail_malformed_id_is_422(signed_in):
    assert signed_in.get("/api/leads/not-a-uuid").status_code == 422


# --- resume download ------------------------------------------------------------------------


def test_download_streams_the_exact_file_with_safe_headers(signed_in, db_session, storage):
    lead = add_lead(db_session, storage)

    response = signed_in.get(f"/api/leads/{lead.id}/resume")

    assert response.status_code == 200
    assert response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-length"] == str(len(PDF))
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in response.headers["cache-control"]
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    # The en dash survives via RFC 5987 encoding.
    assert "filename*=UTF-8''Ada%20Lovelace%20%E2%80%93%20CV.pdf" in disposition


def test_download_unknown_lead_is_404(signed_in):
    assert signed_in.get(f"/api/leads/{uuid.uuid4()}/resume").status_code == 404


def test_download_with_file_missing_from_storage_is_404_not_a_broken_stream(
    signed_in, db_session, storage
):
    lead = add_lead(db_session, storage)
    storage.delete(lead.resume_key)

    response = signed_in.get(f"/api/leads/{lead.id}/resume")

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead not found"}


# --- state transitions ----------------------------------------------------------------------


def mark(client, lead_id, state):
    return client.patch(f"/api/leads/{lead_id}", json={"state": state})


def events_for(db_session, lead_id):
    db_session.expire_all()
    return db_session.scalars(
        select(LeadStateEvent)
        .where(LeadStateEvent.lead_id == lead_id)
        .order_by(LeadStateEvent.created_at)
    ).all()


def test_marking_reached_out_records_who_and_when(signed_in, db_session, storage, attorney):
    lead = add_lead(db_session, storage)

    response = mark(signed_in, lead.id, "REACHED_OUT")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "REACHED_OUT"
    [entry] = body["history"]
    assert (entry["from_state"], entry["to_state"]) == ("PENDING", "REACHED_OUT")
    assert entry["actor_name"] == "Jane Counsel"

    [event] = events_for(db_session, lead.id)
    assert event.actor_id == attorney.id
    assert event.created_at is not None


def test_marking_twice_is_409_and_writes_no_second_event(signed_in, db_session, storage):
    lead = add_lead(db_session, storage)
    mark(signed_in, lead.id, "REACHED_OUT")

    response = mark(signed_in, lead.id, "REACHED_OUT")

    assert response.status_code == 409
    assert response.json() == {"detail": "Can't move a lead from REACHED_OUT to REACHED_OUT"}
    assert len(events_for(db_session, lead.id)) == 1


def test_undo_moves_back_to_pending_and_keeps_full_history(signed_in, db_session, storage):
    lead = add_lead(db_session, storage)
    mark(signed_in, lead.id, "REACHED_OUT")

    response = mark(signed_in, lead.id, "PENDING")

    assert response.status_code == 200
    assert response.json()["state"] == "PENDING"
    transitions = [(e["from_state"], e["to_state"]) for e in response.json()["history"]]
    assert transitions == [("PENDING", "REACHED_OUT"), ("REACHED_OUT", "PENDING")]


def test_marking_unknown_lead_is_404(signed_in):
    assert mark(signed_in, uuid.uuid4(), "REACHED_OUT").status_code == 404


def test_marking_with_unknown_state_is_422(signed_in, db_session, storage):
    lead = add_lead(db_session, storage)

    assert mark(signed_in, lead.id, "REJECTED").status_code == 422


@pytest.mark.parametrize("current", list(LeadState))
@pytest.mark.parametrize("requested", list(LeadState))
def test_every_transition_follows_the_allowed_map(
    signed_in, db_session, storage, current, requested
):
    lead = add_lead(db_session, storage, state=current)

    response = mark(signed_in, lead.id, requested)

    allowed = requested in ALLOWED[current]
    assert response.status_code == (200 if allowed else 409)
    # An allowed change moves the state and writes exactly one history row; a refused one does
    # neither.
    assert len(events_for(db_session, lead.id)) == (1 if allowed else 0)
    assert db_session.get(Lead, lead.id).state == (requested if allowed else current)


def test_content_disposition_strips_control_characters():
    from app.routers.leads import content_disposition

    header = content_disposition("evil\r\nSet-Cookie: x=1.pdf")

    assert "\r" not in header and "\n" not in header
