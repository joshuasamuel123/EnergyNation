# -*- coding: utf-8 -*-
"""
Patched MPI Risk Engine (v03 → v03a)
- Adds province–sector LR shrinkage knob for Bayes (to prevent swamping)
- Points Cox to expanded, audit-friendly coefficients (incl. Greenfield/FOAK, cost_percentile)
- Supports cleantech naming variants (cleantech_flag vs cleantech_Yes dummy)
- Exposes blend weight as a knob
"""

import os
import pandas as pd
import numpy as np

# =========================
# PATHS & CONSTANTS
# =========================
# Default to /content (Colab-style). Override with environment variables if needed.
BAYES_COEFF_PATH = os.getenv("BAYES_COEFF_PATH", "/content/bayes_lr_regenerated_coefficients_expanded.csv")
COX_COEFF_PATH   = os.getenv("COX_COEFF_PATH",   "/content/cox_refit_coefficients_timesplit_expanded.csv")
INPUT_XLSX       = os.getenv("INPUT_XLSX",       "/content/mpi_2024_input.xlsx")
OUT_CSV          = os.getenv("OUT_CSV",          "/content/mpi_2024_scored.csv")
OUT_XLSX         = os.getenv("OUT_XLSX",         "/content/mpi_2024_scored.xlsx")

# Survival baseline at 5 years (confirmed)
S0_T = float(os.getenv("S0_T", "0.545332"))

# ======== CONFIG KNOBS ========
# Bayes: control province–sector interaction strength
PROVSEC_ENABLED = (os.getenv("PROVSEC_ENABLED", "true").lower() == "true")
PROVSEC_ALPHA   = float(os.getenv("PROVSEC_ALPHA", "0.6"))  # 1.0 = no shrink; 0.6–0.8 recommended

# Blending: weight on Bayes
BLEND_BAYES_W   = float(os.getenv("BLEND_BAYES_W", "0.50"))
# ==============================


def norm_str(x):
    if pd.isna(x):
        return "Unknown"
    s = str(x).strip()
    return s if s else "Unknown"


def start_bin_from_year(y):
    try:
        y = int(y)
    except Exception:
        return "Unknown"
    return str(y) if 2018 <= y <= 2024 else "Unknown"


def _load_maps():
    bayes_table = pd.read_csv(BAYES_COEFF_PATH)
    cox_table   = pd.read_csv(COX_COEFF_PATH)
    bayes_lr_map = dict(zip(bayes_table["feature_name"], bayes_table["LR"]))

    # Normalize cox covariate column name
    if "covariate" not in cox_table.columns and "index" in cox_table.columns:
        cox_table = cox_table.rename(columns={"index": "covariate"})
    cox_coef_map = dict(zip(cox_table["covariate"], cox_table["coef"]))
    return bayes_lr_map, cox_coef_map


def _cost_quintile_for_cox(p):
    if pd.isna(p):
        return None
    v = float(p)
    return int(min(0.9999, max(0.0, v)) * 5)


def compute_p_bayes(row, bayes_lr_map):
    """Naive Bayes log-odds with optional α-shrinkage on province–sector interaction."""
    feats = ["PRIOR"]

    # cleantech
    cle = norm_str(row.get("cleantech"))
    feats.append(f"cleantech_{cle if cle in ['Yes','No'] else 'Unknown'}")

    # cost quintile (dataset-relative qcut assigned upstream)
    cq = row.get("_cost_quintile_bayes")
    feats.append(f"cost_quintile_{int(cq) if pd.notna(cq) else 'Unknown'}")

    # group
    grp = norm_str(row.get("group"))
    feats.append(f"group_{grp}" if f"group_{grp}" in bayes_lr_map else "group_Unknown")

    # province & sector
    prov = norm_str(row.get("province"))
    feats.append(f"province_{prov}" if f"province_{prov}" in bayes_lr_map else "province_Unknown")

    sec = norm_str(row.get("sector"))
    feats.append(f"sector_{sec}" if f"sector_{sec}" in bayes_lr_map else "sector_Unknown")

    # start year bin
    sb = start_bin_from_year(row.get("start_year"))
    feats.append(f"start_bin_{sb}" if f"start_bin_{sb}" in bayes_lr_map else "start_bin_Unknown")

    # province–sector interaction (with shrinkage)
    ps = f"prov_sec_{prov}_{sec}"
    if PROVSEC_ENABLED and ps in bayes_lr_map:
        feats.append(ps)

    # flags: greenfield / FOAK
    gf = row.get("greenfield_flag")
    if pd.notna(gf):
        try:
            feats.append(f"greenfield_flag_{int(gf)}")
        except Exception:
            pass
    foak = row.get("FOAK_flag")
    if pd.notna(foak):
        try:
            feats.append(f"FOAK_flag_{int(foak)}")
        except Exception:
            pass

    # sum log LRs with optional α on prov_sec_*
    log_odds = 0.0
    for f in feats:
        v = bayes_lr_map.get(f, 1.0)
        if f.startswith("prov_sec_"):
            if not PROVSEC_ENABLED:
                v = 1.0
            elif PROVSEC_ALPHA != 1.0:
                v = v ** PROVSEC_ALPHA
        log_odds += np.log(v)

    p = 1.0 / (1.0 + np.exp(-log_odds))
    return float(p)


