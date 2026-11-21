from fastapi.testclient import TestClient


def _project(client: TestClient, auth: dict[str, str]) -> str:
    resp = client.post("/projects", json={"name": "Shop", "client": "Acme"}, headers=auth)
    assert resp.status_code == 201
    return resp.json()["project_id"]


def test_auth_required(client: TestClient) -> None:
    assert client.get("/projects").status_code == 401
    assert client.get("/projects", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    assert client.get("/projects", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/health").status_code == 200


def test_end_to_end_over_http(client: TestClient, auth: dict[str, str]) -> None:
    pid = _project(client, auth)
    ing = client.post(
        f"/projects/{pid}/ingest/email",
        json={"content": "Subject: Login\n\nWe need a login page. Make it premium."},
        headers=auth,
    )
    assert ing.status_code == 200
    created = ing.json()["created_requirements"]
    assert len(created) == 2  # "login page" and "make it premium" are separate requirements

    details = [client.get(f"/requirements/{rid}", headers=auth).json() for rid in created]
    assert any(f["issue_type"] == "vague_term" for d in details for f in d["findings"])
    assert all(d["sources"] and d["sources"][0]["channel"] == "email" for d in details)
    req_id = next(d["requirement"]["requirement_id"] for d in details if not d["findings"])

    # Not yet approved -> draft is a conflict (409), not a server error.
    assert client.get(f"/requirements/{req_id}/confirmation-draft", headers=auth).status_code == 409

    rev = client.post(f"/requirements/{req_id}/review", json={"decision": "approve"}, headers=auth)
    assert rev.json()["status"] == "approved"
    assert (
        "CONFIRM"
        in client.get(f"/requirements/{req_id}/confirmation-draft", headers=auth).json()["draft"]
    )

    done = client.post(
        f"/requirements/{req_id}/confirmation", json={"response": "confirmed"}, headers=auth
    )
    assert done.json()["status"] == "confirmed"

    trail = client.get(f"/requirements/{req_id}/trail", headers=auth).json()
    assert trail["complete"] is True

    listing = client.get(f"/projects/{pid}/requirements?status=confirmed&q=login", headers=auth)
    assert len(listing.json()) == 1
    assert (
        client.get(f"/projects/{pid}/dashboard", headers=auth).json()["by_status"]["confirmed"] == 1
    )


def test_whatsapp_webhook_route(client: TestClient, auth: dict[str, str]) -> None:
    pid = _project(client, auth)
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "1",
                                    "type": "text",
                                    "text": {"body": "We need an order tracking page."},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    resp = client.post(f"/projects/{pid}/webhooks/whatsapp", json=payload, headers=auth)
    assert resp.status_code == 200 and len(resp.json()["created_requirements"]) == 1


def test_error_mapping(client: TestClient, auth: dict[str, str]) -> None:
    pid = _project(client, auth)
    assert client.get("/requirements/nope", headers=auth).status_code == 404
    assert (
        client.post(f"/projects/{pid}/ingest/fax", json={"content": "x"}, headers=auth).status_code
        == 404
    )
    assert (
        client.post("/projects/nope/ingest/email", json={"content": "x"}, headers=auth).status_code
        == 404
    )
    bad = client.post(f"/projects/{pid}/webhooks/whatsapp", json={"entry": []}, headers=auth)
    assert bad.status_code == 422


def test_list_includes_open_findings_count(client: TestClient, auth: dict[str, str]) -> None:
    pid = _project(client, auth)
    client.post(
        f"/projects/{pid}/ingest/document",
        json={"content": "Make the homepage premium."},
        headers=auth,
    )
    [item] = client.get(f"/projects/{pid}/requirements", headers=auth).json()
    assert item["open_findings"] >= 1 and item["title"]


def test_cors_allows_frontend_origin_only(client: TestClient) -> None:
    ok = client.options(
        "/projects",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-api-key",
        },
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        "/projects",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers
