"""Streamlit entry point for the application.

design is inspired by https://github.com/streamlit/demo-ai-ai/blob/main/streamlit_app.py. thanks!
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from src.ui.constants import PAGE_ICON, PAGE_TITLE
from src.ui.views.main import create_main_page

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")

create_main_page()
