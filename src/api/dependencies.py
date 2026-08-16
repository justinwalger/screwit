import onnxruntime as ort
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from src.shared.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Password")


def download_model_from_hf(repo_id: str, filename: str, token: str | None = None) -> str:
    """
    Download the model from Hugging Face Hub and return the local path.
    """
    from huggingface_hub import hf_hub_download

    model_path = hf_hub_download(repo_id=repo_id, filename=filename, token=token)
    return model_path


def verify_api_password(api_password: str = Depends(_api_key_header)) -> None:
    """Route dependency gating access behind the shared APP_PASSWORD secret."""
    if api_password != get_settings().app_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API password")


def get_model(request: Request) -> ort.InferenceSession:
    """Route dependency exposing the model loaded once at startup (see app.py's lifespan)."""
    return request.app.state.model
