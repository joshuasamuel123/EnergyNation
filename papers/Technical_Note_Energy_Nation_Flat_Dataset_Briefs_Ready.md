# Technical Note — `energy_nation_flat_dataset_briefs_ready`

This note documents how the script constructs the **briefs‑ready** flat dataset and how to use the resulting schema in analyses and Substack Data Briefs.

## Objectives

1. Canonicalize duplicated key fields (avoid `*_x`, `*_y`, etc.).
2. Attach **EV bases** (`EV_disc_base` preferred; fall back to `EV_base`) using the *override* table.
3. Compute **scenario EVs** and **ΔEV** for:
   - MPO‑only (`blended_prob_mpo` → `EV_mpo`, `delta_EV_mpo`)
   - Indigenous‑only (`blended_prob_indigenous` → `EV_indigenous`, `delta_EV_indigenous`)
   - Combined (Indigenous → MPO) (`blended_prob_combined` → `EV_combined`, `delta_EV_combined`)
4. Compute **Government Override** grid (α ∈ ['0.25', '0.5', '0.75', '1.0']): `EV_disc_override_α` and `delta_EV_override_α` from `blended_prob_override_α`.
5. Produce a stable column ordering (key fields first, then scenarios/overrides, then the rest).

## Inputs (edit in‑file or via env)

- `flat_path`: path to your current flat (must contain `blended_prob` and any scenario probability columns you want to translate into EVs).
- `override_path`: a rich EV source with `EV_disc` and/or `EV_cum` and an ID column (`Unique ID` or `unique_id`).
- `out_path`: output CSV path.

## Core logic

### 1) Canonicalization
For each base field (e.g., `Unique ID`, `project`, `company`, …), the script promotes any of `{name}`, `{name}_x`, `{name}_y`, `{name}.1` to a **single** column named exactly `{name}`. If none match, it selects the first column whose name startswith `{name}`.

### 2) EV base join
From `override_path`, the script builds a slim EV base table keyed by `Unique ID` (or `unique_id`) and computes:
- `EV_disc_base = first(EV_disc)` per ID when present.
- `EV_base = first(EV_cum)` per ID when present.
Left‑join to the flat. If the override ID column differs, it’s dropped post‑merge.

### 3) EV from probability
Given a probability column `p`:
- Determine **PV‑per‑prob** = (`EV_disc_base` or `EV_base`) / `blended_prob` (clipped at 1e‑9 to avoid division by ~0).
- Compute scenario EV = PV‑per‑prob × `p`.
This preserves the project’s valuation scale while translating scenario probabilities to EVs without re‑pricing.

### 4) Scenarios and deltas
For each detected probability column:
- `blended_prob_mpo` → `EV_mpo` and `delta_EV_mpo = EV_mpo − EV_base*`  
- `blended_prob_indigenous` → `EV_indigenous` and `delta_EV_indigenous`  
- `blended_prob_combined` → `EV_combined` and `delta_EV_combined`  
- Overrides `blended_prob_override_α` → `EV_disc_override_α` and `delta_EV_override_α`  
`*` Base is `EV_disc_base` when present and non‑NA, else `EV_base`.

### 5) Column ordering
The script pulls a prioritized list of **first columns** (IDs, meta, bases, per‑scenario outputs and flags). Any remaining columns are appended in their original order to avoid accidental drops.

## Expected columns

- **Core**: `Unique ID, project, company, province, sector, group, start_year, end_year, reporting_years, project_cost, p_bayes, p_cox, blended_prob, priority_index, urgency_scale_(0-1), power_ranking`  
- **Bases**: `EV_base, EV_disc_base`  
- **Scenarios**: `blended_prob_*`, `delta_p_*`, `EV_*`, `delta_EV_*`, `crosser_*`, `dropout_*` for `mpo`, `indigenous`, `combined`  
- **Overrides**: for α ∈ ['0.25', '0.5', '0.75', '1.0'] — `blended_prob_override_α`, `delta_p_override_α`, `EV_disc_override_α`, `delta_EV_override_α`, `crosser_override_α`, `dropout_override_α`

