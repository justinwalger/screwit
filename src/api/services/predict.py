import base64
import io

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

from src.shared.config import get_settings
from src.shared.models import ImagePayload, PredictionResult


def _encode_png(array: np.ndarray, mode: str | None = None) -> str:
    buffer = io.BytesIO()
    Image.fromarray(array, mode=mode).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def _normalize(anomaly_map: np.ndarray) -> np.ndarray:
    """Min-max normalize a single anomaly map to [0, 1]."""
    normalized = anomaly_map - anomaly_map.min()
    return normalized / (normalized.max() + 1e-8)


def _make_heatmap(image_rgb: np.ndarray, normalized_map: np.ndarray) -> np.ndarray:
    """Overlay the normalized anomaly heatmap on the original image."""
    heatmap = cv2.applyColorMap((normalized_map * 255).astype(np.uint8), cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    return cv2.addWeighted(image_rgb, 0.5, heatmap, 0.5, 0)


def _make_circled_result(
    image_rgb: np.ndarray,
    normalized_map: np.ndarray,
    pred_label: bool,
    region_threshold: float = 0.8,
) -> np.ndarray:
    """Circle the most anomalous region(s) of the heatmap - but only if pred_label
    (itself pred_score >= settings.detection_threshold) says this image is actually
    defective. Otherwise there's nothing to flag, so the plain image is returned
    unmarked: the same detection_threshold decision now governs both the label
    and whether a circle gets drawn at all, instead of the circle appearing
    unconditionally regardless of the overall classification.

    Uses the continuous anomaly map (top 20% of its own min-max range) to find
    the region, not the model's binary pred_mask: that mask is thresholded more
    conservatively than the image-level classification, so it's frequently empty
    even on images correctly flagged as defective - which would silently draw no
    circle at all. Min-max normalization guarantees at least the peak pixel
    clears any region_threshold < 1.0, so a region is always found.
    """
    if not pred_label:
        return image_rgb

    result = image_rgb.copy()
    region = (normalized_map >= region_threshold).astype(np.uint8) * 255
    contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        (x, y), radius = cv2.minEnclosingCircle(contour)
        radius = max(radius, 6)  # keep small/single-pixel hotspots visible
        cv2.circle(result, (int(x), int(y)), int(radius), color=(255, 0, 0), thickness=2)
    return result


def run_prediction(payload: ImagePayload, model: ort.InferenceSession) -> PredictionResult:
    """Decode the uploaded image, run inference, and render the mask/heatmap/circled overlays.

    Raises ValueError, TypeError, or PIL.UnidentifiedImageError on malformed input -
    callers are expected to translate those into the appropriate HTTP response.
    """
    image_bytes = base64.b64decode(payload.image_b64, validate=True)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    array = np.array(image, dtype=np.float32) / 255.0  # HWC, [0, 1]
    array = array.transpose(2, 0, 1)[None, ...]  # -> NCHW, add batch dim

    pred_score, _pred_label, anomaly_map, pred_mask = model.run(None, {"input": array})

    score = pred_score.item()
    pred_label = score >= get_settings().detection_threshold

    mask = pred_mask[0, 0]
    normalized_map = _normalize(anomaly_map[0, 0])

    # anomaly_map/pred_mask come back at the model's working resolution, not the
    # original upload's - resize the image to match so the overlays line up.
    output_height, output_width = anomaly_map.shape[-2:]
    image_resized = np.array(image.resize((output_width, output_height)))

    return PredictionResult(
        filename=payload.filename,
        pred_score=score,
        pred_label=pred_label,
        pred_mask_png_b64=_encode_png((mask * 255).astype(np.uint8), mode="L"),
        heatmap_png_b64=_encode_png(_make_heatmap(image_resized, normalized_map)),
        result_png_b64=_encode_png(_make_circled_result(image_resized, normalized_map, pred_label)),
    )
