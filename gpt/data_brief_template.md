# Energy Nation — Data Brief Template (Markdown)

> Paste this into Substack as-is, replacing the {{...}} fields.
> Defaults: scenario={{scenario|combined}}, N={{top_n|10}}, filter={{filter_context|all projects}}.

## Key Insight
{{insight}}

### Metrics
- Scenario: **{{scenario}}** ({{filter_context}}); Projects considered: **{{n_projects}}**
- ΔEV (uplift relative to base EV): **mean {{mean_delta_ev}}**, **median {{median_delta_ev}}**, **total {{total_delta_ev}}**
- Probability change (Δp): **mean {{mean_delta_p}}**, **median {{median_delta_p}}** (pp)
- Crossers: **{{crossers}}**; Dropouts: **{{dropouts}}**
- Notables: {{notables}}

### Visuals
![{{alt_primary}}]({{chart_primary}})
{{optional_secondary_start}}
![{{alt_secondary}}]({{chart_secondary}})
{{optional_secondary_end}}

### Interpretation
{{interpretation_paragraphs}}

### Notes
- Counterfactual results: values reflect scenario probabilities applied to the base EV scale.
- Two‑year cap ensures a decision, not an approval; earlier dropout can still be beneficial by reallocating capital.
- Methods: see Technical Note & README (the CSV is the single source of truth).
- Reproducibility: file hash **{{csv_sha256}}**; figure sidecar JSON includes filters, metrics, and any fallbacks.