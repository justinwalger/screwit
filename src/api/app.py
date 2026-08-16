from contextlib import asynccontextmanager

import onnxruntime as ort
from fastapi import FastAPI

from src.shared.config import get_settings

from .dependencies import download_model_from_hf


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ONNX model once at startup instead of per-request.
    settings = get_settings()
    model = download_model_from_hf(
        repo_id=settings.hf_model_repo_id,
        filename=settings.hf_model_filename,
        token=settings.hf_api_key,
    )
    app.state.model = ort.InferenceSession(model)
    yield


app = FastAPI(
    name="screwit",
    description="A simple API for detecting defects in screws using a machine learning model.",
    version="0.1.0",
    lifespan=lifespan,
)


from .routes import health, predict

app.include_router(health.router)
app.include_router(predict.router)
