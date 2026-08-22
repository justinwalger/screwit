# screwit

Anomaly detection for screws: train a PatchCore model with
[anomalib](https://github.com/open-edge-platform/anomalib), export it to ONNX, and
serve it behind a FastAPI endpoint with a Gradio UI on top — upload a photo, get
back a score and a defect heatmap.

![screwit demo: upload a screw photo, get an anomaly score, heatmap, and defect mask](docs/demo.gif)

## Architecture

```mermaid
flowchart LR
    User(["User"]) --> UI["Gradio UI\n(src/ui)"]
    UI -- "POST /predict\n(X-API-Password)" --> API["FastAPI\n(src/api)"]
    API -- "ONNX Runtime\ninference" --> Model[("PatchCore model\n(.onnx, from HF Hub)")]
    API -- score + heatmap + mask --> UI
```

The API loads the PatchCore ONNX model from Hugging Face Hub once at startup
(`src/api/app.py`'s lifespan) and keeps it in memory; the UI is a thin client that
just forwards uploads to the API and renders the response.

## Layout

- `notebooks/` — training (anomalib, PatchCore), logged to W&B
- `src/api/` — FastAPI inference service, loads the ONNX model from HF Hub
- `src/ui/` — Gradio dashboard: upload image, view score + mask
- `src/shared/` — config and request/response models shared by `api` and `ui`
- `docker/` — one Dockerfile per service (`api`, `gradio`)
- `terraform/` — Cloud Run deployment
- `kubernetes/screwit/` — Helm chart, alternative deployment for local `minikube` use
- `get_data.sh` — downloads MVTec AD categories into `data/`

## Quickstart

```bash
uv sync --all-groups
cp .env.example .env   # fill in HF_API_KEY etc.

./get_data.sh                                  # default: screw
run notebooks/train.ipynb       # train + export a model

uv run uvicorn src.api.app:app --reload        # API on :8000
uv run python src/ui/app.py                    # UI on :7860
```

## Eval

Single training run per model (see `notebooks/train.ipynb`, hyperparameters in
`configs/<model_name>.yaml`), tracked in W&B:

| Model       | Epochs | Image AUROC | Image F1 | Pixel AUROC | Pixel F1 |
|-------------|-------:|-------------:|---------:|-------------:|---------:|
| PatchCore   |      5 |       0.9874 |   0.9639 |       0.8521 |   0.6181 |
| PaDiM       |      1 |       0.8437 |   0.8421 |       0.9716 |   0.1637 |
| EfficientAd |     15 |       0.8373 |   0.8489 |       0.9665 |   0.3912 |

PatchCore leads on image-level detection by a wide margin; PaDiM/EfficientAd
localize pixels better (higher pixel AUROC) but lag well behind on pixel F1.
Not hyperparameter-tuned — see `configs/` to adjust and re-run.

## Deployment

GCP Cloud Run, via Terraform (`terraform/`), auto-applied by
`.github/workflows/deploy.yml` on every push to `main`: build+push the
backend/frontend images to Artifact Registry, then `terraform apply` the
`fastapi-backend` and `gradio-frontend` Cloud Run services.

Terraform is split into two separate configs with separate state, on purpose:

- **`terraform/`** — the Cloud Run services. Meant to run in CI on every push
  to `main`, authenticated as the `github-actions-deployer` service account.
- **`terraform/bootstrap/`** — the Artifact Registry repo, the
  `github-actions-deployer` service account itself, and its IAM grants.
  Applied manually, rarely, by a human with privileged GCP access, never by
  CI: `github-actions-deployer` is deliberately scoped to Cloud Run deploy
  rights only, so a leaked `GCP_CREDENTIALS` secret can't grant itself
  broader project access. If those resources lived in the CI-managed config,
  every CI-driven `terraform apply` would try to reconcile IAM/registry
  settings and fail with a permissions error.

One-time manual setup (not automated, and shouldn't be — see
`terraform/bootstrap/main.tf`'s comments for why the CI identity deliberately
can't do this itself):

1. Create a GCS bucket for Terraform state (Terraform/GCS can't create its
   own backend bucket):
   ```bash
   gcloud storage buckets create gs://<bucket-name> --location=europe-west1
   ```
2. Apply the bootstrap config manually, with your own privileged credentials
   (`gcloud auth application-default login`) — uses its own state prefix
   (`screwit-bootstrap`, vs. `screwit` for the root config, same bucket):
   ```bash
   cd terraform/bootstrap
   terraform init -backend-config="bucket=<bucket-name>" -backend-config="prefix=screwit-bootstrap"
   terraform apply -var project_id=<gcp-project-id> -var state_bucket_name=<bucket-name>
   ```
   Creates the Artifact Registry repo, the `github-actions-deployer` service
   account, and grants it `roles/storage.objectAdmin` on the state bucket
   (needed for the deploy workflow's own `terraform init`/`apply` against
   that bucket).
3. Get the service account's JSON key:
   ```bash
   terraform output -raw ci_deployer_key | base64 -d
   ```
4. Set these as GitHub Actions secrets: `GCP_PROJECT_ID`, `GCP_CREDENTIALS`
   (the key from step 3), `TF_STATE_BUCKET` (the bucket from step 1),
   `HF_API_KEY`, `HF_MODEL_REPO_ID`, `APP_PASSWORD`.

Without step 4's `TF_STATE_BUCKET` secret, `terraform init` in the deploy
workflow fails immediately (empty backend config).

### Local Kubernetes (minikube)

`kubernetes/screwit/` is a Helm chart — a separate, manual, local-only
alternative to the Cloud Run path above, for running both services against
`minikube` instead of GCP. Not part of `deploy.yml`.

```bash
minikube start                                          # one-time per cluster
brew install helm                                       # one-time

docker build -t screwit-api:latest -f docker/Dockerfile.api .
docker build -t screwit-gradio:latest -f docker/Dockerfile.gradio .
minikube image load screwit-api:latest
minikube image load screwit-gradio:latest


kubectl create secret generic screwit-secrets --from-env-file=.env \
  --dry-run=client -o yaml | kubectl apply -f -

helm install screwit kubernetes/screwit                 # first install
helm upgrade screwit kubernetes/screwit --reuse-values   # subsequent changes
```

Non-secret config (`HF_MODEL_REPO_ID`, `BACKEND_API_URL`) lives in
`values.yaml`'s `configMap` block and is applied as a normal committed
manifest — only `screwit-secrets` needs the imperative step above.

Images are loaded straight into the cluster, not pulled from a registry —
both Deployments use `imagePullPolicy: IfNotPresent` for that reason
(`Always` would try Docker Hub and fail, since these images don't exist
anywhere but the local node). **Caveat that actually bit us once**:
`IfNotPresent` only checks whether a tag already exists on the node, not
whether its content changed — reloading a rebuilt image under the same
`:latest` tag can silently keep serving the old code, since neither
`minikube image load` nor a `kubectl rollout restart` change the image
*reference string* the Deployment holds. The reliable rebuild loop uses a
fresh tag every time:

```bash
TAG=$(date +%s)
docker build -t screwit-api:$TAG -f docker/Dockerfile.api .
docker save screwit-api:$TAG -o /tmp/screwit-api.tar
minikube image load /tmp/screwit-api.tar
helm upgrade screwit kubernetes/screwit --reuse-values --set api.image.tag=$TAG
```

Access the Gradio UI (NodePort, so it needs a tunnel under the Docker driver):

```bash
minikube service gradio-service --url
```

### Monitoring (Prometheus + Grafana)

Local-only, like the rest of this section — no Cloud Run equivalent exists.
`src/api/app.py` exposes `/metrics` via `prometheus-fastapi-instrumentator`,
unauthenticated (same reasoning as `/health` — Prometheus doesn't send the
shared `X-API-Password` header).

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.service.type=NodePort
```

`kubernetes/screwit/templates/servicemonitor.yaml` tells the stack's
Prometheus to scrape `screwit-api-service` at `/metrics` every 15s. It only
gets discovered because it carries the label `release: monitoring`, matching
the stack's own Helm release name — the installed Prometheus's
`serviceMonitorSelector` requires that label, so an unlabeled ServiceMonitor
is silently ignored, not an error.

```bash
minikube service monitoring-grafana -n monitoring --url   # Grafana UI

kubectl get secret --namespace monitoring \
  -l app.kubernetes.io/component=admin-secret \
  -o jsonpath="{.data.admin-password}" | base64 -d          # admin password
```

## Roadmap

Done
- Evals (image/pixel AUROC, F1) across PatchCore/PaDiM/EfficientAd — see Eval above
- Real deployment (Cloud Run via Terraform, `deploy.yml`)
- Observability (Prometheus + Grafana, local Kubernetes only — see Monitoring above)

Training
- Configs, experiment tracking, hyperparameter tuning
- Retraining pipeline with human-in-the-loop

API / UI
- Configurable model/category choice (currently hardcoded to PatchCore + screw)
- Blob storage for uploaded images

Ops
- Tests (currently just health + predict smoke tests)

Later / exploratory
- Edge export (run on small devices)
- VLM experiment

Resources
- [MVTec AD dataset](https://www.mvtec.com/research-teaching/datasets/mvtec-ad)
- General anomaly detection methods (GAN-, VAE-based, ...)
