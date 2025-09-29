# MPI Risk Engine — v03a (Expanded, Audit-Ready)

## Overview
This script (`mpi_risk_engine_v03_expanded.py`) is a patched version of the MPI risk engine.  
It scores projects in the **Major Projects Inventory (MPI)** with blended probabilities by combining a **Bayes prior leg** and a **Cox survival leg**.  
Key improvements over earlier versions:

- ✅ Province–sector shrinkage knob (`PROVSEC_ALPHA`) to prevent Bayes swamping.  
- ✅ Audit-friendly Cox coefficients (includes `Greenfield/FOAK`, `cost_percentile`).  
- ✅ Supports cleantech naming variants (`cleantech_flag` vs `cleantech_Yes`).  
- ✅ Exposes blend weight (`BLEND_BAYES_W`) as a configurable knob.  

---

## Inputs

- **Coefficient files**
  - `bayes_lr_regenerated_coefficients_expanded.csv`
  - `cox_refit_coefficients_timesplit_expanded.csv`
- **MPI input file**
  - `mpi_2024_input.xlsx` (must include project metadata and costs)

---

## Outputs

- `mpi_2024_scored.csv`  
- `mpi_2024_scored.xlsx`  

Both outputs contain per-project scores including:
- `p_bayes` — probability from Bayes log-odds with optional shrinkage  
- `risk_score` — Cox proportional hazard risk  
- `p_cox` — probability from Cox survival function  
- `blended_prob` — weighted average of Bayes and Cox legs  
- `priority_index` — blended probability scaled by time remaining  
- `urgency_scale_(0-1)` — normalized urgency index  
- `power_ranking` — weighted composite (0.60 blended prob, 0.40 urgency)  

---

## Configuration Knobs

Set via environment variables or defaults:

- **Bayes province–sector shrinkage**
  - `PROVSEC_ENABLED` (default: `true`)  
  - `PROVSEC_ALPHA` (default: `0.6`; range 0.6–0.8 recommended, 1.0 = no shrink)  
- **Blend weight**
  - `BLEND_BAYES_W` (default: `0.50`)  
- **Cox survival baseline**
  - `S0_T` (default: `0.545332` at 5 years)  

---

## Methodology

1. **Bayes Leg (`p_bayes`)**
   - Constructs features from project metadata (`cleantech`, cost quintile, group, province, sector, start year, FOAK, Greenfield).
   - Province–sector interactions adjusted with shrinkage (`PROVSEC_ALPHA`).
   - Probabilities computed via Naive Bayes log-odds.

2. **Cox Leg (`p_cox`)**
   - Computes linear predictor η using expanded coefficients.
   - Supports both continuous `cost_percentile` and legacy quintiles.
   - Incorporates FOAK, Greenfield, and province/sector fixed effects.
   - Survival probability scaled to 5-year baseline `S0_T`.

3. **Blending**
   - `blended_prob = w * p_bayes + (1 – w) * p_cox`, with `w = BLEND_BAYES_W`.

4. **Priority Index & Ranking**
   - `priority_index = blended_prob / years_remaining`.
   - Normalized urgency scale and combined `power_ranking` output.

---

## Usage

### Default (Colab-style paths)
```bash
python mpi_risk_engine_v03_expanded.py
```

### With environment overrides
```bash
PROVSEC_ALPHA=0.8 BLEND_BAYES_W=0.4 \
INPUT_XLSX=/path/to/input.xlsx \
OUT_CSV=./scored.csv \
python mpi_risk_engine_v03_expanded.py
```

---

## Replication Checklist

1. Provide MPI input file (`mpi_2024_input.xlsx`) and coefficient CSVs.  
2. Adjust environment variables for knobs (optional).  
3. Run script to generate scored outputs.  
4. Archive input + output files.  
5. Record configuration (console prints meta: `PROVSEC_ALPHA`, `BLEND_BAYES_W`, paths).  

---

## Limitations

- Counterfactual scoring only — does not retrain models.  
- Shrinkage and blend weights are **stylized parameters**.  
- Results highlight distributional effects and rankings, not forecasts.  

---

© 2025 — MIT License
