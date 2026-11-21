"""Shared fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from evidence_trail.api.app import create_app
from evidence_trail.config import Settings
from evidence_trail.container import Container, build_container


@pytest.fixture()
def container() -> Container:
    """A fully wired, in-memory system without an LLM."""
    return build_container(Settings(db_path=":memory:"))


@pytest.fixture()
def project_id(container: Container) -> str:
    return container.projects.create("Shop", "Acme").project_id


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(Settings(db_path=":memory:")))


def sign_up(
    client: TestClient, email: str = "sara@example.com", name: str = "Sara"
) -> dict[str, str]:
    """Register a user and return the Authorization header for them."""
    resp = client.post(
        "/auth/signup", json={"name": name, "email": email, "password": "correct-horse"}
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.fixture()
def auth(client: TestClient) -> dict[str, str]:
    """Headers for a freshly registered user."""
    return sign_up(client)
