import base64

import httpx

from src.shared.config import get_ui_settings
from src.shared.models import PredictionResult


class BackendConnector:
    def __init__(self, api_url: str | None = None, timeout: float = 30.0) -> None:
        self.api_url = api_url or get_ui_settings().backend_api_url
        self.timeout = timeout

    def predict(self, image_bytes: bytes, filename: str, password: str) -> PredictionResult:
        """Send an image to the /predict/predict endpoint and return the parsed result."""
        response = httpx.post(
            f"{self.api_url}/predict/predict",
            json={"filename": filename, "image_b64": base64.b64encode(image_bytes).decode()},
            headers={"X-API-Password": password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return PredictionResult.model_validate(response.json())