Presence depends on upstream generators.

## Usage patterns

- **Portfolio snapshots**: sum `delta_EV_*` across projects; report mean vs median to show concentration.
- **Marginal cohort**: filter `crosser_* == True` to examine threshold effects and narrative case studies.
- **Province/sector cuts**: groupby to surface heterogeneous effects and outliers.

## Edge cases & safeguards

- If `blended_prob` is ~0, division is clipped at `1e-9` to avoid extreme PV‑per‑prob.
- If neither `EV_disc_base` nor `EV_base` is present, scenario EVs will be NA (which is correct/transparent).
- If a scenario probability column is missing, that scenario’s EV/ΔEV are simply not created (no error).

## Repro checklist

1. Confirm that upstream runners produced the probability columns you expect to translate.
2. Confirm that the override EV source is aligned by Unique ID (or add a pre‑join mapping step if needed).
3. Re‑run the script after any upstream changes to keep the CSV in sync.

## Data dictionary (dtypes snapshot — first 80)
- `Unique ID`: int64
- `project`: object
- `company`: object
- `province`: object
- `sector`: object
- `group`: object
- `start_year`: int64
- `end_year`: int64
- `reporting_years`: int64
- `project_cost`: float64
- `p_bayes`: float64
- `p_cox`: float64
- `blended_prob`: float64
- `priority_index`: float64
- `urgency_scale_(0-1)`: float64
- `power_ranking`: float64
- `EV_base`: float64
- `EV_disc_base`: float64
- `blended_prob_mpo`: float64
- `delta_p_mpo`: float64
- `EV_mpo`: float64
- `delta_EV_mpo`: float64
- `blended_prob_indigenous`: float64
- `delta_p_indigenous`: float64
- `EV_indigenous`: float64
- `delta_EV_indigenous`: float64
- `blended_prob_combined`: float64
- `delta_p_combined`: float64
- `EV_combined`: float64
- `delta_EV_combined`: float64
- `blended_prob_override_0.25`: float64
- `blended_prob_override_0.5`: float64
- `blended_prob_override_0.75`: float64
- `blended_prob_override_1.0`: float64
- `delta_p_override_0.25`: float64
- `delta_p_override_0.5`: float64
- `delta_p_override_0.75`: float64
- `delta_p_override_1.0`: float64
- `EV_disc_override_0.25`: float64
- `EV_disc_override_0.5`: float64
- `EV_disc_override_0.75`: float64
- `EV_disc_override_1.0`: float64
- `delta_EV_override_0.25`: float64
- `delta_EV_override_0.5`: float64
- `delta_EV_override_0.75`: float64
- `delta_EV_override_1.0`: float64
- `crosser_mpo`: int64
- `crosser_indigenous`: int64
- `crosser_combined`: int64
- `crosser_override_0.25`: int64
- `crosser_override_0.5`: int64
- `crosser_override_0.75`: int64
- `crosser_override_1.0`: int64
- `dropout_mpo`: int64
- `dropout_indigenous`: int64
- `dropout_combined`: int64
- `dropout_override_0.25`: int64
- `dropout_override_0.5`: int64
- `dropout_override_0.75`: int64
- `dropout_override_1.0`: int64
- `project_x`: object
- `company_x`: object
- `province_x`: object
- `sector_x`: object
- `group_x`: object
- `start_year_x`: int64
- `end_year_x`: int64
- `reporting_years_x`: int64
- `project_cost_x`: float64
- `cleantech_x`: object
- `p_bayes_x`: float64
- `p_cox_x`: float64
- `blended_prob_x`: float64
- `priority_index_x`: float64
- `urgency_scale_(0-1)_x`: float64
- `power_ranking_x`: float64
- `EV_disc_x`: float64
- `EV_cum_x`: float64
- `EV_disc_base_x`: float64
- `EV_base_x`: float64