def compute_risk_score(row, cox_coef_map):
    """
    Cox risk = exp(eta); eta = sum(beta_j * x_j)

    - Supports either 'cleantech_Yes' dummy (preferred) or legacy 'cleantech_flag'
    - Uses continuous 'cost_percentile' when present (from re-fit)
    - Includes 'greenfield_flag' and 'FOAK_flag' from re-fit
    - Province/Sector terms are taken literally (e.g., 'province_BC', 'sector_Mining')
    """
    eta = 0.0

    # cleantech: Yes dummy preferred; fallback to cleantech_flag
    cle = norm_str(row.get("cleantech"))
    cle_yes = 1 if cle == "Yes" else 0
    if "cleantech_Yes" in cox_coef_map:
        eta += cox_coef_map.get("cleantech_Yes", 0.0) * cle_yes
    else:
        eta += cox_coef_map.get("cleantech_flag", 0.0) * cle_yes

    # cost: prefer continuous cost_percentile
    cp = row.get("cost_percentile")
    if pd.notna(cp):
        try:
            eta += cox_coef_map.get("cost_percentile", 0.0) * float(cp)
        except Exception:
            pass
    else:
        # backward compatibility: discretize
        try:
            v = float(row.get("cost_percentile"))
            cq = int(min(0.9999, max(0.0, v)) * 5)
            eta += cox_coef_map.get("cost_quintile", 0.0) * cq
        except Exception:
            pass

    # province & sector
    prov = norm_str(row.get("province"))
    sec  = norm_str(row.get("sector"))
    eta += cox_coef_map.get(f"province_{prov}", 0.0)
    eta += cox_coef_map.get(f"sector_{sec}",   0.0)

    # Greenfield / FOAK flags
    gf = row.get("greenfield_flag")
    if pd.notna(gf):
        try:
            eta += cox_coef_map.get("greenfield_flag", 0.0) * int(gf)
        except Exception:
            pass

    foak = row.get("FOAK_flag")
    if pd.notna(foak):
        try:
            eta += cox_coef_map.get("FOAK_flag", 0.0) * int(foak)
        except Exception:
            pass

    return float(np.exp(eta))


def run():
    # Load inputs
    df = pd.read_excel(INPUT_XLSX)

    # Load coefficient maps
    bayes_lr_map, cox_coef_map = _load_maps()

    # === Bayes cost quintile via qcut over dataset ===
    ranks = df["project_cost"].astype(float).rank(method="first")
    df["_cost_quintile_bayes"] = pd.qcut(ranks, 5, labels=[0, 1, 2, 3, 4]).astype("Int64")

    # --- p_bayes ---
    df["p_bayes"] = df.apply(lambda r: compute_p_bayes(r, bayes_lr_map), axis=1)

    # --- Cox ---
    df["risk_score"] = df.apply(lambda r: compute_risk_score(r, cox_coef_map), axis=1)
    df["years_remaining"] = (5.0 - df["reporting_years"]).clip(lower=0.25)
    df["p_cox"] = 1 - (S0_T ** df["risk_score"])

    # --- Blend ---
    w = BLEND_BAYES_W
    df["blended_prob"] = w * df["p_bayes"] + (1.0 - w) * df["p_cox"]
    df["priority_index"] = df["blended_prob"] / df["years_remaining"]

    # Rescale within filtered dataset for urgency
    pi_min = df["priority_index"].min()
    pi_max = df["priority_index"].max()
    if pi_max > pi_min:
        df["urgency_scale_(0-1)"] = (df["priority_index"] - pi_min) / (pi_max - pi_min)
    else:
        df["urgency_scale_(0-1)"] = 0.0

    df["power_ranking"] = 0.60 * df["blended_prob"] + 0.40 * df["urgency_scale_(0-1)"]

    # SAVE
    df.to_csv(OUT_CSV, index=False)
    df.to_excel(OUT_XLSX, index=False)

    # Meta for audit
    print(f"[META] PROVSEC_ENABLED={PROVSEC_ENABLED}, PROVSEC_ALPHA={PROVSEC_ALPHA}")
    print(f"[META] COX_COEFF_PATH={COX_COEFF_PATH}")
    print(f"[META] BAYES_COEFF_PATH={BAYES_COEFF_PATH}")
    print(f"[META] BLEND_BAYES_W={BLEND_BAYES_W}")
    print("Wrote:", OUT_CSV)
    print("Wrote:", OUT_XLSX)
    print("Rows:", len(df))
    return df


if __name__ == "__main__":
    _ = run()
