from contextlib import asynccontextmanager

import onnxruntime as ort
from fastapi import FastAPI
from huggingface_hub import hf_hub_download
from prometheus_fastapi_instrumentator import Instrumentator

from src.shared.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ONNX model once at startup instead of per-request.
    settings = get_settings()
    model_path = hf_hub_download(
        repo_id=settings.hf_model_repo_id,
        filename=settings.hf_model_filename,
        token=settings.hf_api_key,
    )
    app.state.model = ort.InferenceSession(model_path)
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

Instrumentator().instrument(app).expose(app)
