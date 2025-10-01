# Energy Nation — Style Guide for One‑Minute Data Briefs

## Purpose & Length
- Audience: executives, planners, investors; non‑technical readers first.
- Length: ~120–180 words total prose (excluding headings, bullets).

## Voice & Tone
- Neutral, professional, plain language. Avoid hype and jargon.
- Lead with the **one‑sentence headline insight**.
- Call out concentration vs distribution and note caveats explicitly.

## Structure
1) **Key Insight** (1–2 sentences)
2) **Metrics** (bullets; 4–6 lines max)
3) **Visuals** (1–2 figures; each with alt‑text and short caption auto‑generated)
4) **Interpretation** (2–3 short paragraphs; emphasize thresholds/marginal cohort)
5) **Notes** (methodology, caveats, reproducibility)

## Numbers & Notation
- **EV** and **ΔEV** in millions; 1 decimal place; thousands separators (e.g., 1,234.5).
- **Probabilities:** report Δp in **percentage points (pp)**.
- Prefer **median** alongside **mean**; note when tails drive totals.
- Use exact counts for **Crossers/Dropouts** and name 2–3 **Notables**.

## Definitions (for quick reuse)
- **Blended probability:** the model’s combined success probability (Bayesian prior + Cox time component).  
- **Expected Value (EV):** probability × discounted (or cumulative) project value at base scale.

## Visual Accessibility
- Alt‑text is required; one sentence stating the main takeaway.
- Legends top‑right; y‑grid only; compact ticks. No explicit colors set in code.

## Language Do/Don’t
- Do: “counterfactual uplift,” “portfolio concentration,” “threshold effects,” “marginal cohort.”
- Don’t: “guarantees,” “prediction,” “certainty,” or imply approvals are assured.

## Footers
- Always include: “Results are counterfactual; values reflect scenario probabilities applied to base EV.”
- Cite Technical Note & README as method anchors.