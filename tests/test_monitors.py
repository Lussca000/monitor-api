from fastapi.testclient import TestClient
import httpx


def create_monitor(client: TestClient, name: str = "API principal") -> dict:
    response = client.post(
        "/monitors",
        json={"name": name, "url": "https://example.com/health"},
    )

    assert response.status_code == 201
    return response.json()


def test_create_monitor_uses_defaults(client: TestClient) -> None:
    monitor = create_monitor(client)

    assert monitor["id"] == 1
    assert monitor["name"] == "API principal"
    assert monitor["method"] == "GET"
    assert monitor["interval_seconds"] == 60
    assert monitor["timeout_seconds"] == 5
    assert monitor["is_active"] is True
    assert monitor["expected_status_code"] == 200


def test_create_monitor_rejects_invalid_payload(client: TestClient) -> None:
    response = client.post("/monitors", json={"name": "", "url": ""})

    assert response.status_code == 422


def test_list_monitors(client: TestClient) -> None:
    create_monitor(client, "API A")
    create_monitor(client, "API B")

    response = client.get("/monitors")

    assert response.status_code == 200
    assert [monitor["name"] for monitor in response.json()] == ["API A", "API B"]


def test_get_monitor(client: TestClient) -> None:
    monitor = create_monitor(client)

    response = client.get(f"/monitors/{monitor['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == monitor["id"]


def test_get_missing_monitor_returns_404(client: TestClient) -> None:
    response = client.get("/monitors/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_update_monitor_updates_only_sent_fields(client: TestClient) -> None:
    monitor = create_monitor(client)

    response = client.patch(
        f"/monitors/{monitor['id']}",
        json={"name": "API atualizada", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "API atualizada"
    assert response.json()["is_active"] is False
    assert response.json()["url"] == "https://example.com/health"


def test_update_missing_monitor_returns_404(client: TestClient) -> None:
    response = client.patch("/monitors/999", json={"name": "Nao existe"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_delete_monitor(client: TestClient) -> None:
    monitor = create_monitor(client)

    response = client.delete(f"/monitors/{monitor['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/monitors/{monitor['id']}").status_code == 404


def test_delete_missing_monitor_returns_404(client: TestClient) -> None:
    response = client.delete("/monitors/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_check_monitor_returns_success(client: TestClient, monkeypatch) -> None:
    monitor = create_monitor(client)

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(
        "app.services.checker.httpx.request", lambda **_: FakeResponse()
    )

    response = client.post(f"/monitors/{monitor['id']}/check")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["monitor_id"] == monitor["id"]
    assert response.json()["status_code"] == 200
    assert response.json()["success"] is True
    assert response.json()["error_type"] is None


def test_check_monitor_reports_unexpected_status(client: TestClient, monkeypatch) -> None:
    monitor = create_monitor(client)

    class FakeResponse:
        status_code = 503

    monkeypatch.setattr(
        "app.services.checker.httpx.request", lambda **_: FakeResponse()
    )

    response = client.post(f"/monitors/{monitor['id']}/check")

    assert response.status_code == 200
    assert response.json()["status_code"] == 503
    assert response.json()["success"] is False


def test_check_monitor_reports_timeout(client: TestClient, monkeypatch) -> None:
    monitor = create_monitor(client)

    def raise_timeout(**_) -> None:
        raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr("app.services.checker.httpx.request", raise_timeout)

    response = client.post(f"/monitors/{monitor['id']}/check")

    assert response.status_code == 200
    assert response.json()["status_code"] is None
    assert response.json()["success"] is False
    assert response.json()["error_type"] == "TIMEOUT"


def test_check_missing_monitor_returns_404(client: TestClient) -> None:
    response = client.post("/monitors/999/check")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_list_monitor_checks_returns_paginated_results(
    client: TestClient, monkeypatch
) -> None:
    monitor = create_monitor(client)

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(
        "app.services.checker.httpx.request", lambda **_: FakeResponse()
    )
    client.post(f"/monitors/{monitor['id']}/check")
    client.post(f"/monitors/{monitor['id']}/check")

    response = client.get(f"/monitors/{monitor['id']}/checks?page=1&page_size=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["total"] == 2
    assert [check["id"] for check in payload["items"]] == [2]

    second_page = client.get(f"/monitors/{monitor['id']}/checks?page=2&page_size=1")

    assert [check["id"] for check in second_page.json()["items"]] == [1]


def test_list_monitor_checks_validates_pagination(client: TestClient) -> None:
    monitor = create_monitor(client)

    response = client.get(f"/monitors/{monitor['id']}/checks?page=0")

    assert response.status_code == 422


def test_list_checks_for_missing_monitor_returns_404(client: TestClient) -> None:
    response = client.get("/monitors/999/checks")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_monitor_stats_for_monitor_without_checks(client: TestClient) -> None:
    monitor = create_monitor(client)

    response = client.get(f"/monitors/{monitor['id']}/stats")

    assert response.status_code == 200
    assert response.json() == {
        "monitor_id": monitor["id"],
        "total_checks": 0,
        "successful_checks": 0,
        "failed_checks": 0,
        "uptime_percentage": 0.0,
        "average_response_time_ms": None,
    }


def test_monitor_stats_calculates_uptime(client: TestClient, monkeypatch) -> None:
    monitor = create_monitor(client)
    status_codes = iter([200, 503, 200])

    class FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    monkeypatch.setattr(
        "app.services.checker.httpx.request",
        lambda **_: FakeResponse(next(status_codes)),
    )
    for _ in range(3):
        client.post(f"/monitors/{monitor['id']}/check")

    response = client.get(f"/monitors/{monitor['id']}/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["total_checks"] == 3
    assert stats["successful_checks"] == 2
    assert stats["failed_checks"] == 1
    assert stats["uptime_percentage"] == 66.67
    assert stats["average_response_time_ms"] >= 0


def test_stats_for_missing_monitor_returns_404(client: TestClient) -> None:
    response = client.get("/monitors/999/stats")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}
