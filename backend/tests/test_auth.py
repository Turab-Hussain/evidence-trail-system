"""Accounts: signup, login, tokens, project ownership, dashboard, legacy migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from evidence_trail.api.app import create_app
from evidence_trail.config import Settings
from evidence_trail.domain.exceptions import AuthenticationError, RateLimitError
from evidence_trail.repositories.sqlite_repository import SQLiteRepository
from evidence_trail.services.auth_service import LoginThrottle
from evidence_trail.services.security import PasswordHasher, TokenService
from tests.conftest import sign_up


def test_password_hash_is_salted_and_verifies() -> None:
    hasher = PasswordHasher()
    first, second = hasher.hash("secret-pass"), hasher.hash("secret-pass")
    assert first != second and "secret-pass" not in first
    assert hasher.verify("secret-pass", first)
    assert not hasher.verify("other", first)
    assert not hasher.verify("secret-pass", "garbage")


def test_token_roundtrip_expiry_and_tampering() -> None:
    tokens = TokenService("k" * 32, ttl_seconds=60)
    token = tokens.issue("usr-1", now=1000)
    assert tokens.verify(token, now=1030) == "usr-1"
    with pytest.raises(AuthenticationError, match="expired"):
        tokens.verify(token, now=1061)
    body, sig = token.split(".")
    with pytest.raises(AuthenticationError):
        tokens.verify(f"{body}.{sig[:-2]}xx", now=1030)
    with pytest.raises(AuthenticationError):
        TokenService("different-secret", 60).verify(token, now=1030)
    with pytest.raises(AuthenticationError):
        tokens.verify("not-a-token", now=1030)


def test_login_throttle_blocks_after_repeated_failures() -> None:
    throttle = LoginThrottle(max_failures=2, window_seconds=10)
    throttle.record_failure("a", now=0)
    throttle.record_failure("a", now=1)
    with pytest.raises(RateLimitError):
        throttle.check("a", now=2)
    throttle.check("a", now=20)  # window passed
    throttle.check("b", now=2)  # other keys unaffected


def test_signup_login_me(client: TestClient) -> None:
    signup = client.post(
        "/auth/signup",
        json={"name": " Sara ", "email": "Sara@Example.com", "password": "longenough"},
    )
    assert signup.status_code == 201
    user = signup.json()["user"]
    assert user["email"] == "sara@example.com" and user["name"] == "Sara"
    assert "password" not in str(signup.json()).lower().replace("password-less", "")

    login = client.post("/auth/login", json={"email": "SARA@example.com", "password": "longenough"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    me = client.get("/auth/me", headers=headers).json()
    assert me["user_id"] == user["user_id"] and me["last_login_at"]


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"name": "A", "email": "not-an-email", "password": "longenough"}, 422),
        ({"name": "A", "email": "a@b.co", "password": "short"}, 422),
        ({"name": "  ", "email": "a@b.co", "password": "longenough"}, 422),
    ],
)
def test_signup_validation(client: TestClient, payload: dict[str, str], status: int) -> None:
    assert client.post("/auth/signup", json=payload).status_code == status


def test_duplicate_email_and_wrong_password(client: TestClient) -> None:
    sign_up(client, "a@example.com")
    dup = client.post(
        "/auth/signup", json={"name": "B", "email": "A@example.com", "password": "longenough"}
    )
    assert dup.status_code == 409
    bad = client.post("/auth/login", json={"email": "a@example.com", "password": "wrong-pass"})
    unknown = client.post("/auth/login", json={"email": "x@example.com", "password": "wrong-pass"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()  # does not reveal which emails exist


def test_login_is_rate_limited(client: TestClient) -> None:
    sign_up(client, "a@example.com")
    codes = [
        client.post("/auth/login", json={"email": "a@example.com", "password": "bad-guess"})
        for _ in range(6)
    ]
    assert [r.status_code for r in codes] == [401] * 5 + [429]


def test_users_cannot_see_each_others_data(client: TestClient) -> None:
    alice = sign_up(client, "alice@example.com", "Alice")
    bob = sign_up(client, "bob@example.com", "Bob")
    pid = client.post("/projects", json={"name": "P", "client": "C"}, headers=alice).json()[
        "project_id"
    ]
    ing = client.post(
        f"/projects/{pid}/ingest/email", json={"content": "We need a login page."}, headers=alice
    ).json()
    req_id = ing["created_requirements"][0]

    assert client.get("/projects", headers=bob).json() == []
    assert len(client.get("/projects", headers=alice).json()) == 1
    for method, url, body in [
        ("get", f"/projects/{pid}/requirements", None),
        ("get", f"/projects/{pid}/dashboard", None),
        ("post", f"/projects/{pid}/ingest/email", {"content": "We need x."}),
        ("get", f"/requirements/{req_id}", None),
        ("get", f"/requirements/{req_id}/trail", None),
        ("post", f"/requirements/{req_id}/review", {"decision": "approve"}),
    ]:
        resp = getattr(client, method)(url, headers=bob, **({"json": body} if body else {}))
        assert resp.status_code == 404, url
    # Alice's requirement was not changed by Bob's attempted review.
    assert (
        client.get(f"/requirements/{req_id}", headers=alice).json()["requirement"]["status"]
        == "pending_approval"
    )


def test_review_actor_is_the_signed_in_user(client: TestClient) -> None:
    headers = sign_up(client, "pm@example.com", "Priya")
    pid = client.post("/projects", json={"name": "P", "client": "C"}, headers=headers).json()[
        "project_id"
    ]
    req_id = client.post(
        f"/projects/{pid}/ingest/email", json={"content": "We need a login page."}, headers=headers
    ).json()["created_requirements"][0]
    client.post(
        f"/requirements/{req_id}/review",
        json={"decision": "approve", "actor": "someone-else"},
        headers=headers,
    )
    trail = client.get(f"/requirements/{req_id}/trail", headers=headers).json()
    assert any(step["actor"] == "Priya" for step in trail["entries"])
    assert all(step["actor"] != "someone-else" for step in trail["entries"])


def test_account_dashboard_totals(client: TestClient) -> None:
    headers = sign_up(client, "pm@example.com", "Priya")
    empty = client.get("/me/dashboard", headers=headers).json()
    assert empty["user"]["name"] == "Priya" and empty["dashboard"]["projects"] == 0

    pid = client.post("/projects", json={"name": "Shop", "client": "Acme"}, headers=headers).json()[
        "project_id"
    ]
    client.post(
        f"/projects/{pid}/ingest/email",
        json={"content": "We need a login page. Make it premium."},
        headers=headers,
    )
    dash = client.get("/me/dashboard", headers=headers).json()["dashboard"]
    assert dash["projects"] == 1 and dash["requirements"] == 2 and dash["sources"] == 1
    assert dash["awaiting_review"] == 2 and dash["by_channel"]["email"] == 1
    assert dash["open_findings"] >= 1
    summary = dash["project_summaries"][0]
    assert summary["project"]["name"] == "Shop" and summary["requirements"] == 2
    activity = dash["recent_activity"]
    assert activity and activity[0]["project_name"] == "Shop"
    steps = {item["step"] for item in activity}
    assert {"ingested", "requirement_created"} <= steps
    assert not steps & {"extracted", "ambiguity_checked"}  # internal steps stay out of the feed


def test_first_signup_adopts_legacy_projects_and_old_db_is_migrated(tmp_path: Path) -> None:
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE projects (project_id TEXT PRIMARY KEY, name TEXT NOT NULL,
                               client TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active');
        INSERT INTO projects VALUES ('proj-old', 'Legacy', 'Acme', 'active');
        """
    )
    conn.commit()
    conn.close()

    repo = SQLiteRepository(str(db))
    assert repo.get_project("proj-old").owner_id is None
    client = TestClient(create_app(Settings(db_path=str(db))))
    headers = sign_up(client, "first@example.com", "First")
    assert [p["project_id"] for p in client.get("/projects", headers=headers).json()] == [
        "proj-old"
    ]
    second = sign_up(client, "second@example.com", "Second")
    assert client.get("/projects", headers=second).json() == []


def test_login_survives_restart(tmp_path: Path) -> None:
    """The signing key is stored in the database, so a token stays valid after a restart."""
    db = str(tmp_path / "app.db")
    headers = sign_up(TestClient(create_app(Settings(db_path=db))))
    restarted = TestClient(create_app(Settings(db_path=db)))
    assert restarted.get("/auth/me", headers=headers).status_code == 200
