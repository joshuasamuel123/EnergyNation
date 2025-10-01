# Energy Nation — Flat Dataset (Briefs-Ready)

This repository contains:
- `energy_nation_flat_dataset_briefs_ready.py` — a utility script that prepares a **briefs‑ready** flat dataset by (i) canonicalizing key columns, (ii) attaching EV bases (discounted and/or cumulative) from the override file, and (iii) computing scenario Expected Value (EV) outputs and deltas for the MPO, Indigenous, Combined overlays, plus Government Override α-grid.
- `energy_nation_flat_dataset_briefs_ready.csv` — the output table produced by the script; serves as the **single source of truth** for one‑minute Data Briefs.

**Last updated:** 2025-10-01

---

## What you get

- **Rows:** 364
- **Columns:** 179

### Column families (detected in this dataset)

- **Core identity & meta**
  Unique ID, project, company, province, sector, group, start_year, end_year, reporting_years, project_cost, p_bayes, p_cox, blended_prob, priority_index, urgency_scale_(0-1), power_ranking

- **EV bases**
  EV_base, EV_disc_base

- **MPO scenario**
  blended_prob_mpo, delta_p_mpo, EV_mpo, delta_EV_mpo, crosser_mpo, dropout_mpo, delta_EV_mpo_only

- **Indigenous scenario**
  blended_prob_indigenous, delta_p_indigenous, EV_indigenous, delta_EV_indigenous, crosser_indigenous, dropout_indigenous

- **Combined scenario (Indigenous → MPO)**
  blended_prob_combined, delta_p_combined, EV_combined, delta_EV_combined, crosser_combined, dropout_combined

- **Government Override α ∈ ['0.25', '0.5', '0.75', '1.0']**
  (probabilities, deltas, EVs, ΔEVs, crosser/dropout flags)
  blended_prob_override_0.25, blended_prob_override_0.5, blended_prob_override_0.75, blended_prob_override_1.0, delta_p_override_0.25, delta_p_override_0.5, delta_p_override_0.75, delta_p_override_1.0, EV_disc_override_0.25, EV_disc_override_0.5, EV_disc_override_0.75, EV_disc_override_1.0, delta_EV_override_0.25, delta_EV_override_0.5, delta_EV_override_0.75, delta_EV_override_1.0, crosser_override_0.25, crosser_override_0.5, crosser_override_0.75, crosser_override_1.0, dropout_override_0.25, dropout_override_0.5, dropout_override_0.75, dropout_override_1.0

> Tip: *Core* columns should exist across runs; scenario/override columns appear when the corresponding runner generated those fields.

---

## Quick start

1. **Run the script** (paths are set for Colab-style `/content/…`; edit as needed):
   ```bash
   python energy_nation_flat_dataset_briefs_ready.py
   ```
   It will read your current flat (`flat_path`), join EV bases from the override file (`override_path`), compute EVs and deltas, then write the combined CSV to `out_path`.

2. **Point your notebook or plotter** at `energy_nation_flat_dataset_briefs_ready.csv` for Data Briefs:
   - Use `EV_disc_base` when present (preferred) else `EV_base`.
   - Scenario EVs: `EV_mpo`, `EV_indigenous`, `EV_combined`, and `EV_disc_override_{α}` for α in ['0.25', '0.5', '0.75', '1.0'].
   - Scenario deltas vs base: `delta_EV_*` columns.

3. **Interpretation (one‑minute briefs)**
   - **Blended probability** is the model’s combined success probability (Bayesian prior + Cox time‑component).
   - **EV (Expected Value)** is that probability × (discounted or cumulative) project value.
   - **ΔEV** is scenario uplift relative to base EV. Focus on the distribution (median vs mean) and the *marginal cohort* near threshold crossings.

---

## Schema preview

- **Five sample rows:** shown below to illustrate values and NA patterns.
