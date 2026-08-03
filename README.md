# screwit

Anomaly detection for screws (and other MVTec-style categories): train a PatchCore
model with [anomalib](https://github.com/open-edge-platform/anomalib), export it to
ONNX, and serve it behind a FastAPI endpoint with a Streamlit UI on top — upload a
photo, get back a score and a defect heatmap.

![screwit demo: upload a screw photo, get an anomaly score, heatmap, and defect mask](docs/demo.gif)

## Layout

- `notebooks/` — training (anomalib, PatchCore), logged to W&B
- `src/api/` — FastAPI inference service, loads the ONNX model from HF Hub
- `src/ui/` — Streamlit dashboard: upload image, view score + mask
- `src/shared/` — config and request/response models shared by `api` and `ui`
- `docker/` — one Dockerfile per service (`api`, `streamlit`)
- `terraform/` — Cloud Run deployment
- `get_data.sh` — downloads MVTec AD categories into `data/`

## Quickstart

```bash
uv sync --all-groups
cp .env.example .env   # fill in HF_API_KEY etc.

./get_data.sh                                  # default: screw, tile, transistor
run notebooks/train.ipynb       # train + export a model

uv run uvicorn src.api.app:app --reload        # API on :8000
uv run streamlit run src/ui/app.py             # UI on :8501
```

## Roadmap

Training
- Configs, experiment tracking, hyperparameter tuning
- Try other models (PaDiM, ...) alongside PatchCore
- Retraining pipeline with human-in-the-loop

API / UI
- Auth
- Configurable model/category choice (currently hardcoded to PatchCore + screw)
- Blob storage for uploaded images

Ops
- Evals (AUROC, precision/recall, localization IoU)
- Tests
- Real deployment (Cloud Run via terraform)

Later / exploratory
- Edge export (run on small devices)
- VLM experiment
- Efficient AD models

Resources
- [MVTec AD dataset](https://www.mvtec.com/research-teaching/datasets/mvtec-ad)
- General anomaly detection methods (GAN-, VAE-based, ...)
