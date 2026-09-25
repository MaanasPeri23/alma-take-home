import os

# Settings has no defaults for secrets. Inside the api container they come from .env; for host-side
# unit tests (`make test-fast`) fill in throwaway values before anything imports app.config.
for key, value in {
    "JWT_SECRET": "test-secret-that-is-at-least-32-bytes-long",
    "S3_ACCESS_KEY": "test",
    "S3_SECRET_KEY": "test",
}.items():
    os.environ.setdefault(key, value)

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from tests.fakes import InMemoryStorage, RecordingEmailSender  # noqa: E402

TEST_DB_NAME = "leads_test"


@pytest.fixture(scope="session")
def test_engine():
    """A separate database for tests, so running them never touches the data you demo with."""
    import app.models  # noqa: F401  (registers tables)
    from app.config import get_settings
    from app.db import Base

    url = make_url(get_settings().database_url)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    engine = create_engine(url.set(database=TEST_DB_NAME), hide_parameters=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Iterator[Session]:
    with test_engine.begin() as conn:
        conn.execute(text("TRUNCATE leads, lead_state_events, attorneys CASCADE"))
    with sessionmaker(bind=test_engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def email_sender() -> RecordingEmailSender:
    return RecordingEmailSender()


@pytest.fixture
def client(db_session, storage, email_sender) -> Iterator[TestClient]:
    from app.db import get_db
    from app.deps import get_email_sender, get_storage
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
