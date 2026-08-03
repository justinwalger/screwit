from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router


def test_health_returns_ok() -> None:
    """Mounts just the health router on a throwaway app - no model/HF/auth
    dependencies needed, so this stays fast and reliable in CI."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
