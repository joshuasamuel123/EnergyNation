# Energy Nation — Figure Specs

## Output
- **Width:** 1100 px (fixed). **Height:** 220–700 px depending on chart.
- **Format:** PNG (target <200 KB). Optionally save WebP duplicate.
- **Naming:** `charts/YYYYMMDD_slug_scenario_charttype[_filtered_HASH].png`
- **Sidecar JSON:** same basename; include filters, metrics, CSV sha256, unclipped ranges, fallback notes.

## Chart Types (MVP)
1) **Top‑N ΔEV bar** — concentration of uplift; N default 10.
2) **ΔEV histogram** — portfolio distribution (clip to P1–P99; record unclipped min/max).
3) **Side‑by‑side dumbbell** — Base EV vs Scenario EV for two IDs.

## Accessibility & Style
- **Font:** bundle a reproducible open‑source font (e.g., Inter/Lato) if needed.
- **Color:** do not set explicit colors in code; rely on defaults.
- **Grid:** light y‑grid; legends top‑right; avoid overlaps.
- **Labels:** annotate only notable points (top 3 by Δp and top 3 by Δp per $).

## Captions & Alt‑Text
- Caption template (auto): “Top‑10 EV uplift under {scenario} for {filters}. Mean ΔEV={mean}; median={median}; total={total}. Counterfactual.”
- Alt‑text: one‑sentence summary of pattern and takeaway.