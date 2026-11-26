from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy.orm import Session

from app.db.models import User
from app.services.auth import hash_password


@pytest.fixture
def authenticated_user(db: Session) -> User:
    """Create and return an authenticated test user."""
    user = User(username="testuser", hashed_password=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(client: TestClient, authenticated_user: User) -> str:
    """Get a valid JWT token for the test user."""
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "password123"},
    )
    return response.json()["access_token"]


def get_auth_headers(token: str) -> dict:
    """Helper to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


def create_monitor(client: TestClient, auth_token: str, name: str = "API principal") -> dict:
    response = client.post(
        "/monitors",
        json={"name": name, "url": "https://example.com/health"},
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 201
    return response.json()


def test_create_monitor_requires_auth(client: TestClient) -> None:
    """Test that monitor creation requires authentication."""
    response = client.post(
        "/monitors",
        json={"name": "API", "url": "https://example.com"},
    )
    assert response.status_code == 403


def test_create_monitor_uses_defaults(client: TestClient, auth_token: str) -> None:
    monitor = create_monitor(client, auth_token)

    assert monitor["id"] == 1
    assert monitor["name"] == "API principal"
    assert monitor["method"] == "GET"
    assert monitor["interval_seconds"] == 60
    assert monitor["timeout_seconds"] == 5
    assert monitor["is_active"] is True
    assert monitor["expected_status_code"] == 200


def test_create_monitor_rejects_invalid_payload(client: TestClient, auth_token: str) -> None:
    response = client.post(
        "/monitors",
        json={"name": "", "url": ""},
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 422


def test_create_monitor_rejects_invalid_url(client: TestClient, auth_token: str) -> None:
    response = client.post(
        "/monitors",
        json={"name": "Invalid URL", "url": "ftp://example.com"},
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 422


def test_create_monitor_normalizes_http_method(client: TestClient, auth_token: str) -> None:
    response = client.post(
        "/monitors",
        json={"name": "Health API", "url": "https://example.com", "method": "head"},
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 201
    assert response.json()["method"] == "HEAD"


def test_create_monitor_rejects_invalid_http_method(client: TestClient, auth_token: str) -> None:
    response = client.post(
        "/monitors",
        json={"name": "Health API", "url": "https://example.com", "method": "CONNECT"},
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 422


def test_list_monitors(client: TestClient, auth_token: str) -> None:
    create_monitor(client, auth_token, "API A")
    create_monitor(client, auth_token, "API B")

    response = client.get("/monitors", headers=get_auth_headers(auth_token))

    assert response.status_code == 200
    assert [monitor["name"] for monitor in response.json()] == ["API A", "API B"]


def test_list_monitors_requires_auth(client: TestClient) -> None:
    response = client.get("/monitors")
    assert response.status_code == 403


def test_list_monitors_only_returns_user_monitors(
    client: TestClient, db: Session
) -> None:
    """Test that users only see their own monitors."""
    # Create two users
    user1 = User(username="user1", hashed_password=hash_password("pass1"))
    user2 = User(username="user2", hashed_password=hash_password("pass2"))
    db.add(user1)
    db.add(user2)
    db.commit()
    db.refresh(user1)
    db.refresh(user2)
    
    # Login both users and get tokens
    login1 = client.post(
        "/auth/login",
        json={"username": "user1", "password": "pass1"},
    )
    token1 = login1.json()["access_token"]
    
    login2 = client.post(
        "/auth/login",
        json={"username": "user2", "password": "pass2"},
    )
    token2 = login2.json()["access_token"]
    
    # Create monitors as user1
    create_monitor(client, token1, "User1 Monitor")
    
    # Create monitors as user2
    create_monitor(client, token2, "User2 Monitor")
    
    # List monitors as user1
    response = client.get("/monitors", headers=get_auth_headers(token1))
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "User1 Monitor"
    
    # List monitors as user2
    response = client.get("/monitors", headers=get_auth_headers(token2))
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "User2 Monitor"


def test_get_monitor(client: TestClient, auth_token: str) -> None:
    monitor = create_monitor(client, auth_token)

    response = client.get(f"/monitors/{monitor['id']}", headers=get_auth_headers(auth_token))

    assert response.status_code == 200
    assert response.json()["id"] == monitor["id"]


def test_get_missing_monitor_returns_404(client: TestClient, auth_token: str) -> None:
    response = client.get("/monitors/999", headers=get_auth_headers(auth_token))

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_get_other_user_monitor_returns_404(
    client: TestClient, db: Session
) -> None:
    """Test that users cannot access other users' monitors."""
    # Create two users
    user1 = User(username="user1", hashed_password=hash_password("pass1"))
    user2 = User(username="user2", hashed_password=hash_password("pass2"))
    db.add(user1)
    db.add(user2)
    db.commit()
    db.refresh(user1)
    db.refresh(user2)
    
    # Login user1 and create monitor
    login1 = client.post(
        "/auth/login",
        json={"username": "user1", "password": "pass1"},
    )
    token1 = login1.json()["access_token"]
    monitor = create_monitor(client, token1, "User1 Monitor")
    
    # Login user2 and try to access user1's monitor
    login2 = client.post(
        "/auth/login",
        json={"username": "user2", "password": "pass2"},
    )
    token2 = login2.json()["access_token"]
    
    response = client.get(f"/monitors/{monitor['id']}", headers=get_auth_headers(token2))
    assert response.status_code == 404


