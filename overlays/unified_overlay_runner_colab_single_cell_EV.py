# %% [markdown]
# # Unified Overlay Runner — Single Cell (Colab‑Ready) with Reports
#
# Answer these four mini‑questions (the **knobs**), then run this **one cell**.
#
# 1) **Where are your input files?** (paths on Colab, e.g., `/content/...`)
# 2) **When a row has *both* flags (Indigenous + MPO), which policy should apply?**
#    - \"ind_then_cap\" (default): shift/hazard, then cap (recommended)
#    - \"cap_then_ind\": cap first, then shift/hazard
#    - \"priority_ind\": apply only Indigenous overlay
#    - \"priority_mpo\": apply only MPO overlay
# 3) **How strong is Indigenous time compression and hazard boost?**
#    - delta_years = -1.0 compresses start time by one year
#    - hazard_multiplier = 1.10 gently raises approval velocity (risk)
# 4) **What is the MPO cap (years)?** e.g., 2.0
#
# The cell computes Bayes/Cox/Blended probabilities, applies overlays by flags,
# and emits: a unified output CSV, a Markdown summary, segmented CSVs, and PNG charts.

# ==================== KNOBS ====================
CONFIG = {
    "input_xlsx": "/content/mpi_2024_input.xlsx",
    "bayes_lr":   "/content/bayes_lr_regenerated_coefficients_expanded.csv",
    "cox_coefs":  "/content/cox_refit_coefficients_timesplit_expanded.csv",
    "breslow":    "/content/breslow_baseline_survival_2018_2020.csv",
    "out_csv":    "/content/unified_overlay_run.csv",
    "out_md":     "/content/unified_overlay_summary.md",
    "report_dir": "/content/reports",
    "both_policy": "ind_then_cap",
    "delta_years": -1.0,
    "hazard_multiplier": 1.10,
    "mpo_cap_years": 2.0,
    "w": 0.50,
}

import os, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def norm_str(x):
    if pd.isna(x): return "Unknown"
    return str(x).strip()

def compute_p_bayes_row(row, lr_map, provsec_enabled=True, provsec_alpha=1.0):
    feats = ["PRIOR"]
    cle = norm_str(row.get("cleantech"))
    feats.append(f"cleantech_{cle if cle in ['Yes','No'] else 'Unknown'}")
    cq = row.get("_cost_quintile_bayes")
    feats.append(f"cost_quintile_{int(cq) if pd.notna(cq) else 'Unknown'}")
    grp = norm_str(row.get("group"))
    feats.append(f"group_{grp}" if f"group_{grp}" in lr_map else "group_Unknown")
    prov = norm_str(row.get("province"))
    feats.append(f"province_{prov}" if f"province_{prov}" in lr_map else "province_Unknown")
    sec = norm_str(row.get("sector"))
    feats.append(f"sector_{sec}" if f"sector_{sec}" in lr_map else "sector_Unknown")
    y = row.get("start_year")
    try: y = int(y)
    except Exception: y = "Unknown"
    feats.append(f"start_bin_{y}" if f"start_bin_{y}" in lr_map else "start_bin_Unknown")
    ps = f"prov_sec_{prov}_{sec}"
    if provsec_enabled and ps in lr_map: feats.append(ps)
    log_odds = 0.0
    for f in feats:
        v = lr_map.get(f, 1.0)
        if f.startswith("prov_sec_") and provsec_alpha != 1.0: v = v ** provsec_alpha
        try: log_odds += np.log(float(v))
        except Exception: pass
    return 1.0 / (1.0 + np.exp(-log_odds))

def compute_risk_score_row(row, coef_map):
    eta = 0.0
    cle_yes = 1 if norm_str(row.get("cleantech")) == "Yes" else 0
    eta += coef_map.get("cleantech_Yes", 0.0) * cle_yes
    cp = row.get("cost_percentile")
    if pd.notna(cp):
        try: eta += coef_map.get("cost_percentile", 0.0) * float(cp)
        except Exception: pass
    gf = row.get("greenfield_flag")
    if pd.notna(gf):
        try: eta += coef_map.get("greenfield_flag", 0.0) * int(gf)
        except Exception: pass
    foak = row.get("FOAK_flag")
    if pd.notna(foak):
        try: eta += coef_map.get("FOAK_flag", 0.0) * int(foak)
        except Exception: pass
    prov = f"province_{norm_str(row.get('province'))}"
    eta += coef_map.get(prov, 0.0)
    sec = f"sector_{norm_str(row.get('sector'))}"
    eta += coef_map.get(sec, 0.0)
    return float(np.exp(eta))

