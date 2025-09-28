
# Technical Note: Unified Overlay Runner (Indigenous + MPO)

## 1. Background and Purpose
The *Unified Overlay Runner* is a post-estimation tool designed to apply **counterfactual policy adjustments** to projects in the Major Projects Inventory (MPI). It does not refit the base Bayes or Cox engines. Instead, it simulates how probabilities of project success would shift under two popular policy interventions:

1. **Indigenous Overlay** – time compression (Δ years) and hazard multiplier.  
2. **MPO Overlay** – hard cap on approval years.  
3. **Combined Policy** – sequential application of both overlays under a configurable rule (default: `ind_then_cap`).  

The goal is to evaluate **distributional effects** and **marginal uplifts** across projects, not to generate new forecasts.

## 2. Methods

### 2.1 Base Inputs
The runner requires four inputs:  
1. MPI Input File: `mpi_2024_input.xlsx`  
2. Bayes Likelihood Ratios: `bayes_lr_regenerated_coefficients_expanded.csv`  
3. Cox Coefficients: `cox_refit_coefficients_timesplit_expanded.csv`  
4. Breslow Baseline Survival: `breslow_baseline_survival_2018_2020.csv`  

### 2.2 Overlay Logic
- Indigenous overlay: time shift and hazard multiplier  
- MPO overlay: hard cap on approval years  
- Combined: sequence determined by `both_policy` (default = `ind_then_cap`)  

### 2.3 Outputs
Each row includes: overlay flags, adjusted times (`t0_adj`), risk scores, knot diagnostics, Cox probabilities, blended probabilities, and deltas.  
Outputs: `unified_overlay_run.csv` and `unified_overlay_summary.md`.

## 3. Configuration
Parameters in `CONFIG`:  
- `delta_years`: –1.0  
- `hazard_multiplier`: 1.1  
- `mpo_cap_years`: 2.0  
- `both_policy`: ind_then_cap  
- `w`: 0.5  

## 4. Replication Procedure
1. Prepare inputs.  
2. Set flags in the MPI file (`indigenous_flag_overlay`, `mpo_flag`).  
3. Run: `python unified_overlay_runner_colab_report.py`  
4. Review outputs: CSV + Markdown summary.

## 5. Audit Checks
- Fixture test across flag combos.  
- Parity checks (MPO-only vs Indigenous-only).  
- Knot diagnostics (`knot_before`, `knot_after`).  
- Probability shifts (`delta_blended` positive when approvals shortened).  

## 6. Limitations
- Counterfactual only; does not re-estimate coefficients.  
- Parameters are stylized.  
- No Indigenous pp uplift modeled.  
- Shows distributional shifts, not forecasts.

## 7. Conclusion
The runner provides a transparent, auditable framework for policy overlay analysis. Results are reproducible and highlight who benefits most under Indigenous and MPO interventions.  
