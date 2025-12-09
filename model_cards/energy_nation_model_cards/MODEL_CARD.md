# Energy Nation Modeling Suite (v2025a)
_Comprehensive Counterfactual Modeling Framework for Project-Level Analysis_

**Maintainer:** Joshua Samuel · Northeast Renewables LP  
**License:** CC BY-NC-SA 4.0 — Open for research and educational use. Commercial use prohibited without written permission.

---

## 1. Overview
The **Energy Nation Modeling Suite (v2025a)** is a modular pipeline for quantitative evaluation of Canada’s Major Projects Inventory (MPI).  
It integrates risk estimation, expected-value and developer economics, and policy-counterfactual overlays into a unified analytical workflow.

The suite enables transparent, reproducible analysis of how policy signals—such as permitting caps, Indigenous participation, or government override mechanisms—affect project-level probabilities, expected values (EV), and portfolio-level economic outcomes.

---

## 2. Dependency Chain

| Stage | Script | Description | Key Output |
|--------|---------|-------------|-------------|
| 1 | `mpi_risk_engine_v03_expanded.py` | Computes base probabilities (Bayes, Cox, blended) for all MPI projects. | `mpi_2024_scored.csv` |
| 2 | `ev_dev_engine_5yr.py` | Expands probabilities into 5-year expected-value horizons and developer metrics (PV, MOIC, k*, IRR). | `mpi_2024_ev_dev_combined_5y.csv` |
| 3 | `unified_overlay_runner_colab_revised_v2_patched.py` | Applies Indigenous and MPO policy overlays individually and jointly. | Overlay CSVs, summaries, Markdown reports |
| 4 | `government_overrisde_runner_colab_v2.py` | Models higher-order government intervention (Override + Contracted-Demand) with α/β grids and interaction θ. | Full per-project and grid summaries |

---

## 3. Intended Use & Audience
**Intended for:**  
- Energy policy analysts, system modelers, and research institutions (e.g., EMH).  
- Academic and non-commercial R&D exploring the effect of policy levers on project viability.  

**Not intended for:**  
- Commercial forecasting, investment solicitation, or production-grade financial models.

---

## 4. Inputs & Outputs

| Input | Description | Source |
|--------|-------------|---------|
| `mpi_2024_input.xlsx` | Base dataset of project features and metadata | NRCan / MPI |
| `bayes_lr_regenerated_coefficients_expanded.csv` | Log-ratio coefficients for Bayes engine | Derived |
| `cox_refit_coefficients_timesplit_expanded.csv` | Re-fit Cox regression coefficients | Derived |

| Output | Description |
|--------|-------------|
| `mpi_2024_scored.csv` | Base probabilities & urgency metrics |
| `mpi_2024_ev_dev_combined_5y.csv` | Expected value + developer metrics |
| `overlay_outputs/*.csv` | Indigenous / MPO overlay results |
| `overlay_out/*.csv` | Government Override + Contracted Demand results |
| `.json`, `.md` reports | Audit trail and scenario summaries |

---

## 5. Parameter Defaults

| Category | Parameter | Default |
|-----------|------------|----------|
| **Risk Engine** | `BLEND_BAYES_W` | 0.50 |
| | `PROVSEC_ALPHA` | 0.6 |
| **EV / Developer Engine** | `EV_HORIZON_YEARS` | 5 |
| | `DEV_COST_PCT` | 0.03 |
| | `DEV_DISCOUNT` | 0.13 |
| | `EV_DISCOUNT` | 0.00 |
| | `BASE_YEAR` | 2024 |
| **MPO / Indigenous Overlays** | `APPROVAL_CAP_YEARS` | 2 |
| | `TIME_COMPRESSION_YEARS` | −1 |
| | `HAZARD_MULTIPLIER` | 1.10 |
| **Override / Contracts** | `α` grid | 0.25–1.00 |
| | `β` grid | 0.0–1.0 |
| | `θ` (interaction) | 0.00 |
| | `θ_scale` | 0.05 |

---

## 6. Methods Summary
1. **Risk Engine**:  
   - Computes `p_bayes` via log-odds product of categorical likelihood ratios with province-sector shrinkage.  
   - Computes `p_cox` via parametric survival model with re-fit coefficients.  
   - Blends the two via fixed weight to produce `blended_prob`.

2. **EV + Developer Engine**:  
   - Allocates probability mass across candidate FID years using a softmax allocator.  
   - Derives EV_cum, EV_disc, and developer metrics (`k*`, `PV_MOIC_k`, `IRR_k`).  

3. **Unified Overlay Runner**:  
   - Applies Indigenous and MPO policy levers as counterfactuals via odds scaling.  
   - Computes EV deltas, crossovers, and summary reports.  

4. **Government Override Runner**:  
   - Adds higher-order intervention levers (α, β, θ).  
   - Evaluates portfolio uplift, sensitivity bands, and interaction dynamics.

---

## 7. Reproducibility
- **Language:** Python 3.10+  
- **Libraries:** pandas, numpy, math, argparse, json  
- **Execution:** Deterministic for identical CSV inputs.  
- **Artifacts:** Each stage writes CSVs with audit-ready metadata and optional JSON/Markdown logs.  
- **Suggested structure:**
  ```
  /data/
  /scripts/
  /outputs/
  /docs/
  ```

---

## 8. Limitations & Risks
- Counterfactual overlays are **scenario simulations**, not forecasts.  
- EV and probability estimates rely on historical MPI data; extrapolation may not capture post-policy behavior.  
- Developer economics assume simplified S-curve spend profiles and constant discount rates.

---

## 9. Versioning & Metadata
- **Version:** v2025a  
- **Change log:** Adds 5-year horizon, discounted EV basis, and unified overlay structure.  
- **Maintainer:** Joshua Samuel · Northeast Renewables LP  
- **Contact:** Internal collaboration and R&D inquiries only.

---

## 10. License
Licensed under **Creative Commons Attribution–NonCommercial–ShareAlike 4.0 (CC BY-NC-SA 4.0)**  
Open for research and educational use. Commercial use prohibited without written permission.