def p_cox_conditional(t0_years, risk_score, S0_map, S0_T):
    if t0_years >= 5: return 0.0
    t0_use = max(2, int(np.floor(float(t0_years))))
    t0_use = min(t0_use, 4)
    S0_t0 = S0_map.get(t0_use, None)
    if S0_t0 is None or S0_T is None: return np.nan
    return 1.0 - (S0_T / S0_t0) ** risk_score

def knot_from_t0(t0):
    try: t = float(t0)
    except Exception: return np.nan
    t_floor = int(np.floor(t))
    return max(2, min(t_floor, 4))

# RUN
os.makedirs(CONFIG["report_dir"], exist_ok=True)
df = pd.read_excel(CONFIG["input_xlsx"]) if CONFIG["input_xlsx"].lower().endswith((".xlsx",".xls")) else pd.read_csv(CONFIG["input_xlsx"])
bayes_table = pd.read_csv(CONFIG["bayes_lr"])
cox_table   = pd.read_csv(CONFIG["cox_coefs"])
baseline    = pd.read_csv(CONFIG["breslow"])

bayes_lr_map = dict(zip(bayes_table["feature_name"], bayes_table["LR"]))
cox_coef_map = dict(zip(cox_table["covariate"], cox_table["coef"]))
S0_map = dict(zip(baseline["time_years"], baseline["S0_survival"]))
S0_T = float(S0_map.get(5))

ranks = df["project_cost"].astype(float).rank(method="first")
df["_cost_quintile_bayes"] = pd.qcut(ranks, 5, labels=[0,1,2,3,4]).astype("Int64")
df["p_bayes"] = df.apply(lambda r: compute_p_bayes_row(r, bayes_lr_map), axis=1)
df["risk_score"] = df.apply(lambda r: compute_risk_score_row(r, cox_coef_map), axis=1)
w = float(CONFIG["w"])

df["p_cox_engine"] = 1.0 - (S0_T ** df["risk_score"])
df["blended_engine"] = w * df["p_bayes"] + (1.0 - w) * df["p_cox_engine"]

if "indigenous_flag_overlay" not in df.columns: df["indigenous_flag_overlay"] = 0
if "mpo_flag" not in df.columns: df["mpo_flag"] = 0

is_ind = df["indigenous_flag_overlay"].astype(int) == 1
is_mpo = df["mpo_flag"].astype(int) == 1
ind_only =  is_ind & ~is_mpo
mpo_only = ~is_ind &  is_mpo
both     =  is_ind &  is_mpo

df["t0"] = df["reporting_years"].astype(float)
df["t0_adj"] = df["t0"]
df["risk_score_adj"] = df["risk_score"]

def apply_indigenous(mask):
    if CONFIG["delta_years"] != 0:
        df.loc[mask, "t0_adj"] = (df.loc[mask, "t0_adj"] + CONFIG["delta_years"]).clip(lower=0.0)
    if CONFIG["hazard_multiplier"] and CONFIG["hazard_multiplier"] != 1.0:
        df.loc[mask, "risk_score_adj"] = df.loc[mask, "risk_score_adj"] * CONFIG["hazard_multiplier"]

def apply_mpo(mask):
    df.loc[mask, "t0_adj"] = np.minimum(df.loc[mask, "t0_adj"], CONFIG["mpo_cap_years"])

apply_indigenous(ind_only)
apply_mpo(mpo_only)
if CONFIG["both_policy"] == "ind_then_cap":
    apply_indigenous(both); apply_mpo(both)
elif CONFIG["both_policy"] == "cap_then_ind":
    apply_mpo(both); apply_indigenous(both)
elif CONFIG["both_policy"] == "priority_ind":
    apply_indigenous(both)
elif CONFIG["both_policy"] == "priority_mpo":
    apply_mpo(both)

df["overlay_mode"] = "none"
df.loc[ind_only, "overlay_mode"] = "indigenous_only"
df.loc[mpo_only, "overlay_mode"] = "mpo_only"
df.loc[both,     "overlay_mode"] = f"both({CONFIG['both_policy']})"
df["t0_orig"] = df["t0"]
df["delta_t"] = df["t0_adj"] - df["t0_orig"]
df["hazard_mult_applied"] = False
df.loc[is_ind & (CONFIG["hazard_multiplier"] != 1.0), "hazard_mult_applied"] = True

