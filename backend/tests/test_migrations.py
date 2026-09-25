import pytest
from sqlalchemy import inspect

from app.db import engine

pytestmark = pytest.mark.integration


def test_migrations_create_every_table():
    tables = set(inspect(engine).get_table_names())

    assert {"leads", "attorneys", "lead_state_events", "alembic_version"} <= tables


def test_dashboard_and_history_indexes_exist():
    inspector = inspect(engine)
    lead_indexes = {ix["name"] for ix in inspector.get_indexes("leads")}
    event_indexes = {ix["name"] for ix in inspector.get_indexes("lead_state_events")}

    assert "ix_leads_state_created_id" in lead_indexes
    assert "ix_lead_state_events_lead_created" in event_indexes


def test_attorney_email_is_unique():
    uniques = inspect(engine).get_unique_constraints("attorneys")

    assert any(u["column_names"] == ["email"] for u in uniques)
