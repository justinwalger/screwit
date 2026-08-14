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
    # Name of the model that was trained (e.g. "patchcore", "padim") - drives the
    # uploaded/downloaded filename below, so training and serving can't drift
    # out of sync by editing one but not the other.
    model_name: str = "padim"
    app_password: str

    detection_threshold: float = 0.6

    @property
    def hf_model_filename(self) -> str:
        return f"{self.model_name}_onnx"


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
    """Settings for local/notebook training runs - not needed by the deployed API or UI.

    Model-specific hyperparameters (batch sizes, epochs, ...) live in
    configs/<model_name>.yaml instead, since they differ per model type -
    see notebooks/train.ipynb.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    data_root: Path = Path("../data")
    category: str = "screw"
    wandb_project: str = "screwit"


@lru_cache
def get_training_settings() -> TrainingSettings:
    return TrainingSettings()
