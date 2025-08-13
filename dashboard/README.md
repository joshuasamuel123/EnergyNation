---
title: MPI Dashboard
emoji: 📊
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# EnergyNation — MPI Dashboard (Dash)

[![Open in Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Open%20in%20Spaces-black)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)
[![Sync to HF Space](https://github.com/joshuasamuel123/EnergyNation/actions/workflows/hf-space-sync-subdir.yml/badge.svg)](https://github.com/joshuasamuel123/EnergyNation/actions/workflows/hf-space-sync-subdir.yml)

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

## Folder layout (this repo)
```
EnergyNation/
├── dashboard/               # <— this folder is pushed to the Space
│   ├── app.py               # Dash app (exposes `server = app.server`)
│   ├── requirements.txt     # Python deps
│   ├── Dockerfile           # Runs app with gunicorn on port 7860
│   ├── space.yml            # (optional) Space metadata
│   ├── mpi_2024_scored.xlsx # Sample dataset used by the app
│   └── README.md            # (this file)
└── .github/
    └── workflows/
        └── hf-space-sync-subdir.yml  # GitHub→HF auto-deploy (subfolder)
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
# Windows PowerShell:
# $env:DATAFILE="my_other_file.xlsx"
```

### 2) Run locally (Docker)
```bash
docker build -t mpi-dash .
docker run -p 7860:7860 -e DATAFILE=mpi_2024_scored.xlsx mpi-dash
```

### 3) Deploy to Hugging Face Spaces (auto from GitHub, subfolder)
- This repository uses a workflow that **packages `dashboard/`** and **pushes it to the Space**.
- Ensure you added a Hugging Face **Write** token as a repo secret named `HF_TOKEN`.
- Workflow file: `.github/workflows/hf-space-sync-subdir.yml`

Trigger a deploy by committing any change under `dashboard/` (or run the workflow manually in the **Actions** tab).

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
- **Configuration error (Missing configuration in README)**: The Space requires a README with a YAML front matter block (the one at the top of this file) that sets `sdk: docker`. Keep this README at the **root of the Space repo**. In our setup, `dashboard/README.md` becomes the Space’s root README when deployed.
- **“Failed to read Excel”**: Ensure the `.xlsx` is next to `app.py` or set `DATAFILE` to the correct filename.
- **Build succeeds but blank page**: Check Space **Settings → Builds → Logs**. Common culprits are missing columns or typos in column names.
- **Workflow didn’t run**: Confirm your default branch is `main` (or update the YAML), and that `HF_TOKEN` exists with **Write** scope.

---

## License
MIT — see `LICENSE` (add one if missing).
