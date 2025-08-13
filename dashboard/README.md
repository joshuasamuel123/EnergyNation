# EnergyNation — MPI Dashboard (Dash)

[![Open in Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Open%20in%20Spaces-black)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard-v4)
[![Sync to HF Space](https://github.com/joshuasamuel123/EnergyNation/actions/workflows/hf-space-sync.yml/badge.svg)](https://github.com/joshuasamuel123/EnergyNation/actions/workflows/hf-space-sync.yml)

A lightweight **Dash** app for exploring the **Major Projects Inventory (MPI)** dataset with interactive KPIs, probability/priority charts, rankings, and a map view. Designed as a minimal, review-friendly interface that can be deployed on **Hugging Face Spaces** and kept in sync from **GitHub**.

---

## Live demo
- **Hugging Face Space:** https://huggingface.co/spaces/EnergyNation/MPI-Dashboard

---

## What’s inside
- **Interactive tabs**: Probability vs Priority, Sector & Cleantech, Cost & Timeline, Map, and Stage Flow.
- **KPIs & rankings**: probability of construction (≤ 3 years), priority (time-to-event urgency), and a normalized power ranking.
- **Single-file dataset**: reads a bundled `*.xlsx` by default (configurable via `DATAFILE`).
- **Docker-first deploy**: reliable builds on Spaces.

---

## Repository structure
```
.
├── app.py                   # Dash app (exposes `server = app.server`)
├── requirements.txt         # Python deps (Dash, Plotly, Pandas, etc.)
├── Dockerfile               # Runs app with gunicorn on port 7860
├── space.yml                # Space metadata (sdk: docker)
├── mpi_2024_scored.xlsx     # Sample dataset used by the app
└── .github/
    └── workflows/
        └── hf-space-sync.yml  # (added in setup) GitHub→HF auto-deploy
```

---

## Quick start

### 1) Run locally (no Docker)
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
# Serve the Dash app via Gunicorn on port 7860
gunicorn app:server -b 0.0.0.0:7860 --timeout 120
```
Then open http://localhost:7860

> The app reads an Excel file placed next to `app.py`. To point at a different file, set `DATAFILE`:
```bash
export DATAFILE=my_other_file.xlsx  # macOS/Linux
# set DATAFILE=my_other_file.xlsx   # Windows PowerShell: $env:DATAFILE="my_other_file.xlsx"
```

### 2) Run locally (Docker)
```bash
docker build -t mpi-dash .
docker run -p 7860:7860 -e DATAFILE=mpi_2024_scored.xlsx mpi-dash
```

### 3) Deploy to Hugging Face Spaces (auto from GitHub)
1. **Create a write token** on Hugging Face: *Settings → Access Tokens → New token (Write)*.
2. **Add secret to GitHub** repo: *Settings → Secrets and variables → Actions → New repository secret*:
   - **Name**: `HF_TOKEN`
   - **Value**: the HF write token
3. **Create the workflow** file in your repo at `.github/workflows/hf-space-sync.yml`:
```yaml
name: Sync to Hugging Face Space
on:
  push:
    branches: [main]    # change to 'master' if your default branch is master
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true
      - name: Push to Space
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git push https://EnergyNation:$HF_TOKEN@huggingface.co/spaces/EnergyNation/MPI-Dashboard-v4 HEAD:main
```
4. **Commit any change** to `main` (e.g., edit README). Watch **Actions** run. Your Space rebuilds and goes live.

> Prefer web UI? You can create this workflow completely from GitHub’s web interface (no terminal required).

---

## Configuration
- **Port**: Spaces expect `7860` (the Dockerfile exposes this port).
- **Dataset path**: set **`DATAFILE`** in the Space (Settings → Variables) or as an environment variable locally. Default preference includes `mpi_2024_scored.xlsx`.
- **File sizes**: if you later add large assets (>10 MB), consider Git LFS in your repo.

---

## Data expectations (minimum columns)
The app expects the following columns in the Excel file:

- `province`, `sector`, `group`, `cleantech`
- `company`, `project`
- `start_year`, `end_year`, `start_status`, `end_status`, `end_success`, `current_survival`
- `project_cost` (CAD$), `cost_mm` (optional convenience field)
- `blended_prob`, `priority_index`, `power_ranking`
- (Optionally used for display/hover): `prob2dp`, `priority_index_2dp`, `power_ranking_2dp`, `bubble_size`, `label`, `score01`
- (Optional for map): `latitude_1`, `longitude_1`

> Column names must match exactly (case-sensitive). Extra columns are ignored.

---

## Troubleshooting
- **“Failed to read Excel”**: Ensure the `.xlsx` is in the repo root (next to `app.py`) or set `DATAFILE` to the correct filename.
- **Build succeeds but blank page**: Check Space **Settings → Builds → Logs**. Common culprits are missing columns or typos in column names.
- **Port/Bind errors**: The Dockerfile already binds `0.0.0.0:7860`. If you change the command, keep the same port.
- **Workflow didn’t run**: Confirm your default branch is `main` (or update the YAML), and that `HF_TOKEN` exists with **Write** scope.

---

## Roadmap
- Add contextual features (policy & local signals) to evolve from static monitoring to decision support.
- Expand data dictionary and validation checks on load.
- Optional: public Colab for the risk engines (separate notebook).

---

## License
MIT — see `LICENSE` (add one if missing).

---

## Acknowledgements
Thanks to reviewers and collaborators providing feedback on the MVP dashboard.
