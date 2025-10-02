# MPO Cap Only — Overlay Report

- **Scenario key:** `mpo_only`
- **Projects:** 364
- **Mean Δ blended probability:** 0.031726 (pp)
- **Σ Δ EV (millions CAD):** 16047.320438
- **Σ Δ EV_disc (millions CAD, PV):** 5961.117304
- **Crossovers (→ ≥0.5):** 34
- **Cross-outs (→ <0.5):** 0

## Notes
- EV is computed as probability × project_cost (millions).
- If present, EV_disc uses the discounted project cost column (EV_disc) as the cost base.
- years_in_pipeline is standardized as `2024 - t0_orig + 1`.
- MPO cap limits approvals to the configured cap and applies an odds scaling based on HAZARD_MULTIPLIER.
- Indigenous overlay applies the configured time compression and hazard multiplier only to Indigenous-flagged rows.
