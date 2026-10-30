from fastapi.testclient import TestClient


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
