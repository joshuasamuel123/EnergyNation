#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Government Override + Contracted-Demand Runner — v2 (Discounted EV, Evidence Tags, Sensitivity Bands)

Scenario-only overlays applied to an already-scored MPI cohort (NO re-estimation of Bayes/Cox).

What’s new vs v1:
- EV basis: uses EV_disc if present (discounted EV); falls back to EV_cum only if EV_disc missing.
- Anchors exposed as stylized *scenario dials* (conservative/central/optimistic) with optional sensitivity table.
- Interaction bump: parameterized via theta_scale (small, explicit), reported in summary.
- Evidence tags + disclaimer embedded in outputs; audit JSON written.
- Performance hygiene (batch concat) and QA metrics (cap hits, crossers).
"""

import os, math, argparse, json
import numpy as np
import pandas as pd

# ==================== CONFIG (defaults; override via CLI) ====================
CONFIG = {
    # Inputs (CSV must include: p_bayes, p_cox, blended_prob; EV_disc preferred, EV_cum acceptable)
    "in_csv": "/content/mpi_2024_ev_dev_combined_5y.csv",

    # Outputs
    "out_dir": "./overlay_out",

    # Override strength grid (α) & Contract strength grid (β)
    "alphas": [0.25, 0.50, 0.75, 1.00],                  # Guidance → Emergency
    "betas":  [0.00, 0.25, 0.50, 0.75, 1.00],            # Off → Max

    # Interaction knob between override & contracts (−1=substitution, 0=independent, +1=complementarity)
    "theta": 0.00,
    # Small scalar for logit-bump magnitude (explicit, reported)
    "theta_scale": 0.05,

    # Probability cap & crosser threshold
    "cap_p": 0.90,
    "threshold": 0.50,

    # Anchors (stylized scenario dials). v2 uses the "central" set for main run, but records bands.
    "anchors_bands": {
        "conservative": {"OR_override": math.exp(0.45), "HR_override": math.exp(0.30), "k_contract": 0.50, "h_contract": 0.35},
        "central":      {"OR_override": math.exp(0.75), "HR_override": math.exp(0.50), "k_contract": 0.75, "h_contract": 0.50},
        "optimistic":   {"OR_override": math.exp(1.00), "HR_override": math.exp(0.75), "k_contract": 1.00, "h_contract": 0.65},
    },
    "anchors_use": "central",  # which band to use for the main run

    # Evidence tags & disclaimer
    "evidence_timeline":   "moderate",
    "evidence_contracts":  "weak",
    "evidence_indigenous": "weak",
    "disclaimer": ("Counterfactual overlays; no re-estimation of Bayes/Cox; "
                   "stylized scenario dials with sensitivity bands; not a forecast."),

    # Sensitivity table toggle (writes a compact CSV comparing bands at α=0.5, β=0.5)
    "write_anchor_sensitivity": True,

    # Plot toggle (not producing charts here; keep code minimal)
}

# ==================== Labels ====================
LABELS        = {0.25: "Guidance", 0.50: "Priority", 0.75: "Mandate", 1.00: "Emergency"}
BETA_LABELS   = {0.00: "Off", 0.25: "Light", 0.50: "Medium", 0.75: "Strong", 1.00: "Max"}

# ==================== Helpers ====================
def clamp01(x):
    try:
        v = float(x)
        if not np.isfinite(v): return 0.0
        return float(np.clip(v, 0.0, 1.0))
    except Exception:
        return 0.0

def safe_prob(p):
    return float(np.clip(float(p), 1e-9, 1.0 - 1e-9))

def write_csv(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False)

def estimate_w_bayes_row(p_bayes, p_cox, p_blend):
    """Estimate per-row Bayes blend weight from the three legs (no refit)."""
    pb = safe_prob(p_bayes); pc = safe_prob(p_cox)
    denom = pb - pc
    if abs(denom) < 1e-12:
        return 0.60
    w = (p_blend - pc) / denom
    return float(np.clip(w, 0.0, 1.0))

# ==================== Transforms ====================
def apply_override_scalar(p_bayes, p_cox, w_bayes, alpha, OR_anchor, HR_anchor, cap):
    """Post-model override lever with strength α: Bayes logit shift & Cox survival power; then re-blend."""
    pb = safe_prob(p_bayes); pc = safe_prob(p_cox); w = float(np.clip(w_bayes, 0.0, 1.0))
    # Bayes
    OR_eff   = OR_anchor ** alpha
    logit_pb = math.log(pb / (1 - pb))
    pb_adj   = 1 / (1 + math.exp(-(logit_pb + math.log(OR_eff))))
    # Cox
    HR_eff = HR_anchor ** alpha
    S      = 1 - pc
    S_adj  = S ** HR_eff
    pc_adj = 1 - S_adj
    # Blend & cap
    p_blend = float(np.clip(w * pb_adj + (1 - w) * pc_adj, 0.0, cap))
    return pb_adj, pc_adj, p_blend

def apply_contract_overlay_row(row, beta, k, h, cap):
    """Contracted-demand overlay scaled by coverage in [0,1], intensity β."""
    coverage = clamp01(row.get("contract_coverage_share", 0.0))
    if beta <= 0.0 or coverage <= 1e-12:
        return row["p_bayes"], row["p_cox"], row["blended_prob"]

    pb = safe_prob(row["p_bayes"]); pc = safe_prob(row["p_cox"]); w = float(np.clip(row["w_bayes_est"], 0.0, 1.0))

    OR_c = math.exp(k * coverage) ** beta
    HR_c = math.exp(h * coverage) ** beta

    logit_pb = math.log(pb / (1 - pb))
    pb_adj   = 1 / (1 + math.exp(-(logit_pb + math.log(OR_c))))

    S      = 1 - pc
    S_adj  = S ** HR_c
    pc_adj = 1 - S_adj

    p_blend = float(np.clip(w * pb_adj + (1 - w) * pc_adj, 0.0, cap))
    return pb_adj, pc_adj, p_blend

def _slogit(p):
    p = safe_prob(p)
    return math.log(p / (1 - p))

def compose_with_interaction(p_base, p_override, p_contract, theta, theta_scale, cap):
    """Compose two levers: sequential probability + small logit-bump scaled by theta_scale."""
    p_base = safe_prob(p_base); p_over = safe_prob(p_override); p_cont = safe_prob(p_contract)
    # Sequential baseline (bounded)
    p_seq = float(np.clip(p_over + p_cont - p_base, 0.0, cap))
    if abs(theta) < 1e-12 or abs(theta_scale) < 1e-12:
        return p_seq
    # Small bump in logit space, scaled
    logit_base = _slogit(p_base)
    bump = theta_scale * (_slogit(p_over) - logit_base) * (_slogit(p_cont) - logit_base)
    logit_final = _slogit(p_seq) + theta * bump
    p_final = 1 / (1 + math.exp(-logit_final))
    return float(np.clip(p_final, 0.0, cap))

# ==================== Core ====================
def run_override_contract(in_csv, out_dir, alphas, betas, theta, theta_scale, cap_p, threshold, anchors_use, anchors_bands, write_anchor_sensitivity):
    df = pd.read_csv(in_csv)

    # Required columns
    for col in ["p_bayes", "p_cox", "blended_prob"]:
        if col not in df.columns:
            raise ValueError(f"Input must include '{col}' column. Missing in file: {in_csv}")

    # EV column preference
    ev_col = "EV_disc" if "EV_disc" in df.columns else ("EV_cum" if "EV_cum" in df.columns else None)
    if ev_col is None:
        raise ValueError("Input must include EV_disc (preferred) or EV_cum.")

    # Copy & prep
    out = df.copy()

    # Per-row blend weights (no model refit)
    out["w_bayes_est"] = out.apply(lambda r: estimate_w_bayes_row(r["p_bayes"], r["p_cox"], r["blended_prob"]), axis=1).fillna(0.60)

    # Normalize contract inputs
    out["ppa_flag"]         = out.get("ppa_flag", 0)
    out["gov_ofstake_flag"] = out.get("gov_ofstake_flag", 0)

    # Ensure clamp01 is applied correctly to merchant_share and contract_coverage_share
    merchant_share_data = out.get("merchant_share", 0.0)
    if isinstance(merchant_share_data, pd.Series):
        out["merchant_share"] = merchant_share_data.apply(clamp01)
    else:
        out["merchant_share"] = clamp01(merchant_share_data)

    cov = out.get("contract_coverage_share", np.nan)
    if isinstance(cov, pd.Series):
        out["contract_coverage_share"] = cov.where(pd.notna(cov), 1.0 - out["merchant_share"]).apply(clamp01)
    else:
        out["contract_coverage_share"] = clamp01(cov if pd.notna(cov) else 1.0 - out["merchant_share"])


    # Anchors (select band)
    band = anchors_bands.get(anchors_use, anchors_bands["central"])
    OR_OVERRIDE_ANCHOR = float(band["OR_override"])
    HR_OVERRIDE_ANCHOR = float(band["HR_override"])
    K_CONTRACT         = float(band["k_contract"])
    H_CONTRACT         = float(band["h_contract"])

    # ---------- Override-only (α) ----------
    # Batch-compute columns into a dict, then concat (performance hygiene)
    over_cols = {}
    pv_success = np.where(out["blended_prob"] > 1e-12, out[ev_col] / out["blended_prob"], np.nan)

    for a in alphas:
        res = out.apply(
            lambda r: apply_override_scalar(r["p_bayes"], r["p_cox"], r["w_bayes_est"], a,
                                            OR_OVERRIDE_ANCHOR, HR_OVERRIDE_ANCHOR, cap_p),
            axis=1, result_type="expand"
        )
        p_ba, p_ca, p_bl = res[0].values, res[1].values, res[2].values
        over_cols[f"p_bayes_{a}"]  = p_ba
        over_cols[f"p_cox_{a}"]    = p_ca
        over_cols[f"blended_{a}"]  = p_bl
        dp = p_bl - out["blended_prob"].values
        over_cols[f"Δp_{a}"]       = dp
        EVa = pv_success * p_bl
        over_cols[f"{ev_col}_{a}"] = EVa
        over_cols[f"ΔEV_{a}"]      = EVa - out[ev_col].values

    out = pd.concat([out, pd.DataFrame(over_cols, index=out.index)], axis=1)

    # ---------- Contract-only (β) ----------
    cont_cols = {}
    for b in betas:
        if b == 0.0:
            cont_cols[f"p_bayes_contract_{b}"]   = out["p_bayes"].values
            cont_cols[f"p_cox_contract_{b}"]     = out["p_cox"].values
            cont_cols[f"blended_contract_{b}"]    = out["blended_prob"].values
        else:
            cres = out.apply(lambda r: apply_contract_overlay_row(r, b, K_CONTRACT, H_CONTRACT, cap_p),
                             axis=1, result_type="expand")
            cont_cols[f"p_bayes_contract_{b}"] = cres[0].values
            cont_cols[f"p_cox_contract_{b}"]   = cres[1].values
            cont_cols[f"blended_contract_{b}"] = cres[2].values

    out = pd.concat([out, pd.DataFrame(cont_cols, index=out.index)], axis=1)

    # ---------- Compose α × β with interaction θ ----------
    comp_cols = {}
    cap_hits = 0

    for a in alphas:
        p_over = out[f"blended_{a}"].values
        for b in betas:
            p_cont = out[f"blended_contract_{b}"].values
            blended = np.fromiter(
                (compose_with_interaction(pb, po, pc, theta, theta_scale, cap_p)
                 for pb, po, pc in zip(out["blended_prob"].values, p_over, p_cont)),
                dtype=float, count=len(out)
            )
            comp_cols[f"blended_alpha_{a}_beta_{b}"] = blended
            dp = blended - out["blended_prob"].values
            comp_cols[f"Δp_alpha_{a}_beta_{b}"] = dp
            EVab = pv_success * blended
            comp_cols[f"{ev_col}_alpha_{a}_beta_{b}"] = EVab
            comp_cols[f"ΔEV_alpha_{a}_beta_{b}"]      = EVab - out[ev_col].values
            cap_hits += int((blended >= (cap_p - 1e-9)).sum())

    out = pd.concat([out, pd.DataFrame(comp_cols, index=out.index)], axis=1)

    # ---------- Write per-project ----------
    os.makedirs(out_dir, exist_ok=True)
    per_project_csv = os.path.join(out_dir, "override_contract_overlay_full.csv")
    write_csv(out, per_project_csv)

    # ---------- Summaries ----------
    base_EV_sum   = float(np.nansum(out[ev_col].values))
    base_crossers = int((out["blended_prob"] >= threshold).sum())

    # Override-only summary (by α)
    rows = []
    for a in alphas:
        dp = out[f"Δp_{a}"]
        dE = out[f"ΔEV_{a}"]
        rows.append({
            "alpha": a,
            "alpha_label": LABELS.get(a, str(a)),
            "Δp_mean": float(np.nanmean(dp.values)),
            "Δp_median": float(np.nanmedian(dp.values)),
            "Δp_p10": float(np.nanpercentile(dp.values, 10)),
            "Δp_p90": float(np.nanpercentile(dp.values, 90)),
            "ΔEV_sum": float(np.nansum(dE.values)),
            "uplift_%_EV": (float(np.nansum(dE.values)) / base_EV_sum) if base_EV_sum else np.nan,
            "net_new_crossers": int((out[f"blended_{a}"] >= threshold).sum() - base_crossers)
        })
    over_sum = pd.DataFrame(rows)
    write_csv(over_sum, os.path.join(out_dir, "override_summary_by_alpha.csv"))

    # Grid summary (α × β, with θ)
    rows = []
    for a in alphas:
        for b in betas:
            dp = out[f"Δp_alpha_{a}_beta_{b}"]
            dE = out[f"ΔEV_alpha_{a}_beta_{b}"]
            rows.append({
                "alpha": a, "alpha_label": LABELS.get(a, str(a)),
                "beta": b,  "beta_label":  BETA_LABELS.get(b, str(b)),
                "THETA": float(theta), "theta_scale": float(theta_scale),
                "Δp_mean": float(np.nanmean(dp.values)),
                "Δp_median": float(np.nanmedian(dp.values)),
                "Δp_p10": float(np.nanpercentile(dp.values, 10)),
                "Δp_p90": float(np.nanpercentile(dp.values, 90)),
                "ΔEV_sum": float(np.nansum(dE.values)),
                "uplift_%_EV": (float(np.nansum(dE.values)) / base_EV_sum) if base_EV_sum else np.nan,
                "net_new_crossers": int((out[f"blended_alpha_{a}_beta_{b}"] >= threshold).sum() - base_crossers),
            })
    grid_sum = pd.DataFrame(rows)
    write_csv(grid_sum, os.path.join(out_dir, "override_contract_grid_summary.csv"))

    # ---------- Optional sensitivity table over anchor bands (α=0.5, β=0.5) ----------
    anchor_sens_path = None
    if write_anchor_sensitivity:
        a_sens, b_sens = 0.50, 0.50
        sens_rows = []
        for band_name, anchors in anchors_bands.items():
            ORa = anchors["OR_override"]; HRa = anchors["HR_override"]
            ka  = anchors["k_contract"];   ha  = anchors["h_contract"]

            # One-shot recompute for the pair (α, β) using alternative anchors
            p_over_tmp = np.fromiter(
                (apply_override_scalar(r["p_bayes"], r["p_cox"], r["w_bayes_est"],
                                       a_sens, ORa, HRa, cap_p)[2]
                 for _, r in out.iterrows()), dtype=float, count=len(out)
            )
            p_cont_tmp = np.fromiter(
                (apply_contract_overlay_row(r, b_sens, ka, ha, cap_p)[2]
                 for _, r in out.iterrows()), dtype=float, count=len(out)
            )
            blend_tmp  = np.fromiter(
                (compose_with_interaction(pb, po, pc, theta, theta_scale, cap_p)
                 for pb, po, pc in zip(out["blended_prob"].values, p_over_tmp, p_cont_tmp)),
                dtype=float, count=len(out)
            )
            dp_tmp = blend_tmp - out["blended_prob"].values
            EV_tmp = pv_success * blend_tmp
            dE_tmp = EV_tmp - out[ev_col].values
            sens_rows.append({
                "band": band_name,
                "OR_override": ORa, "HR_override": HRa, "k_contract": ka, "h_contract": ha,
                "alpha": a_sens, "beta": b_sens,
                "Δp_mean": float(np.nanmean(dp_tmp)), "Δp_median": float(np.nanmedian(dp_tmp)),
                "ΔEV_sum": float(np.nansum(dE_tmp)),
                "uplift_%_EV": (float(np.nansum(dE_tmp)) / base_EV_sum) if base_EV_sum else np.nan
            })
        anchor_sens = pd.DataFrame(sens_rows)
        anchor_sens_path = os.path.join(out_dir, "override_anchor_sensitivity.csv")
        write_csv(anchor_sens, anchor_sens_path)

    # ---------- Audit JSON ----------
    audit = {
        "rows": int(len(out)),
        "ev_basis": f"{ev_col} (discounted basis preferred)" if ev_col == "EV_disc" else "EV_cum (fallback)",
        "cap_p": float(cap_p),
        "cap_hits": int(cap_hits),
        "threshold": float(threshold),
        "alphas": list(map(float, alphas)),
        "betas":  list(map(float, betas)),
        "theta": float(theta),
        "theta_scale": float(theta_scale),
        "anchors_used": anchors_use,
        "anchors_bands": anchors_bands,
        "evidence": {
            "timeline":   CONFIG["evidence_timeline"],
            "contracts":  CONFIG["evidence_contracts"],
            "indigenous": CONFIG["evidence_indigenous"]
        },
        "disclaimer": CONFIG["disclaimer"],
        "outputs": {
            "per_project_csv": per_project_csv,
            "override_summary_by_alpha": os.path.join(out_dir, "override_summary_by_alpha.csv"),
            "override_contract_grid_summary": os.path.join(out_dir, "override_contract_grid_summary.csv"),
            "anchor_sensitivity_csv": anchor_sens_path
        }
    }
    with open(os.path.join(out_dir, "override_run_audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    # Console peek
    print("\n=== Override summary by α ===")
    print(over_sum.to_string(index=False))
    print("\n=== Grid summary (α × β) — head ===")
    print(grid_sum.head(12).to_string(index=False))
    print(f"\nPer-project results: {per_project_csv}")
    print(f"Summaries in: {out_dir}")
    if anchor_sens_path:
        print(f"Anchor sensitivity table: {anchor_sens_path}")

# ==================== CLI ====================
# Remove argparse setup
# def parse_args():
#     p = argparse.ArgumentParser(description="Government Override + Contracted Demand Runner — v2")
#     p.add_argument("--in_csv", help="Input cohort CSV")
#     p.add_argument("--out_dir", help="Output directory")
#     p.add_argument("--alphas", help="Comma-separated α list, e.g., 0.25,0.5,0.75,1.0")
#     p.add_argument("--betas", help="Comma-separated β list, e.g., 0.0,0.25,0.5,0.75,1.0")
#     p.add_argument("--theta", type=float, help="Interaction knob (−1..+1)")
#     p.add_argument("--theta_scale", type=float, help="Small scalar for logit bump")
#     p.add_argument("--cap_p", type=float, help="Probability cap (default 0.90)")
#     p.add_argument("--threshold", type=float, help="Crosser threshold (default 0.50)")
#     p.add_argument("--anchors_use", choices=["conservative","central","optimistic"], help="Band for anchors")
#     p.add_argument("--write_anchor_sensitivity", type=int, choices=[0,1], help="Write anchor sensitivity CSV (1/0)")
#     return p.parse_args()

# def _parse_list(val):
#     return [float(x) for x in str(val).split(",") if str(x).strip()]

if __name__ == "__main__":
    # args = parse_args() # Removed argparse
    # overlay CLI args into CONFIG # Removed argparse
    # if args.in_csv:     CONFIG["in_csv"] = args.in_csv
    # if args.out_dir:    CONFIG["out_dir"] = args.out_dir
    # if args.alphas:     CONFIG["alphas"] = _parse_list(args.alphas)
    # if args.betas:      CONFIG["betas"]  = _parse_list(args.betas)
    # if args.theta is not None:        CONFIG["theta"] = float(args.theta)
    # if args.theta_scale is not None:  CONFIG["theta_scale"] = float(args.theta_scale)
    # if args.cap_p is not None:        CONFIG["cap_p"] = float(args.cap_p)
    # if args.threshold is not None:    CONFIG["threshold"] = float(args.threshold)
    # if args.anchors_use:              CONFIG["anchors_use"] = args.anchors_use
    # if args.write_anchor_sensitivity is not None:
    #     CONFIG["write_anchor_sensitivity"] = bool(args.write_anchor_sensitivity)

    # Use default values from CONFIG directly or set explicitly here
    run_override_contract(
        in_csv=CONFIG["in_csv"],
        out_dir=CONFIG["out_dir"],
        alphas=CONFIG["alphas"],
        betas=CONFIG["betas"],
        theta=CONFIG["theta"],
        theta_scale=CONFIG["theta_scale"],
        cap_p=CONFIG["cap_p"],
        threshold=CONFIG["threshold"],
        anchors_use=CONFIG["anchors_use"],
        anchors_bands=CONFIG["anchors_bands"],
        write_anchor_sensitivity=CONFIG["write_anchor_sensitivity"],
    )