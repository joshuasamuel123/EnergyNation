# build_flat_dataset.py
import pandas as pd
import numpy as np
from typing import List

THRESHOLD = 0.50
ALPHAS = [0.25, 0.50, 0.75, 1.00]

def pivot_unified_overlay_to_wide(df_uo: pd.DataFrame) -> pd.DataFrame:
    """
    Coerce unified_overlay_flat_merged_from_runner into a wide table with per-scenario columns.
    Handles:
      (1) Already-wide tables (columns contain 'mpo'/'ind'/'combined') -> passthrough
      (2) Long tables with scenario_key + metrics -> pivot to wide
    """
    wide_cols = [c for c in df_uo.columns if any(k in c.lower() for k in ["mpo", "ind", "combined"])]
    if wide_cols:
        return df_uo.copy()

    if "scenario_key" in df_uo.columns:
        key = "Unique ID" if "Unique ID" in df_uo.columns else ("unique_id" if "unique_id" in df_uo.columns else None)
        if key is None:
            raise ValueError("Could not find Unique ID column in unified overlay file.")
        metrics = ["blended_overlay", "delta_blended", "EV_overlay", "EV_disc_overlay"]
        present = [m for m in metrics if m in df_uo.columns]
        if not present:
            return df_uo.copy()

        pivots = {}
        for m in present:
            tmp = df_uo[[key, "scenario_key", m]].pivot(index=key, columns="scenario_key", values=m)
            tmp.columns = [f"{m}_{scen}" for scen in tmp.columns]
            pivots[m] = tmp

        base_cols = [c for c in df_uo.columns if c not in ["scenario_key"] + metrics]
        base = df_uo[base_cols].drop_duplicates(subset=[key]).set_index(key)
        out = base
        for t in pivots.values():
            out = out.join(t, how="left")
        return out.reset_index()

    return df_uo.copy()

def pick_col(df: pd.DataFrame, base: str) -> str:
    """Find a canonical column even if pandas added suffixes (_x/_y/.1)."""
    for c in (base, f"{base}_x", f"{base}_y", f"{base}.1"):
        if c in df.columns: return c
    for c in df.columns:
        if c.startswith(base): return c
    return ""

