from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    hf_api_key: str
    hf_url: str = "https://huggingface.co"
    hf_model_repo_id: str
    hf_model_filename: str = "model.onnx"
    app_password: str

    detection_threshold: float = 0.6


@lru_cache
def get_settings() -> Settings:
    return Settings()


class UISettings(BaseSettings):
    """Settings for the Streamlit frontend only - deliberately separate from Settings so the
    UI container never needs the backend's secrets just to start."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    backend_api_url: str = "http://127.0.0.1:8000"
    # Shared UI password gate. Required - enforced everywhere, including local dev.
    app_password: str


@lru_cache
def get_ui_settings() -> UISettings:
    return UISettings()


class TrainingSettings(BaseSettings):
    """Settings for local/notebook training runs - not needed by the deployed API or UI."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    data_root: Path = Path("../data")
    category: str = "screw"
    train_batch_size: int = 64
    eval_batch_size: int = 64
    num_neighbors: int = 6
    coreset_sampling_ratio: float = 0.1
    wandb_project: str = "screwit"
    wandb_run_name: str = "screw-patchcore"


@lru_cache
def get_training_settings() -> TrainingSettings:
    return TrainingSettings()