df["knot_before"] = df["t0"].apply(knot_from_t0)
df["knot_after"]  = df["t0_adj"].apply(knot_from_t0)
df["knot_changed"] = (df["knot_before"] != df["knot_after"]).astype(int)

df["p_cox_cond_status"] = [p_cox_conditional(t, r, S0_map, S0_T) for t, r in zip(df["t0"], df["risk_score"])]
df["p_cox_cond_overlay"] = [p_cox_conditional(t, r, S0_map, S0_T) for t, r in zip(df["t0_adj"], df["risk_score_adj"])]
df["delta_p_cox_cond"]   = df["p_cox_cond_overlay"] - df["p_cox_cond_status"]

df["blended_status"]  = w * df["p_bayes"] + (1.0 - w) * df["p_cox_cond_status"]
df["blended_overlay"] = w * df["p_bayes"] + (1.0 - w) * df["p_cox_cond_overlay"]
df["delta_blended"]   = df["blended_overlay"] - df["blended_status"]

df["years_remaining_status"] = (5.0 - df["t0"]).clip(lower=0.25)
df["years_remaining_overlay"] = (5.0 - df["t0_adj"]).clip(lower=0.25)
df["priority_index_status"]  = df["blended_status"]  / df["years_remaining_status"]
df["priority_index_overlay"] = df["blended_overlay"] / df["years_remaining_overlay"]
df["delta_priority_index"]   = df["priority_index_overlay"] - df["priority_index_status"]

# === Expected Value (EV) additions ===
# EV uses blended probabilities and project_cost (already in millions).
df["EV_status"]  = df["blended_status"]  * df["project_cost"].astype(float)
df["EV_overlay"] = df["blended_overlay"] * df["project_cost"].astype(float)
df["delta_EV"]   = df["EV_overlay"] - df["EV_status"]

out_cols = [
    "Unique ID","company","project","province","group","sector",
    "reporting_years","_cost_quintile_bayes","cost_percentile","cleantech",
    "greenfield_flag","FOAK_flag",
    "indigenous_flag_overlay","mpo_flag","overlay_mode",
    "p_bayes","risk_score","risk_score_adj",
    "p_cox_engine","blended_engine",
    "t0_orig","t0_adj","delta_t",
    "knot_before","knot_after","knot_changed",
    "p_cox_cond_status","p_cox_cond_overlay","delta_p_cox_cond",
    "blended_status","blended_overlay","delta_blended",
    "years_remaining_status","years_remaining_overlay",
    "priority_index_status","priority_index_overlay","delta_priority_index",
    "EV_status","EV_overlay","delta_EV"
]
df[out_cols].to_csv(CONFIG["out_csv"], index=False)

summary = {
    "rows": int(len(df)),
    "S0_T": float(S0_T),
    "counts": {
        "none": int((df["overlay_mode"]=="none").sum()),
        "ind_only": int((df["overlay_mode"]=="indigenous_only").sum()),
        "mpo_only": int((df["overlay_mode"]=="mpo_only").sum()),
        "both": int((df["overlay_mode"].str.startswith("both")).sum())
    },
    "delta_p_cox_cond_mean": float(np.nanmean(df["delta_p_cox_cond"])),
    "delta_p_cox_cond_median": float(np.nanmedian(df["delta_p_cox_cond"])),
    "delta_blended_mean": float(np.nanmean(df["delta_blended"])),
    "delta_blended_median": float(np.nanmedian(df["delta_blended"])),
    "delta_EV_mean": float(np.nanmean(df["delta_EV"])),
    "delta_EV_median": float(np.nanmedian(df["delta_EV"])),
    "knot_changes": int((df["knot_changed"]==1).sum()),
    "hazard_multiplier_used": float(CONFIG["hazard_multiplier"]),
    "delta_years_used": float(CONFIG["delta_years"]),
    "mpo_cap_years_used": float(CONFIG["mpo_cap_years"]),
    "both_policy_used": str(CONFIG["both_policy"]),
    "blend_w_used": float(CONFIG["w"])
}

