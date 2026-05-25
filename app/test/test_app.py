import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index_returns_200(client):
    res = client.get("/")
    assert res.status_code == 200


def test_index_has_version(client):
    data = client.get("/").get_json()
    assert "version" in data
    assert "environment" in data


def test_health_returns_healthy(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"


def test_ready_returns_ready(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ready"


def test_version_endpoint(client):
    data = client.get("/version").get_json()
    assert "version" in data
    assert "environment" in data


def test_simulate_error_returns_500(client):
    res = client.get("/simulate/error")
    assert res.status_code == 500
