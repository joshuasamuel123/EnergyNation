---
title: Canada Major Projects Probability & Ranking Dashboard
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

A lightweight **Dash** app for exploring the **Major Projects Inventory (MPI)** dataset with interactive KPIs, probability/priority charts, rankings, and map views.  
Designed as a minimal, review-friendly interface that can be deployed on **Hugging Face Spaces** and kept in sync from **GitHub**.

---

## Features

- **Probability vs Priority scatter** with quadrant guides.  
- **Top-N charts**: Power Ranking, Probability, Priority Index.  
- **Facts & Figures** tab with 2×4 grid:  
  - Projects by Sector/Province (Count or Cost)  
  - Total Project Value (Sector, Province)  
  - Cleantech / Ownership donuts (Count or Cost)  
  - Vintage trends (Count or Cost)  
- **Map** of projects sized by cost.  
- **Stage Flow** Sankey (Start → End status).  
- **Count vs Cost** toggle drives Rows 1, 3, 4. Row 2 is always cost.  
- **Download filtered CSV**.

---

## Data expectations

The app auto-loads an Excel file (`.xlsx`) from:  
1. `DATAFILE` env var (if set), else  
2. `mpi_2024_scored.xlsx`, else  
3. `sample_mpi.xlsx`, else  
4. any `.xlsx` in the app folder.

**Minimum columns required:**  
`province`, `sector`, `group`, `cleantech`, `company`, `project`, `start_year`, `end_year`,  
`project_cost`, `blended_prob`, `priority_index`, `power_ranking`, `start_status`, `end_status`.  

**Additional columns used:**  
- `urgency_scale_(0-1)` → remapped to `priority_index` (Priority Index now reflects 0–1 urgency).  
- `company_type` (Ownership donut).  
- `latitude_1`, `longitude_1` (Map).  

Full schema and methodology: see the [📄 Model Card](MPI_Dashboard_Model_Card.md).

---

## Quick start

### Run locally
```bash
pip install -r requirements.txt
python app.py
# open http://localhost:7860
```

To specify a different dataset:
```bash
export DATAFILE=my_other_file.xlsx   # macOS/Linux
# or
$env:DATAFILE="my_other_file.xlsx"  # Windows PowerShell
```

### Run via Docker
```bash
docker build -t mpi-dash .
docker run -p 7860:7860 -e DATAFILE=mpi_2024_scored.xlsx mpi-dash
```

### Deploy on Hugging Face Spaces
- Uses `sdk: docker` (see front matter above).  
- Repo auto-syncs subfolder `dashboard/` → Space via GitHub Action.  
- Set `HF_TOKEN` secret in GitHub with **Write** scope.

---

## License
MIT — see `LICENSE`.

---

## Documentation
- 📄 [Model Card](MPI_Dashboard_Model_Card.md) — full details on data, processing, and ethical considerations.

---

## Changelog
- **v1.1 (2025-08-19):** Priority wiring to `urgency_scale_(0-1)`; new Facts & Figures grid; Count vs Cost toggle active.  
- **v1.0:** Initial release.