os.makedirs(os.path.dirname(CONFIG["out_md"]), exist_ok=True)
with open(CONFIG["out_md"], "w", encoding="utf-8") as f:
    f.write("# Unified Overlay Runner — Summary\n\n")
    f.write(f"- Rows: **{summary['rows']}**\n\n")
    f.write(f"- S0(5): **{summary['S0_T']:.6f}**\n\n")
    f.write(f"- Mode counts: none={summary['counts']['none']}, ind_only={summary['counts']['ind_only']}, mpo_only={summary['counts']['mpo_only']}, both={summary['counts']['both']}\n\n")
    f.write(f"- Knot changes: **{summary['knot_changes']}**\n\n")
    f.write(f"- Params: Δyears={summary['delta_years_used']}, hazard_mult={summary['hazard_multiplier_used']}, mpo_cap={summary['mpo_cap_years_used']}, policy={summary['both_policy_used']}, w={summary['blend_w_used']}\n\n")
    f.write("**Δ p_cox (conditional, overlay − status):**\n\n")
    f.write(f"- Mean: **{summary['delta_p_cox_cond_mean']:.6f}**\n\n")
    f.write(f"- Median: **{summary['delta_p_cox_cond_median']:.6f}**\n\n")
    f.write(f"**Δ blended (w = {w:.2f}):**\n\n")
    f.write(f"- Mean: **{summary['delta_blended_mean']:.6f}**\n\n")
    f.write(f"- Median: **{summary['delta_blended_median']:.6f}**\n")

    f"**Δ EV (millions):**\n\n")
    f"- Mean: **{summary['delta_EV_mean']:.6f}**\n\n")
    f"- Median: **{summary['delta_EV_median']:.6f}**\n")

plt.figure(figsize=(10,6))
plt.hist(df["delta_blended"], bins=40, density=True)
plt.title("Distribution of Δ Blended Probability (overlay − status)")
plt.xlabel("Δ blended")
plt.ylabel("Density")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CONFIG["report_dir"], "hist_delta_blended.png"), dpi=160)
plt.close()

# EV Δ histogram
plt.figure(figsize=(10,6))
plt.hist(df["delta_EV"], bins=40, density=True)
plt.title("Distribution of Δ Expected Value (overlay − status) — Millions")
plt.xlabel("Δ EV (Millions)")
plt.ylabel("Density")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CONFIG["report_dir"], "hist_delta_EV.png"), dpi=160)
plt.close()

seg = df.groupby(["province","group"], dropna=False).agg(
    rows=("Unique ID","count"),
    mean_delta_blended=("delta_blended","mean"),
    median_delta_blended=("delta_blended","median"),
    pct_positive_blended=("delta_blended", lambda x: (x>0).mean()),
    mean_delta_EV=("delta_EV","mean"),
    median_delta_EV=("delta_EV","median"),
    pct_positive_EV=("delta_EV", lambda x: (x>0).mean())
).reset_index()
seg.to_csv(os.path.join(CONFIG["report_dir"], "segment_province_group.csv"), index=False)

# Bar charts per province for Δ blended
for prov in seg["province"].dropna().unique().tolist():
    sub = seg[seg["province"] == prov]
    plt.figure(figsize=(12, max(3, 0.5 * len(sub.index))))
    plt.bar(sub["group"].astype(str), sub["mean_delta_blended"].values)
    plt.title(f"Δ blended by group in {prov}")
    plt.ylabel("Mean Δ blended")
    plt.xlabel("Group")
    plt.xticks(rotation=45, ha="right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(CONFIG["report_dir"], f"bars_blended_{prov}.png"), dpi=160)
    plt.close()

# Bar charts per province for Δ EV
for prov in seg["province"].dropna().unique().tolist():
    sub = seg[seg["province"] == prov]
    plt.figure(figsize=(12, max(3, 0.5 * len(sub.index))))
    plt.bar(sub["group"].astype(str), sub["mean_delta_EV"].values)
    plt.title(f"Δ EV by group in {prov} (Millions)")
    plt.ylabel("Mean Δ EV (Millions)")
    plt.xlabel("Group")
    plt.xticks(rotation=45, ha="right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(CONFIG["report_dir"], f"bars_EV_{prov}.png"), dpi=160)
    plt.close()

with open(os.path.join(CONFIG["report_dir"], "run_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print(json.dumps(summary, indent=2))
print(f"Saved CSV: {CONFIG['out_csv']}")
print(f"Saved Markdown: {CONFIG['out_md']}")
print(f"Saved reports to: {CONFIG['report_dir']}")
