import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.main import app
from app.models.attorney import Attorney
from app.services.auth_service import create_session_token
from scripts.seed_attorneys import seed

pytestmark = pytest.mark.integration

EMAIL = "attorney@example.com"
PASSWORD = "correct horse battery staple"
PUBLIC_ROUTES = {
    ("post", "/api/leads"),
    ("post", "/api/auth/login"),
    ("post", "/api/auth/logout"),  # always clears the cookie; see routers/auth.py
    ("get", "/health"),
}


@pytest.fixture
def attorney(db_session) -> Attorney:
    return seed(db_session, EMAIL, PASSWORD)


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def attorney_routes():
    """Every non-public route, read from the spec so a new route can't be missed."""
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            if (method, path) not in PUBLIC_ROUTES:
                yield method, path.replace("{lead_id}", str(uuid.uuid4()))


def test_login_sets_an_httponly_lax_session_cookie(client, attorney):
    response = login(client)

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("session=")
    assert "HttpOnly" in cookie
    assert re.search(r"SameSite=lax", cookie, re.IGNORECASE)
    assert "Path=/" in cookie
    assert f"Max-Age={get_settings().session_ttl_minutes * 60}" in cookie
    assert client.get("/api/auth/me").json()["email"] == EMAIL


@pytest.mark.parametrize(
    ("email", "password"),
    [(EMAIL, "wrong password"), ("nobody@example.com", PASSWORD)],
    ids=["wrong-password", "unknown-email"],
)
def test_bad_credentials_get_the_same_401_and_no_cookie(client, attorney, email, password):
    response = login(client, email, password)

    assert response.status_code == 401
    assert response.json() == {"detail": "Wrong email or password"}
    assert "set-cookie" not in response.headers


def test_email_is_case_insensitive(client, attorney):
    assert login(client, email="Attorney@Example.COM").status_code == 200


@pytest.mark.parametrize(("method", "path"), list(attorney_routes()))
def test_every_attorney_route_is_401_without_a_session(client, method, path):
    response = client.request(method, path, json={"state": "REACHED_OUT"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Not signed in"}


def test_signed_in_attorney_gets_past_auth_on_lead_routes(client, attorney):
    login(client)

    assert client.get("/api/leads").status_code == 200


def forged_tokens(attorney_id: uuid.UUID) -> dict[str, str]:
    """Tokens for a real attorney, so a 401 proves the check itself, not a missing account."""
    sub = str(attorney_id)
    now = datetime.now(UTC)
    good = create_session_token(attorney_id)
    return {
        "garbage": "not-a-jwt",
        "bad-signature": good[:-4] + ("AAAA" if not good.endswith("AAAA") else "BBBB"),
        "other-secret": jwt.encode(
            {"sub": sub, "iat": now, "exp": now + timedelta(hours=1)},
            "a-completely-different-secret-32-bytes!!",
            algorithm="HS256",
        ),
        "alg-none": jwt.encode(
            {"sub": sub, "iat": now, "exp": now + timedelta(hours=1)}, None, algorithm="none"
        ),
        "no-exp": jwt.encode({"sub": sub, "iat": now}, get_settings().jwt_secret, "HS256"),
        "expired": create_session_token(attorney_id, now=now - timedelta(days=2)),
    }


@pytest.mark.parametrize(
    "kind", ["garbage", "bad-signature", "other-secret", "alg-none", "no-exp", "expired"]
)
def test_invalid_tokens_for_a_real_attorney_are_rejected(client, attorney, kind):
    client.cookies.set("session", create_session_token(attorney.id))
    assert client.get("/api/auth/me").status_code == 200  # the valid token works...

    client.cookies.set("session", forged_tokens(attorney.id)[kind])
    assert client.get("/api/auth/me").status_code == 401  # ...and the forged one doesn't


def test_overlong_password_is_a_401_not_a_500(client, attorney):
    assert login(client, password="x" * 80).status_code == 401
    assert login(client, email="nobody@example.com", password="x" * 80).status_code == 401


def test_token_for_a_deleted_attorney_is_rejected(client, db_session, attorney):
    login(client)
    db_session.delete(attorney)
    db_session.commit()

    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_the_cookie(client, attorney):
    login(client)

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert (
        'session=""' in response.headers["set-cookie"]
        or "Max-Age=0" in response.headers["set-cookie"]
    )
    assert client.get("/api/auth/me").status_code == 401


def test_password_is_stored_as_a_bcrypt_hash(attorney):
    assert PASSWORD not in attorney.password_hash
    assert attorney.password_hash.startswith("$2")


def test_seed_is_idempotent_and_resets_the_password(client, db_session):
    seed(db_session, EMAIL, "first password")
    seed(db_session, EMAIL, PASSWORD)

    assert len(db_session.scalars(select(Attorney)).all()) == 1
    assert login(client).status_code == 200


@pytest.mark.parametrize("cookie", [None, "expired", "garbage"])
def test_logout_always_clears_the_cookie_even_without_a_valid_session(client, attorney, cookie):
    if cookie == "expired":
        client.cookies.set("session", forged_tokens(attorney.id)["expired"])
    elif cookie == "garbage":
        client.cookies.set("session", "not-a-jwt")

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