def test_update_monitor_updates_only_sent_fields(client: TestClient, auth_token: str) -> None:
    monitor = create_monitor(client, auth_token)

    response = client.patch(
        f"/monitors/{monitor['id']}",
        json={"name": "API atualizada", "is_active": False},
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "API atualizada"
    assert response.json()["is_active"] is False
    assert response.json()["url"] == "https://example.com/health"


def test_update_missing_monitor_returns_404(client: TestClient, auth_token: str) -> None:
    response = client.patch(
        "/monitors/999",
        json={"name": "Nao existe"},
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_update_monitor_validates_url_and_method(client: TestClient, auth_token: str) -> None:
    monitor = create_monitor(client, auth_token)

    invalid_url = client.patch(
        f"/monitors/{monitor['id']}",
        json={"url": "example.com"},
        headers=get_auth_headers(auth_token),
    )
    invalid_method = client.patch(
        f"/monitors/{monitor['id']}",
        json={"method": "TRACE"},
        headers=get_auth_headers(auth_token),
    )

    assert invalid_url.status_code == 422
    assert invalid_method.status_code == 422


def test_delete_monitor(client: TestClient, auth_token: str) -> None:
    monitor = create_monitor(client, auth_token)

    response = client.delete(
        f"/monitors/{monitor['id']}",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 204
    assert response.content == b""
    assert (
        client.get(f"/monitors/{monitor['id']}", headers=get_auth_headers(auth_token)).status_code
        == 404
    )


def test_delete_missing_monitor_returns_404(client: TestClient, auth_token: str) -> None:
    response = client.delete(
        "/monitors/999",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_check_monitor_returns_success(
    client: TestClient, auth_token: str, monkeypatch
) -> None:
    monitor = create_monitor(client, auth_token)

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(
        "app.services.checker.httpx.request", lambda **_: FakeResponse()
    )

    response = client.post(
        f"/monitors/{monitor['id']}/check",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["monitor_id"] == monitor["id"]
    assert response.json()["status_code"] == 200
    assert response.json()["success"] is True
    assert response.json()["error_type"] is None


def test_check_monitor_reports_unexpected_status(
    client: TestClient, auth_token: str, monkeypatch
) -> None:
    monitor = create_monitor(client, auth_token)

    class FakeResponse:
        status_code = 503

    monkeypatch.setattr(
        "app.services.checker.httpx.request", lambda **_: FakeResponse()
    )

    response = client.post(
        f"/monitors/{monitor['id']}/check",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 200
    assert response.json()["status_code"] == 503
    assert response.json()["success"] is False


def test_check_monitor_reports_timeout(
    client: TestClient, auth_token: str, monkeypatch
) -> None:
    monitor = create_monitor(client, auth_token)

    def raise_timeout(**_) -> None:
        raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr("app.services.checker.httpx.request", raise_timeout)

    response = client.post(
        f"/monitors/{monitor['id']}/check",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 200
    assert response.json()["status_code"] is None
    assert response.json()["success"] is False
    assert response.json()["error_type"] == "TIMEOUT"


def test_check_missing_monitor_returns_404(client: TestClient, auth_token: str) -> None:
    response = client.post(
        "/monitors/999/check",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_list_monitor_checks_returns_paginated_results(
    client: TestClient, auth_token: str, monkeypatch
) -> None:
    monitor = create_monitor(client, auth_token)

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(
        "app.services.checker.httpx.request", lambda **_: FakeResponse()
    )
    client.post(
        f"/monitors/{monitor['id']}/check",
        headers=get_auth_headers(auth_token),
    )
    client.post(
        f"/monitors/{monitor['id']}/check",
        headers=get_auth_headers(auth_token),
    )

    response = client.get(
        f"/monitors/{monitor['id']}/checks?page=1&page_size=1",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["total"] == 2
    assert [check["id"] for check in payload["items"]] == [2]

    second_page = client.get(
        f"/monitors/{monitor['id']}/checks?page=2&page_size=1",
        headers=get_auth_headers(auth_token),
    )

    assert [check["id"] for check in second_page.json()["items"]] == [1]


def test_list_monitor_checks_validates_pagination(client: TestClient, auth_token: str) -> None:
    monitor = create_monitor(client, auth_token)

    response = client.get(
        f"/monitors/{monitor['id']}/checks?page=0",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 422


def test_list_checks_for_missing_monitor_returns_404(client: TestClient, auth_token: str) -> None:
    response = client.get(
        "/monitors/999/checks",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_monitor_stats_for_monitor_without_checks(client: TestClient, auth_token: str) -> None:
    monitor = create_monitor(client, auth_token)

    response = client.get(
        f"/monitors/{monitor['id']}/stats",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "monitor_id": monitor["id"],
        "total_checks": 0,
        "successful_checks": 0,
        "failed_checks": 0,
        "uptime_percentage": 0.0,
        "average_response_time_ms": None,
    }


def test_monitor_stats_calculates_uptime(
    client: TestClient, auth_token: str, monkeypatch
) -> None:
    monitor = create_monitor(client, auth_token)
    status_codes = iter([200, 503, 200])

    class FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    monkeypatch.setattr(
        "app.services.checker.httpx.request",
        lambda **_: FakeResponse(next(status_codes)),
    )
    for _ in range(3):
        client.post(
            f"/monitors/{monitor['id']}/check",
            headers=get_auth_headers(auth_token),
        )

    response = client.get(
        f"/monitors/{monitor['id']}/stats",
        headers=get_auth_headers(auth_token),
    )

    assert response.status_code == 200
    stats = response.json()
    assert stats["total_checks"] == 3
    assert stats["successful_checks"] == 2
    assert stats["failed_checks"] == 1
    assert stats["uptime_percentage"] == 66.67
    assert stats["average_response_time_ms"] >= 0


def test_stats_for_missing_monitor_returns_404(client: TestClient, auth_token: str) -> None:
    response = client.get(
        "/monitors/999/stats",
        headers=get_auth_headers(auth_token),
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}
