from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_segments_have_demo_fallback() -> None:
    response = client.get("/api/segments")
    assert response.status_code == 200
    assert len(response.json()["segments"]) >= 1


def test_campaign_generation_without_external_services() -> None:
    response = client.post(
        "/api/campaigns",
        json={"product": "A transparent savings offer", "segment_ids": [1], "persona_count": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["campaigns"]) == 1
    assert len(body["campaigns"][0]["personas"]) == 3


def test_lex_lambda_local_fallback() -> None:
    from lambda_function_import import invoke_handler

    response = invoke_handler()
    assert response["sessionState"]["intent"]["state"] == "Fulfilled"

