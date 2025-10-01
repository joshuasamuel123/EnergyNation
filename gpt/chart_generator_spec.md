
# 📊 Chart Generator — Final Spec (Energy Nation Data Briefs)

## 1) Goals
- Produce **one or two crisp visuals per brief**.  
- Ensure **deterministic & reproducible outputs**.  
- Output **lightweight PNGs** sized for Substack/Twitter/LinkedIn.  

## 2) Inputs
- **Data:** `energy_nation_flat_dataset_briefs_ready.csv` (single source of truth).  
- **Query parameters:**
  - `topic` (free text → slugified for filenames: lowercase, underscores, strip special chars).  
  - `filter`: dict (e.g., `{"province":["AB","ON"],"sector":["Energy"]}`).  
  - `scenario`: `base | mpo | indigenous | combined | override_{0.25|0.5|0.75|1.0}`.  
  - `compare`: **exactly two `Unique ID`s** for side-by-side/dumbbell plots.  
  - `metric`: one of `EV`, `delta_EV`, `blended_prob`, `delta_p`, `crosser`, `dropout`.  
  - `agg`: `"sum" | "mean" | "median" | "count"`.  

- **Column map (canonical):**
  - Base: `EV_disc_base` (preferred) else `EV_base`; `blended_prob`  
  - Scenarios: `EV_mpo`, `EV_indigenous`, `EV_combined`, `EV_disc_override_*`  
  - Deltas: `delta_EV_*`, `delta_p_*`  
  - Flags: `crosser_*`, `dropout_*`  
  - Meta: `Unique ID`, `project`, `company`, `province`, `sector`, `group`, `project_cost`  

## 3) Supported Chart Types
1. **Portfolio EV Uplift — Bar (Top-N)**  
2. **Distribution — Histogram of ΔEV**  
3. **Cohort Crossing — Count Bars**  
4. **Project Side-by-Side — Dumbbell Plot**  
5. **Province/Sector Aggregates — Grouped Bar**  
6. **Δp vs Project Cost — Scatter**  

## 4) Output & File Rules
- Size: 1100 px wide, 220–700 px height  
- Format: PNG (<200 KB), optional WebP duplicate  
- Naming: `charts/YYYYMMDD_slugifiedtopic_scenario_charttype[_filters|N].png`  
- Sidecar JSON: include filters, metrics, fallback notes, unclipped ranges  

## 5) Visual Style & Accessibility
- Font: bundle open-source font (*Inter* or *Lato*)  
- Palette: default to Viridis or ColorBrewer Set2  
- Axis labels ≤ 12 pt, compact ticks  
- Grid: light y-grid  
- Legends: top-right  
- Annotations: only notable points  

## 6) Error Handling & Guardrails
- Fallback logic explicit in caption + JSON  
- <3 rows: "Not enough data" card  
- Clipping: P1–P99, but original min/max in JSON  
- EV_disc_base preferred; fallback flagged  

## 7) Caption & Alt-Text Autogen
- Caption: include scenario + filters, mean/median/total ΔEV  
- Alt-text: one-sentence takeaway  
- Footnote: "See Technical Note & README for methods."  

## 8) Typical Calls
- Top-10 uplift (MPO)  
- Histogram (Combined)  
- Crossers by Sector (MPO)  
- Side-by-side dumbbell (Combined)  
- Scatter Δp vs Cost (Override 0.5)  

## 9) MVP Checklist
- Implement three first: Top-N bar, Histogram, Side-by-side dumbbell  
- Enforce 1100 px width + compression  
- Emit JSON with all metrics + metadata  
