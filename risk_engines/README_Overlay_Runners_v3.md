# Overlay Runners — Government Override × Contracted Demand & Unified (Indigenous + MPO)

This repository contains two complementary **scenario-only overlay runners** for the Major Projects Inventory (MPI). Both tools apply **counterfactual policy interventions** on already-scored projects without re-estimating Bayes or Cox models.

---

## 1. Government Override × Contracted Demand Runner (v2)

**Purpose:**  
Applies two levers on top of baseline probabilities (`p_bayes`, `p_cox`, `blended_prob`):  
- **Government Override (α):** policy dial shifting Bayes odds and Cox hazard.  
- **Contracted Demand (β):** PPA/CfD/offtake coverage scaling.  
- **Interaction (Θ):** tests substitution vs complementarity.

**Key Features (v2):**  
- EV basis: uses `EV_disc` (preferred) or `EV_cum`.  
- Anchors exposed as scenario dials (conservative/central/optimistic).  
- Evidence tags and disclaimers embedded.  
- QA metrics: cap hits, crossers.  
- Outputs audit JSON for replication.

**Run (Colab-ready):**
```bash
python go_override_runner_colab_v2.py
```

**Outputs (default `./overlay_out/`):**
- `override_contract_overlay_full.csv` — per-project overlays.  
- `override_summary_by_alpha.csv` — summaries by α.  
- `override_contract_grid_summary.csv` — α×β grid with Θ.  
- `override_anchor_sensitivity.csv` — sensitivity bands (optional).  
- `override_run_audit.json` — reproducibility metadata.

📄 See: *Technical_Note_Government_Override_v3.pdf*

---

## 2. Unified Overlay Runner (Indigenous + MPO)

**Purpose:**  
Applies counterfactual policy overlays for:  
- **Indigenous Overlay:** time compression (Δ years, default = –1) + hazard multiplier.  
- **MPO Overlay:** hard cap on approval duration (default = 2 years).  
- **Combined:** sequential application (default: MPO → Indigenous).

**Key Features (Revised v2):**  
- Computes `years_in_pipeline = 2024 − t0_orig + 1`.  
- Uses `EV_disc` if present; otherwise falls back to `project_cost`.  
- Outputs grouped summaries (province, sector, group, FOAK, cleantech, cost_band).  
- Writes concise Markdown roll-up.

**Run (Colab-ready):**
```bash
python unified_overlay_runner_colab_revised_v2.py
```

**Outputs (default `./overlay_outputs/`):**
- `{scenario}_overlay_results.csv` — per-project overlays.  
- `{scenario}_summary_{group}.csv` — grouped summaries.  
- `{scenario}_report.md` — concise Markdown roll-up.

📄 See: *Technical_Note_Unified_Overlay_v3.pdf*

---

## 3. Replication Checklist (common to both)

1. Provide input CSV with required fields.  
2. Declare scenario knobs (`alphas`, `betas`, `theta`, caps, Δ years, multipliers).  
3. Run via Colab or CLI.  
4. Archive input and all outputs.  
5. Save CONFIG / code hash and audit JSON/Markdown reports.

---

## 4. Limitations

- Counterfactual only; no re-estimation of Bayes/Cox.  
- Stylized parameters; results show **distributional shifts, not forecasts**.  
- Designed for transparency, reproducibility, and audit.

---

© 2025 — MIT License
