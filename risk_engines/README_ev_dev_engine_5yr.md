# EV + Developer Engine — N-year Horizon (Default 5 years)

## Overview
`ev_dev_engine_5yr.py` allocates project probability mass across candidate FID years, computes expected value (EV) by year, and evaluates developer economics (DevCost, MOIC, k*, IRR).

---

## Inputs
- Input CSV: `mpi_2024_scored.csv` from MPI risk engine
- Required columns: `blended_prob` (or `p_bayes` / `p_cox`), `project_cost`, `years_remaining`, `urgency_scale_(0-1)`

---

## Outputs
- Output CSV: `mpi_2024_ev_dev_combined_5y.csv`
- Columns include:  
  - Annual probabilities: `annual_p_YYYY`  
  - Annual EV: `EV_YYYY`  
  - `EV_cum`, `EV_disc`  
  - Developer metrics: `DevCost`, `E_FID_year`, `PV_MOIC_k`, `k_star`, `IRR_k`, `k_star_adj`

---

## Configuration Knobs
- Probability source: `--p-source` (`blended_prob`, `p_bayes`, `p_cox`)
- Value mode: `--value-mode` (`capex`, `dev_fee`, `count`)
- Developer:  
  - `--dev-fee-rate` (default 0.05)  
  - `--dev-discount` (default 0.13)  
  - `--dev-cost-pct` (default 0.03)  
  - `--k` (default 1.0)  
  - `--scurve` (`S`, `even`, `front`, `back`)  
  - `--scurve-steepness` (default 6.0)

---

## Usage
### Default
```bash
python ev_dev_engine_5yr.py
```

### Custom
```bash
python ev_dev_engine_5yr.py   --input mpi_2024_scored.csv   --output mpi_2024_ev_dev_combined_5y.csv   --p-source blended_prob   --value-mode capex   --dev-fee-rate 0.05   --ev-discount 0.00   --dev-discount 0.13   --dev-cost-pct 0.03   --k 1.0   --scurve S   --scurve-steepness 6.0   --ev-horizon-years 5
```

---

## Replication Checklist
1. Run MPI Risk Engine to create `mpi_2024_scored.csv`
2. Execute EV + Developer Engine with knobs
3. Archive input and output CSVs
4. Record command/config used

---

## Limitations
- Stylized parameters; not calibrated
- Distributional/marginal analysis only
- Results are counterfactual, not forecasts

---
© 2025 — MIT License
