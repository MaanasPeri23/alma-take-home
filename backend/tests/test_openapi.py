from app.main import app

# The API contract from docs/DESIGN.md. The frontend client is generated from this spec,
# so a route missing here is a route the frontend can't call.
EXPECTED_ROUTES = {
    ("post", "/api/leads"),
    ("get", "/api/leads"),
    ("get", "/api/leads/{lead_id}"),
    ("patch", "/api/leads/{lead_id}"),
    ("get", "/api/leads/{lead_id}/resume"),
    ("post", "/api/auth/login"),
    ("post", "/api/auth/logout"),
    ("get", "/api/auth/me"),
    ("get", "/health"),
}


def test_every_designed_route_is_in_the_spec():
    spec = app.openapi()
    actual = {(method, path) for path, ops in spec["paths"].items() for method in ops}

    assert actual == EXPECTED_ROUTES


def test_no_route_ends_with_a_trailing_slash():
    # A trailing slash triggers FastAPI's redirect to the internal api:8000 host.
    assert not [path for path in app.openapi()["paths"] if path.endswith("/")]


def test_lead_submission_is_multipart_with_a_file():
    body = app.openapi()["paths"]["/api/leads"]["post"]["requestBody"]

    assert "multipart/form-data" in body["content"]


PUBLIC_ROUTES = {
    ("post", "/api/leads"),
    ("post", "/api/auth/login"),
    ("post", "/api/auth/logout"),  # always clears the cookie; see routers/auth.py
    ("get", "/health"),
}


def test_every_attorney_route_declares_401():
    # The frontend's generated types only know about errors the spec declares.
    spec = app.openapi()
    missing = [
        (method, path)
        for path, ops in spec["paths"].items()
        for method, op in ops.items()
        if (method, path) not in PUBLIC_ROUTES and "401" not in op["responses"]
    ]

    assert missing == []


def test_state_change_declares_409():
    assert "409" in app.openapi()["paths"]["/api/leads/{lead_id}"]["patch"]["responses"]
