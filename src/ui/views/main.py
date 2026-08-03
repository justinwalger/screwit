"""Main page: upload a screw photo, get back an anomaly score + defect mask."""

import base64

import httpx
import streamlit as st

from src.shared.config import get_ui_settings
from src.shared.models import PredictionResult
from src.ui.backend_connector import BackendConnector
from src.ui.constants import ABOUT_TEXT, PAGE_ICON, PAGE_TITLE

_connector = BackendConnector()
_IMAGE_WIDTH = 260


def _prompt_for_password() -> bool:
    """Ask for the shared password once per session. Returns True once past the gate."""
    settings = get_ui_settings()
    if st.session_state.get("password"):
        return True

    st.title(f"{PAGE_ICON} {PAGE_TITLE}", anchor=False)
    password = st.text_input("Password", type="password", key="password_input")
    if st.button("Enter") and password:
        if password == settings.app_password:
            st.session_state.password = password
            st.rerun()
        else:
            st.error("Wrong password.")
    return False


def _render_status(result: PredictionResult) -> None:
    if result.pred_label:
        st.error(f"Defect detected — anomaly score **{result.pred_score:.2f}**", icon="🔴")
    else:
        st.success(f"Looks good — anomaly score **{result.pred_score:.2f}**", icon="🟢")


def _render_images(uploaded_file, result: PredictionResult) -> None:
    """One row, fixed-size thumbnails - nothing stretched, nothing below the fold."""
    images = [
        (uploaded_file, uploaded_file.name),
        (base64.b64decode(result.result_png_b64), "Detected defect"),
        (base64.b64decode(result.heatmap_png_b64), "Anomaly heatmap"),
        (base64.b64decode(result.pred_mask_png_b64), "Predicted defect mask"),
    ]
    for col, (image, caption) in zip(st.columns(4), images, strict=True):
        with col:
            st.image(image, caption=caption, width=_IMAGE_WIDTH)


def create_main_page() -> None:
    """Create main page."""
    if not _prompt_for_password():
        return

    st.title(f"{PAGE_ICON} {PAGE_TITLE}", anchor=False)
    st.caption(ABOUT_TEXT)

    uploaded_file = st.file_uploader(
        "Screw photo",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
    )
    if uploaded_file is None:
        st.info("Upload a photo to see the anomaly mask here.")
        return

    with st.spinner("Running inference..."):
        try:
            result = _connector.predict(
                uploaded_file.getvalue(),
                uploaded_file.name,
                st.session_state.password,
            )
        except httpx.HTTPError as exc:
            st.error(f"Prediction failed: {exc}")
            return

    _render_status(result)
    _render_images(uploaded_file, result)
