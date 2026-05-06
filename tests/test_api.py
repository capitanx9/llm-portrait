from django.test import Client


def test_api_health_returns_ok(client: Client) -> None:
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_schema_is_served(client: Client) -> None:
    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert "openapi" in response.content.decode().lower()


def test_api_docs_is_served(client: Client) -> None:
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()
