import onnxruntime as ort
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from PIL import UnidentifiedImageError

from src.api.dependencies import get_model, verify_api_password
from src.api.services.prediction import run_prediction
from src.shared.models import ImagePayload, PredictionResult

router = APIRouter(
    prefix="/predict",
    tags=["predict"],
    dependencies=[Depends(verify_api_password)],
    responses={404: {"description": "Not found"}},
)


@router.post("/predict", response_model=PredictionResult, response_class=JSONResponse)
async def predict_image(
    payload: ImagePayload, model: ort.InferenceSession = Depends(get_model)
) -> PredictionResult:
    try:
        return run_prediction(payload, model)
    except (ValueError, TypeError, UnidentifiedImageError) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc
