#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Overlay Runner
----------------------
Applies Indigenous and MPO approval-cap overlays (ind_only, mpo_only, combined)
to a pre-construction MPI cohort and recomputes probabilities and expected value.

Key features:
- All knobs at the top (easy to tweak).
- Integrates EV_disc column if present.
- Standardizes years_in_pipeline from t0_orig as: 2024 - t0_orig + 1.
- Removes ownership flag handling per latest direction.
- MPO overlay = hard cap on federal approvals window.
- Indigenous overlay = time compression + hazard multiplier for flagged projects.
- Combined overlay runs overlays in a chosen sequence (default: MPO → Indigenous).
- Generates results CSV + grouped summary CSVs + a Markdown report.
- Robust to missing optional columns; emits clear warnings instead of failing.

Assumptions (kept explicit):
- Base probability column is PROB_COL (default 'blended'). Values in [0,1].
- Project cost column is COST_COL (default 'project_cost') in *millions of CAD*.
- Optional discounted cost column 'EV_disc' represents a discounted project cost
  (present value); when present we compute EV_disc = p * EV_disc.
- If explicit approvals duration is not provided, we infer from t0_orig:
  approvals_years ≈ years_in_pipeline = REPORT_YEAR - t0_orig + 1.
- Time compression impacts probabilities via a simple odds scaling:
  odds' = odds * (HAZARD_MULTIPLIER ** (-delta_years)),
  where negative delta_years (faster reviews) increases odds when multiplier > 1.
"""

import argparse
import os
import sys
import math
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
from datetime import datetime

# =========================
# ======== KNOBS ==========
# =========================
# Paths
INPUT_CSV = "/content/mpi_2024_ev_dev_combined_5y.csv"  # <-- set to your input file
OUTPUT_DIR = "overlay_outputs"               # results and reports will be saved here

# Which scenario to run: 'ind_only' | 'mpo_only' | 'combined' | 'all'
SCENARIO = "all"

# Columns (override here if your headings differ)
ID_COL = "unique_id"
PROB_COL = "blended_prob"          # base probability (0..1)
COST_COL = "project_cost"     # in millions CAD
DISCOUNTED_COST_COL = "EV_disc"  # OPTIONAL: discounted project cost (PV). If present, we compute EV_disc = p * EV_disc
PROVINCE_COL = "province"
SECTOR_COL = "sector"
GROUP_COL = "group"
FOAK_COL = "FOAK"             # 1/0 or True/False
CLEANTECH_COL = "cleantech"   # 1/0 or True/False
COST_BAND_COL = "cost_band"   # categorical
T0_ORIG_COL = "t0_orig"       # a YEAR like 2019, 2020, etc. Used to compute years_in_pipeline
APPROVAL_YEARS_COL = "reporting_years"  # OPTIONAL explicit approvals duration; falls back to years_in_pipeline if missing

# Indigenous flag detection: the first present column among this list will be used.
INDIGENOUS_FLAG_CANDIDATES = [
    "indigenous_flag", "indigenous", "has_indigenous_partner", "ind"
]

# Year anchor for years_in_pipeline
REPORT_YEAR = 2024

# MPO overlay params
APPROVAL_CAP_YEARS = 2  # hard cap on approvals for the MPO overlay

# Indigenous overlay params
TIME_COMPRESSION_YEARS = -1.0  # negative means "faster by 1 year"
HAZARD_MULTIPLIER = 1.10       # >1 means faster reviews increase survival odds per year compressed

# Combined overlay sequence; valid tokens are 'mpo' and 'ind'
COMBINED_ORDER: List[str] = ["mpo", "ind"]

# Output formatting
FLOAT_DECIMALS = 6

# =========================
# ======== LOGIC ==========
# =========================

def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)

def info(msg: str):
    print(f"[INFO] {msg}")

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def coerce_bool_or_int(series: pd.Series) -> pd.Series:
    """Coerce heterogenous 1/0/True/False/yes/no to clean {0,1} ints."""
    if series.dtype == bool:
        return series.astype(int)
    # Lowercase strings like 'true', 'yes', etc.
    def _coerce(v):
        if pd.isna(v):
            return 0
        if isinstance(v, (int, np.integer)):
            return int(v != 0)
        if isinstance(v, (float, np.floating)):
            return int(v != 0.0)
        s = str(v).strip().lower()
        if s in ("1", "true", "t", "y", "yes"):
            return 1
        if s in ("0", "false", "f", "n", "no"):
            return 0
        # Default to 0 but warn once
        return 0
    return series.map(_coerce).astype(int)

def clip_prob(p: pd.Series) -> pd.Series:
    return p.clip(lower=0.0, upper=1.0)

def odds_from_prob(p: np.ndarray) -> np.ndarray:
    # Add epsilon to avoid division by zero
    eps = 1e-12
    return p / (1.0 - p + eps)

def prob_from_odds(o: np.ndarray) -> np.ndarray:
    return o / (1.0 + o)

def apply_time_shift_probability(base_p: pd.Series,
                                 years_delta: pd.Series,
                                 hazard_multiplier: float) -> pd.Series:
    """
    Apply an odds-scaling to represent time compression/expansion effect.
    If years_delta is negative (faster), odds are multiplied by hazard_multiplier**(-years_delta) > 1.
    If years_delta is positive (slower), odds are reduced accordingly.
    """
    p = base_p.values.astype(float)
    y = years_delta.values.astype(float)
    odds = odds_from_prob(p)
    scale = np.power(hazard_multiplier, -y)  # note the negative sign
    new_odds = odds * scale
    new_p = prob_from_odds(new_odds)
    return pd.Series(new_p, index=base_p.index).pipe(clip_prob)

def ensure_column(df: pd.DataFrame, col: str, default=np.nan) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = default
    return df

def years_in_pipeline_from_t0(df: pd.DataFrame, t0_col: str, report_year: int) -> pd.Series:
    """
    per latest instruction:
      years_in_pipeline = REPORT_YEAR - t0_orig + 1
    """
    if t0_col not in df.columns:
        warn(f"'{t0_col}' missing; cannot compute years_in_pipeline. Will default to NaN.")
        return pd.Series([np.nan]*len(df), index=df.index)

    years = (report_year - pd.to_numeric(df[t0_col], errors="coerce") + 1)
    return years

def infer_approvals_years(df: pd.DataFrame) -> pd.Series:
    """
    Prefer APPROVAL_YEARS_COL if present; otherwise fall back to years_in_pipeline.
    """
    if APPROVAL_YEARS_COL in df.columns:
        vals = pd.to_numeric(df[APPROVAL_YEARS_COL], errors="coerce")
        if vals.isna().all():
            warn(f"'{APPROVAL_YEARS_COL}' present but all NA; falling back to derived years_in_pipeline.")
            yip = years_in_pipeline_from_t0(df, T0_ORIG_COL, REPORT_YEAR)
            return yip
        return vals
    else:
        yip = years_in_pipeline_from_t0(df, T0_ORIG_COL, REPORT_YEAR)
        return yip

def detect_indigenous_flag(df: pd.DataFrame) -> Optional[str]:
    for cand in INDIGENOUS_FLAG_CANDIDATES:
        if cand in df.columns:
            return cand
    return None

def compute_ev(prob: pd.Series, cost_millions: pd.Series) -> pd.Series:
    """
    EV (in millions CAD) = probability * cost (in millions CAD).
    """
    return (prob.astype(float) * pd.to_numeric(cost_millions, errors="coerce").fillna(0.0))

def scenario_labels(s: str) -> Dict[str, str]:
    if s == "ind_only":
        return {"name": "ind_only", "pretty": "Indigenous Only"}
    if s == "mpo_only":
        return {"name": "mpo_only", "pretty": "MPO Cap Only"}
    if s == "combined":
        return {"name": "mpi_ind", "pretty": "Combined (MPO → Indigenous)"}
    return {"name": s, "pretty": s}

def run_mpo_overlay(df: pd.DataFrame) -> pd.Series:
    """
    Universal overlay: cap approvals at APPROVAL_CAP_YEARS, then convert time delta to probability shift.
    """
    approvals = infer_approvals_years(df)
    cap = APPROVAL_CAP_YEARS
    new_years = np.minimum(approvals.fillna(np.inf).values, cap)
    years_delta = pd.Series(new_years - approvals.values, index=df.index)  # <= 0
    # Apply odds scaling to base probability
    p0 = pd.to_numeric(df[PROB_COL], errors="coerce").fillna(0.0).clip(0, 1)
    p1 = apply_time_shift_probability(p0, years_delta, HAZARD_MULTIPLIER)
    return p1

def run_indigenous_overlay(df: pd.DataFrame) -> pd.Series:
    """
    Selective overlay: apply time compression + hazard multiplier only to Indigenous-flagged rows.
    Others get base probability unchanged.
    """
    p0 = pd.to_numeric(df[PROB_COL], errors="coerce").fillna(0.0).clip(0, 1)
    flag_col = detect_indigenous_flag(df)
    if flag_col is None:
        warn("No Indigenous flag column found; ind_only overlay will behave like no-op.")
        return p0

    flags = coerce_bool_or_int(df[flag_col])
    years_delta = pd.Series([0.0]*len(df), index=df.index)
    # Apply only to flagged rows
    years_delta.loc[flags == 1] = TIME_COMPRESSION_YEARS
    p1 = apply_time_shift_probability(p0, years_delta, HAZARD_MULTIPLIER)
    return p1

def run_combined_overlay(df: pd.DataFrame) -> pd.Series:
    """
    Apply overlays in sequence given by COMBINED_ORDER.
    """
    p = pd.to_numeric(df[PROB_COL], errors="coerce").fillna(0.0).clip(0, 1).copy()
    tmp_df = df.copy()
    tmp_df["_work_p"] = p.values
    for step in COMBINED_ORDER:
        if step.lower() == "mpo":
            # run MPO using current _work_p as base
            tmp_df[PROB_COL] = tmp_df["_work_p"]
            tmp_df["_work_p"] = run_mpo_overlay(tmp_df)
        elif step.lower() == "ind":
            tmp_df[PROB_COL] = tmp_df["_work_p"]
            tmp_df["_work_p"] = run_indigenous_overlay(tmp_df)
        else:
            warn(f"Unknown combined step '{step}' — skipping.")
    return tmp_df["_work_p"].clip(0, 1)

def attach_standard_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Derive years_in_pipeline from t0_orig.
    - Ensure grouping columns exist (fill NA for grouping).
    """
    df = df.copy()
    df["years_in_pipeline"] = years_in_pipeline_from_t0(df, T0_ORIG_COL, REPORT_YEAR)

    # Ensure group-by columns exist
    for col in [PROVINCE_COL, SECTOR_COL, GROUP_COL, FOAK_COL, CLEANTECH_COL, COST_BAND_COL]:
        if col not in df.columns:
            warn(f"Grouping column '{col}' missing; filling with NA.")
            df[col] = np.nan

    # Clean FOAK / cleantech to 0/1 if possible
    try:
        df[FOAK_COL] = coerce_bool_or_int(df[FOAK_COL])
    except Exception:
        pass
    try:
        df[CLEANTECH_COL] = coerce_bool_or_int(df[CLEANTECH_COL])
    except Exception:
        pass

    return df

def compute_overlay_outputs(df: pd.DataFrame, p_overlay: pd.Series, scenario_key: str) -> pd.DataFrame:
    """
    Build a result dataframe with overlay prob/EV deltas and crossover flags.
    """
    out = df.copy()
    out = ensure_column(out, ID_COL, default=np.arange(len(out)))
    out = ensure_column(out, COST_COL, default=0.0)
    out = ensure_column(out, PROB_COL, default=0.0)

    p0 = pd.to_numeric(out[PROB_COL], errors="coerce").fillna(0.0).clip(0, 1)
    c0 = pd.to_numeric(out[COST_COL], errors="coerce").fillna(0.0)

    # Base EVs
    out["EV_base"] = compute_ev(p0, c0)

    # Discounted EVs if EV_disc column present
    has_disc = (DISCOUNTED_COST_COL in out.columns)
    if has_disc:
        disc_cost = pd.to_numeric(out[DISCOUNTED_COST_COL], errors="coerce").fillna(0.0)
        out["EV_disc_base"] = compute_ev(p0, disc_cost)

    # Overlay
    out["blended_overlay"] = p_overlay.clip(0, 1)
    out["delta_blended"] = out["blended_overlay"] - p0

    out["EV_overlay"] = compute_ev(out["blended_overlay"], c0)
    out["delta_EV"] = out["EV_overlay"] - out["EV_base"]

    if has_disc:
        out["EV_disc_overlay"] = compute_ev(out["blended_overlay"], disc_cost)
        out["delta_EV_disc"] = out["EV_disc_overlay"] - out.get("EV_disc_base", 0.0)

    # Crossover cohorts
    out["cross_over_to_favorite"] = ((p0 < 0.5) & (out["blended_overlay"] >= 0.5)).astype(int)
    out["cross_out_to_underdog"] = ((p0 >= 0.5) & (out["blended_overlay"] < 0.5)).astype(int)

    # Label scenario
    meta = scenario_labels(scenario_key)
    out["scenario_key"] = meta["name"]
    out["scenario_label"] = meta["pretty"]

    # Tidy floats
    float_cols = out.select_dtypes(include=[float]).columns
    out[float_cols] = out[float_cols].astype(float).round(FLOAT_DECIMALS)

    return out

def group_summaries(df: pd.DataFrame, scenario_key: str) -> Dict[str, pd.DataFrame]:
    """
    Produce grouped summaries by province, sector, group, FOAK, cleantech, cost_band, plus overall.
    Summaries include counts, mean delta_blended, sums of delta_EV and delta_EV_disc, and crossover counts.
    """
    groups = {
        "province": [PROVINCE_COL],
        "sector": [SECTOR_COL],
        "group": [GROUP_COL],
        "foak": [FOAK_COL],
        "cleantech": [CLEANTECH_COL],
        "cost_band": [COST_BAND_COL],
        "overall": []  # special case
    }

    metrics = ["delta_blended", "delta_EV", "cross_over_to_favorite", "cross_out_to_underdog"]
    if "delta_EV_disc" in df.columns:
        metrics.append("delta_EV_disc")

    summaries = {}

    for name, cols in groups.items():
        if len(cols) == 0:
            # overall
            agg = {
                "unique_id": ("unique_id", "count") if "unique_id" in df.columns else ("scenario_key", "count"),
                "delta_blended": ("delta_blended", "mean"),
                "delta_EV": ("delta_EV", "sum"),
                "cross_over_to_favorite": ("cross_over_to_favorite", "sum"),
                "cross_out_to_underdog": ("cross_out_to_underdog", "sum"),
            }
            if "delta_EV_disc" in df.columns:
                agg["delta_EV_disc"] = ("delta_EV_disc", "sum")

            s = df.agg({k: v[1] for k, v in agg.items() if v[1] != "count"})
            # Count for overall
            total_n = len(df)
            row = {
                "n": total_n,
                "mean_delta_blended": float(s["delta_blended"]) if "delta_blended" in s else np.nan,
                "sum_delta_EV": float(s["delta_EV"]) if "delta_EV" in s else np.nan,
                "sum_delta_EV_disc": float(s.get("delta_EV_disc", np.nan)),
                "cross_over_to_favorite": int(df["cross_over_to_favorite"].sum()),
                "cross_out_to_underdog": int(df["cross_out_to_underdog"].sum()),
                "scenario_key": scenario_labels(scenario_key)["name"],
            }
            summaries[name] = pd.DataFrame([row])
        else:
            g = df.groupby(cols, dropna=False)
            agg_dict = {
                "n": (ID_COL, "count") if ID_COL in df.columns else ("scenario_key", "count"),
                "mean_delta_blended": ("delta_blended", "mean"),
                "sum_delta_EV": ("delta_EV", "sum"),
                "cross_over_to_favorite": ("cross_over_to_favorite", "sum"),
                "cross_out_to_underdog": ("cross_out_to_underdog", "sum"),
            }
            if "delta_EV_disc" in df.columns:
                agg_dict["sum_delta_EV_disc"] = ("delta_EV_disc", "sum")

            s = g.agg(**agg_dict).reset_index()
            s["scenario_key"] = scenario_labels(scenario_key)["name"]
            # Round floats
            for col in ["mean_delta_blended", "sum_delta_EV", "sum_delta_EV_disc"]:
                if col in s.columns:
                    s[col] = pd.to_numeric(s[col], errors="coerce").round(FLOAT_DECIMALS)
            summaries[name] = s

    return summaries

def write_reports(result_df: pd.DataFrame,
                  summaries: Dict[str, pd.DataFrame],
                  out_dir: str,
                  scenario_key: str):
    """Write CSVs and a concise Markdown report."""
    ensure_dir(out_dir)
    meta = scenario_labels(scenario_key)
    tag = meta["name"]

    # Results CSV
    results_path = os.path.join(out_dir, f"{tag}_overlay_results.csv")
    result_df.to_csv(results_path, index=False)
    info(f"Wrote results: {results_path}")

    # Grouped summaries
    for k, v in summaries.items():
        path = os.path.join(out_dir, f"{tag}_summary_{k}.csv")
        v.to_csv(path, index=False)
        info(f"Wrote summary: {path}")

    # Markdown roll-up
    md_path = os.path.join(out_dir, f"{tag}_report.md")
    total_ev_uplift = float(result_df["delta_EV"].sum())
    total_ev_disc_uplift = float(result_df["delta_EV_disc"].sum()) if "delta_EV_disc" in result_df.columns else None
    mean_delta_blended = float(result_df["delta_blended"].mean())
    crossovers = int(result_df["cross_over_to_favorite"].sum())
    crossouts = int(result_df["cross_out_to_underdog"].sum())
    n = len(result_df)

    lines = []
    lines.append(f"# {meta['pretty']} — Overlay Report")
    lines.append("")
    lines.append(f"- **Scenario key:** `{meta['name']}`")
    lines.append(f"- **Projects:** {n}")
    lines.append(f"- **Mean Δ blended probability:** {mean_delta_blended:.6f} (pp)")
    lines.append(f"- **Σ Δ EV (millions CAD):** {total_ev_uplift:.6f}")
    if total_ev_disc_uplift is not None:
        lines.append(f"- **Σ Δ EV_disc (millions CAD, PV):** {total_ev_disc_uplift:.6f}")
    lines.append(f"- **Crossovers (→ ≥0.5):** {crossovers}")
    lines.append(f"- **Cross-outs (→ <0.5):** {crossouts}")
    lines.append("")
    lines.append("## Notes")
    lines.append("- EV is computed as probability × project_cost (millions).")
    lines.append("- If present, EV_disc uses the discounted project cost column (EV_disc) as the cost base.")
    lines.append("- years_in_pipeline is standardized as `2024 - t0_orig + 1`.")
    lines.append("- MPO cap limits approvals to the configured cap and applies an odds scaling based on HAZARD_MULTIPLIER.")
    lines.append("- Indigenous overlay applies the configured time compression and hazard multiplier only to Indigenous-flagged rows.")
    lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    info(f"Wrote report: {md_path}")

def run_one(df_in: pd.DataFrame, scenario_key: str) -> pd.DataFrame:
    """
    Execute one scenario, returning the per-project result dataframe (ready to write).
    """
    meta = scenario_labels(scenario_key)

    if scenario_key == "ind_only":
        p1 = run_indigenous_overlay(df_in)
    elif scenario_key == "mpo_only":
        p1 = run_mpo_overlay(df_in)
    elif scenario_key == "combined":
        p1 = run_combined_overlay(df_in)
    else:
        raise ValueError(f"Unknown scenario '{scenario_key}'")

    res = compute_overlay_outputs(df_in, p1, scenario_key)
    return res

def main():
    global REPORT_YEAR, APPROVAL_CAP_YEARS, TIME_COMPRESSION_YEARS, HAZARD_MULTIPLIER
    # Remove argparse setup
    # parser = argparse.ArgumentParser(description="Unified Overlay Runner")
    # parser.add_argument("--input", type=str, default=INPUT_CSV, help="Path to input CSV")
    # parser.add_argument("--outdir", type=str, default=OUTPUT_DIR, help="Directory for outputs")
    # parser.add_argument("--scenario", type=str, default=SCENARIO,
    #                     choices=["ind_only", "mpo_only", "combined", "all"],
    #                     help="Which scenario to run")
    # parser.add_argument("--report_year", type=int, default=REPORT_YEAR, help="Anchor year (default 2024)")
    # parser.add_argument("--cap", type=float, default=APPROVAL_CAP_YEARS, help="MPO approvals cap (years)")
    # parser.add_argument("--time_compress", type=float, default=TIME_COMPRESSION_YEARS,
    #                     help="Indigenous overlay time compression (years; negative = faster)")
    # parser.add_argument("--hazard_mult", type=float, default=HAZARD_MULTIPLIER,
    #                     help="Hazard multiplier per year of compression (odds scaling)")
    # args = parser.parse_args()

    # Update globals from CLI (so report text matches) - now use default values or set directly
    # REPORT_YEAR = args.report_year
    # APPROVAL_CAP_YEARS = args.cap
    # TIME_COMPRESSION_YEARS = args.time_compress
    # HAZARD_MULTIPLIER = args.hazard_mult

    ensure_dir(OUTPUT_DIR)

    # Load input
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    # Standard fields
    df = attach_standard_fields(df)

    # Sanity checks
    missing_crit = [c for c in [PROB_COL, COST_COL] if c not in df.columns]
    if missing_crit:
        raise ValueError(f"Missing required column(s): {missing_crit}. "
                         f"Expected at least probability '{PROB_COL}' and cost '{COST_COL}'.")

    # Run scenarios
    scenarios_to_run = ["ind_only", "mpo_only", "combined"] if SCENARIO == "all" else [SCENARIO]

    for scen in scenarios_to_run:
        info(f"Running scenario: {scen}")
        res = run_one(df, scen)
        sums = group_summaries(res, scen)
        write_reports(res, sums, OUTPUT_DIR, scen)

    info("Done.")

if __name__ == "__main__":
    main()