def build_flat_dataset(
    path_override_full: str,
    path_unified_overlay_flat: str,
    out_csv: str = "energy_nation_flat_dataset.csv",
    alphas: List[float] = ALPHAS,
    threshold: float = THRESHOLD
) -> str:
    # Load inputs
    df_over = pd.read_csv(path_override_full)
    df_uo = pd.read_csv(path_unified_overlay_flat)

    # Identify ID column
    id_col = "Unique ID" if "Unique ID" in df_over.columns else ("unique_id" if "unique_id" in df_over.columns else None)
    if id_col is None:
        raise ValueError("No Unique ID column found in override_contract_overlay_full.csv")

    # Prepare unified overlay wide table
    df_uo_wide = pivot_unified_overlay_to_wide(df_uo)

    # --- Base fields from override (richest metadata)
    base_keep = []
    for c in [id_col, "project", "company", "province", "sector", "group", "start_year", "end_year",
              "reporting_years", "project_cost", "cost_band", "FOAK", "cleantech",
              "p_bayes", "p_cox", "blended_prob",
              "priority_index", "urgency_scale_(0-1)", "power_ranking",
              "EV_disc", "EV_cum", "EV_disc_base", "EV_base"]:
        if c in df_over.columns:
            base_keep.append(c)
    base = df_over[base_keep].drop_duplicates(subset=[id_col])

    # Normalize base EV columns
    if "EV_disc_base" not in base.columns and "EV_disc" in base.columns:
        base["EV_disc_base"] = df_over.groupby(id_col)["EV_disc"].first()
    if "EV_base" not in base.columns and "EV_cum" in base.columns:
        base["EV_base"] = df_over.groupby(id_col)["EV_cum"].first()

    # --- Override (α) scenario columns
    over_keep = [id_col]
    for a in alphas:
        for c in [f"blended_{a}", f"Δp_{a}", f"EV_disc_{a}", f"EV_cum_{a}"]:
            if c in df_over.columns:
                over_keep.append(c)
    df_over_keep = df_over[over_keep].groupby(id_col).first().reset_index()

    # Merge to form initial flat
    flat = base.merge(df_uo_wide, on=id_col, how="left").merge(df_over_keep, on=id_col, how="left")

    # Canonicalize the base blended probability (handle _x/_y suffixes)
    base_prob_col = pick_col(flat, "blended_prob")
    if base_prob_col and base_prob_col != "blended_prob":
        flat["blended_prob"] = flat[base_prob_col]

    # --- MPO / Indigenous / Combined columns from unified overlay wide
    scen_map = {
        "mpo": ["mpo_only", "mpo", "MPO"],
        "indigenous": ["mpi_ind", "ind_only", "indigenous"],
        "combined": ["combined", "ind_mpo", "both"]
    }

    def find_metric(prefixes, needle):
        for col in flat.columns:
            lc = col.lower()
            if (needle in lc) and any(p in lc for p in prefixes):
                return col
        return ""

    for scen, keys in scen_map.items():
        # blended prob
        col_b = find_metric(keys, "blended")
        if not col_b:
            # try 'blended_prob_<scen>'
            for col in flat.columns:
                if col.lower().startswith("blended_prob_") and any(k in col.lower() for k in keys):
                    col_b = col; break
        if col_b:
            flat[f"blended_prob_{scen}"] = flat[col_b]

        # delta prob
        col_dp = find_metric(keys, "delta_blended")
        if col_dp:
            flat[f"delta_p_{scen}"] = flat[col_dp]

        # EV / EV_disc
        col_e = find_metric(keys, "ev_overlay")
        if col_e:
            flat[f"EV_{scen}"] = flat[col_e]
        col_ed = find_metric(keys, "ev_disc_overlay")
        if col_ed:
            flat[f"EV_disc_{scen}"] = flat[col_ed]

    # --- Derive override deltas and EVs vs base
    if "blended_prob" in flat.columns:
        for a in alphas:
            bcol = f"blended_{a}"
            if bcol in flat.columns:
                flat[f"blended_prob_override_{a}"] = flat[bcol]
                flat[f"delta_p_override_{a}"] = flat[bcol] - flat["blended_prob"]

            # EV (prefer discounted)
            if f"EV_disc_{a}" in flat.columns and "EV_disc_base" in flat.columns:
                flat[f"EV_disc_override_{a}"] = flat[f"EV_disc_{a}"]
                flat[f"delta_EV_override_{a}"] = flat[f"EV_disc_{a}"] - flat["EV_disc_base"]
            elif f"EV_cum_{a}" in flat.columns and "EV_base" in flat.columns:
                flat[f"EV_override_{a}"] = flat[f"EV_cum_{a}"]
                flat[f"delta_EV_override_{a}"] = flat[f"EV_cum_{a}"] - flat["EV_base"]

    # --- Crosser / dropout flags
    def _flag_crosser(base, scen): return ((base < threshold) & (scen >= threshold)).astype(int)
    def _flag_dropout(base, scen): return ((base >= threshold) & (scen < threshold)).astype(int)

    if "blended_prob" in flat.columns:
        for scen in ["mpo", "indigenous", "combined"]:
            s = flat.get(f"blended_prob_{scen}")
            if s is not None:
                flat[f"crosser_{scen}"] = _flag_crosser(flat["blended_prob"], s)
                flat[f"dropout_{scen}"] = _flag_dropout(flat["blended_prob"], s)

        for a in alphas:
            ocol = flat.get(f"blended_prob_override_{a}")
            if ocol is not None:
                flat[f"crosser_override_{a}"] = _flag_crosser(flat["blended_prob"], ocol)
                flat[f"dropout_override_{a}"] = _flag_dropout(flat["blended_prob"], ocol)

    # Write output
    flat.to_csv(out_csv, index=False)
    return out_csv

out = build_flat_dataset(
    "/content/override_contract_overlay_full.csv",
    "/content/unified_overlay_flat_merged_from_runner.csv",
    out_csv="/content/energy_nation_flat_dataset.csv"
)
print("Wrote:", out)

