import pandas as pd
from pathlib import Path

# --- INPUTS ---
flat_path = "/content/energy_nation_flat_dataset.csv"          # your current flat
override_path = "/content/override_contract_overlay_full.csv"  # rich EV source (disc/cum)
out_path = "/content/energy_nation_flat_dataset_briefs_ready.csv"

# --- LOAD ---
flat = pd.read_csv(flat_path)
over = pd.read_csv(override_path)

# --- 1) Canonicalize common columns (drop _x/_y ambiguity) ---
def canonize(df, name):
    for c in (name, f"{name}_x", f"{name}_y", f"{name}.1"):
        if c in df.columns:
            df[name] = df[c]
            return
    # fallback: first that startswith
    for c in df.columns:
        if c.startswith(name):
            df[name] = df[c]
            return

for base in ["Unique ID","project","company","province","sector","group",
             "start_year","end_year","reporting_years","project_cost",
             "p_bayes","p_cox","blended_prob","priority_index","urgency_scale_(0-1)","power_ranking"]:
    canonize(flat, base)

# --- 2) Join EV bases from override file (prefer EV_disc; else EV_cum) ---
id_col = "Unique ID" if "Unique ID" in over.columns else "unique_id"
ev_base = over[[id_col]].drop_duplicates().copy()
if "EV_disc" in over.columns:
    ev_base["EV_disc_base"] = over.groupby(id_col)["EV_disc"].first()
if "EV_cum" in over.columns:
    ev_base["EV_base"] = over.groupby(id_col)["EV_cum"].first()

flat = flat.merge(ev_base, left_on="Unique ID", right_on=id_col, how="left")
if id_col != "Unique ID":
    flat.drop(columns=[id_col], errors="ignore", inplace=True)

# --- Helper to compute EV from a prob column (uses EV_disc_base if present else EV_base) ---
def ev_from_prob(df, prob_col):
    if "EV_disc_base" in df.columns and df["EV_disc_base"].notna().any():
        # infer PV-per-prob success from base (avoid divide by zero)
        pv_per_prob = df["EV_disc_base"] / df["blended_prob"].clip(lower=1e-9)
        return pv_per_prob * df[prob_col]
    elif "EV_base" in df.columns:
        pv_per_prob = df["EV_base"] / df["blended_prob"].clip(lower=1e-9)
        return pv_per_prob * df[prob_col]
    else:
        return pd.Series([pd.NA]*len(df))

# --- 3) EV for MPO / Indigenous / Combined + ΔEV ---
for scen in ["mpo","indigenous","combined"]:
    prob_col = f"blended_prob_{scen}"
    if prob_col in flat.columns:
        flat[f"EV_{scen}"] = ev_from_prob(flat, prob_col)
        base_ev = flat["EV_disc_base"] if "EV_disc_base" in flat.columns and flat["EV_disc_base"].notna().any() else flat.get("EV_base")
        if base_ev is not None:
            flat[f"delta_EV_{scen}"] = flat[f"EV_{scen}"] - base_ev

# --- 4) EV for override α + ΔEV ---
ALPHAS = [0.25, 0.5, 0.75, 1.0]
for a in ALPHAS:
    prob_col = f"blended_prob_override_{a}"
    if prob_col in flat.columns:
        col_ev_disc = f"EV_disc_override_{a}"
        flat[col_ev_disc] = ev_from_prob(flat, prob_col)
        base_ev = flat["EV_disc_base"] if "EV_disc_base" in flat.columns and flat["EV_disc_base"].notna().any() else flat.get("EV_base")
        if base_ev is not None:
            flat[f"delta_EV_override_{a}"] = flat[col_ev_disc] - base_ev

# --- 5) Optional: final tidy of columns (put key fields first) ---
first_cols = [
    "Unique ID","project","company","province","sector","group",
    "start_year","end_year","reporting_years","project_cost",
    "p_bayes","p_cox","blended_prob","priority_index","urgency_scale_(0-1)","power_ranking",
    "EV_base","EV_disc_base",
    "blended_prob_mpo","delta_p_mpo","EV_mpo","delta_EV_mpo",
    "blended_prob_indigenous","delta_p_indigenous","EV_indigenous","delta_EV_indigenous",
    "blended_prob_combined","delta_p_combined","EV_combined","delta_EV_combined",
    *[f"blended_prob_override_{a}" for a in ALPHAS],
    *[f"delta_p_override_{a}" for a in ALPHAS],
    *[f"EV_disc_override_{a}" for a in ALPHAS],
    *[f"delta_EV_override_{a}" for a in ALPHAS],
    "crosser_mpo","crosser_indigenous","crosser_combined",
    *[f"crosser_override_{a}" for a in ALPHAS],
    "dropout_mpo","dropout_indigenous","dropout_combined",
    *[f"dropout_override_{a}" for a in ALPHAS],
]
# keep existing order for the rest
ordered = [c for c in first_cols if c in flat.columns] + [c for c in flat.columns if c not in first_cols]
flat = flat[ordered]

# --- SAVE ---
flat.to_csv(out_path, index=False)
print("Wrote:", out_path)
