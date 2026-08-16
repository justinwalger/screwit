import base64
import io
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from src.api.dependencies import get_model, verify_api_password
from src.api.routes import predict as predict_route


class _FakeModel:
    """Stands in for the ONNX InferenceSession - fixed-shape outputs, no real model file needed."""

    def run(self, output_names, inputs):
        _, _, height, width = inputs["input"].shape
        pred_score = np.array([0.9], dtype=np.float32)
        pred_label = np.array([True])
        anomaly_map = np.full((1, 1, height, width), 0.7, dtype=np.float32)
        pred_mask = np.ones((1, 1, height, width), dtype=np.float32)
        return pred_score, pred_label, anomaly_map, pred_mask


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        "src.api.services.predict.get_settings",
        lambda: SimpleNamespace(detection_threshold=0.6),
    )

    app = FastAPI()
    app.include_router(predict_route.router)
    app.dependency_overrides[verify_api_password] = lambda: None
    app.dependency_overrides[get_model] = lambda: _FakeModel()
    return TestClient(app)


def _sample_image_b64() -> str:
    image = Image.new("RGB", (32, 32), color=(200, 50, 50))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_predict_returns_expected_fields(client: TestClient) -> None:
    response = client.post(
        "/predict/predict",
        json={"filename": "test.png", "image_b64": _sample_image_b64()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "test.png"
    assert body["pred_score"] == pytest.approx(0.9)
    assert body["pred_label"] is True
    assert body["result_png_b64"]
    assert body["heatmap_png_b64"]
    assert body["pred_mask_png_b64"]


def test_predict_rejects_invalid_base64(client: TestClient) -> None:
    response = client.post(
        "/predict/predict",
        json={"filename": "bad.png", "image_b64": "not-base64!!"},
    )

    assert response.status_code == 400
