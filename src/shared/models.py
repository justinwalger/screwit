from pydantic import BaseModel


class ImagePayload(BaseModel):
    """Request body for /predict/predict."""

    filename: str
    image_b64: str


class PredictionResult(BaseModel):
    """Response body for /predict."""

    filename: str
    pred_score: float
    pred_label: bool
    pred_mask_png_b64: str
    heatmap_png_b64: str
    result_png_b64: str
