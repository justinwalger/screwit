"""Gradio entry point: upload a screw photo, get back an anomaly score + defect mask."""

import base64
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import gradio as gr
import httpx
# hotfix: should not be importing uvicorn here, but gradio's FastAPI mount requires it to be installed
import uvicorn
from fastapi import FastAPI
from PIL import Image

from src.shared.config import get_ui_settings
from src.ui.backend_connector import BackendConnector
from src.ui.constants import ABOUT_TEXT, PAGE_ICON, PAGE_TITLE

_connector = BackendConnector()
_settings = get_ui_settings()


def _decode(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64)))


def predict(image: Image.Image | None) -> tuple[str, float, Image.Image, Image.Image, Image.Image]:
    if image is None:
        raise gr.Error("Upload a photo first.")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    try:
        # The UI's own password gate (below) already authenticated this session,
        # so the shared secret from config - not anything typed at request time -
        # is what's forwarded to the API.
        result = _connector.predict(buffer.getvalue(), "upload.png", _settings.app_password)
    except httpx.HTTPError as exc:
        raise gr.Error(f"Prediction failed: {exc}") from exc

    label = "🔴 Defect detected" if result.pred_label else "🟢 Looks good"
    return (
        label,
        round(result.pred_score, 2),
        _decode(result.result_png_b64),
        _decode(result.heatmap_png_b64),
        _decode(result.pred_mask_png_b64),
    )


demo = gr.Interface(
    fn=predict,
    inputs=gr.Image(type="pil", label="Screw photo"),
    outputs=[
        gr.Label(label="Result"),
        gr.Number(label="Anomaly score"),
        gr.Image(label="Detected defect"),
        gr.Image(label="Anomaly heatmap"),
        gr.Image(label="Predicted defect mask"),
    ],
    title=f"{PAGE_ICON} {PAGE_TITLE}",
    description=ABOUT_TEXT,
    flagging_mode="never",
)


def main() -> None:
    port = int(os.environ.get("PORT", "7860"))


    app = FastAPI()
    gr.mount_gradio_app(
        app,
        demo,
        path="/",
        server_name="0.0.0.0",
        server_port=port,
        auth=lambda _username, password: password == _settings.app_password,
        auth_message="Enter the shared password (username is ignored, type anything).",

        theme=gr.themes.Base(primary_hue="indigo"),
    )
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
