#!/usr/bin/env python3
# Energy Nation - Chart Generator (MVP)
# Matplotlib only, one plot per figure, no explicit colors.
# Saves 1100px-wide PNGs and JSON sidecars with metadata.

import json
import math
import hashlib
import os
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ---------- Defaults (env-overridable) ----------
CSV_PATH_DEFAULT = os.environ.get("EN_BRIEFS_CSV", "energy_nation_flat_dataset_briefs_ready.csv")
OUTPUT_DIR_DEFAULT = os.environ.get("EN_CHARTS_DIR", "charts")
os.makedirs(OUTPUT_DIR_DEFAULT, exist_ok=True)


# ---------- Helpers ----------

def slugify(text: str) -> str:
    """Lowercase, replace whitespace with underscores, remove non-alphanum/underscore."""
    if text is None:
        return "untitled"
    s = text.lower().strip()
    out = []
    for ch in s:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        elif ch.isspace() or ch in "-/|:,.;+&":
            out.append("_")
        # else drop
    # collapse multiple underscores
    slug = "".join(out)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "untitled"


def short_hash(obj) -> str:
    """Stable short hash for dicts/filters in filenames."""
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:6]


def today_stamp() -> str:
    return datetime.now().strftime("%Y%m%d")


def ensure_columns(df: pd.DataFrame, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {missing}")


def apply_filters(df: pd.DataFrame, filt: dict | None) -> pd.DataFrame:
    if not filt:
        return df
    out = df.copy()
    for k, v in filt.items():
        if k not in out.columns:
            # ignore unknown filters
            continue
        if isinstance(v, (list, tuple, set)):
            out = out[out[k].isin(list(v))]
        else:
            out = out[out[k] == v]
    return out


def scenario_to_cols(scenario: str) -> dict:
    """Map scenario name to delta_EV and probability column roots. Fallback handled by caller."""
    if scenario == "base":
        return {"ev": "EV_disc_base", "p": "blended_prob", "delta_ev": None, "delta_p": None}
    if scenario == "mpo":
        return {"ev": "EV_mpo", "p": "blended_prob_mpo", "delta_ev": "delta_EV_mpo", "delta_p": "delta_p_mpo"}
    if scenario == "indigenous":
        return {"ev": "EV_indigenous", "p": "blended_prob_indigenous", "delta_ev": "delta_EV_indigenous", "delta_p": "delta_p_indigenous"}
    if scenario == "combined":
        return {"ev": "EV_combined", "p": "blended_prob_combined", "delta_ev": "delta_EV_combined", "delta_p": "delta_p_combined"}
    if scenario.startswith("override_"):
        a = scenario.split("_", 1)[1]
        return {
            "ev": f"EV_disc_override_{a}",
            "p": f"blended_prob_override_{a}",
            "delta_ev": f"delta_EV_override_{a}",
            "delta_p": f"delta_p_override_{a}",
        }
    raise ValueError(f"Unknown scenario: {scenario}")


def base_ev_column(df: pd.DataFrame) -> tuple[str, str | None]:
    """Return base EV column to use and any fallback note."""
    if "EV_disc_base" in df.columns and not df["EV_disc_base"].isna().all():
        return "EV_disc_base", None
    if "EV_base" in df.columns:
        return "EV_base", "Used EV_base because EV_disc_base not found or not populated."
    raise ValueError("Neither EV_disc_base nor EV_base found.")


def format_num(x: float, decimals: int = 1) -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return "NA"
    return f"{x:,.{decimals}f}"


def save_with_sidecar(fig, out_path: str, sidecar: dict, width_px: int = 1100, dpi: int = 110):
    """Save figure with width in px and write sidecar JSON. No explicit colors; one chart per fig."""
    # set size in inches from pixels
    w_in = width_px / dpi
    size = fig.get_size_inches()
    h_in = size[1] * (w_in / size[0] if size[0] else 1.0)
    fig.set_size_inches(w_in, h_in)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    with open(out_path.replace(".png", ".json"), "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2, ensure_ascii=False)


# ---------- Chart Implementations (MVP) ----------

def chart_topn_delta_ev_bar(
    df: pd.DataFrame,
    scenario: str,
    N: int = 10,
    filt: dict | None = None,
    topic: str = "portfolio_uplift",
    output_dir: str = OUTPUT_DIR_DEFAULT,
    csv_path: str = CSV_PATH_DEFAULT,
):
    """Top-N projects by delta_EV for a scenario."""
    cols = scenario_to_cols(scenario)
    delta_col = cols["delta_ev"]
    fallback_note = None
    if (delta_col is None) or (delta_col not in df.columns) or df[delta_col].isna().all():
        if "delta_EV_combined" in df.columns:
            delta_col = "delta_EV_combined"
            fallback_note = f"delta_EV for '{scenario}' not found; fell back to 'combined'."
        else:
            raise ValueError(f"No delta_EV column available for scenario '{scenario}' and no fallback.")

    base_col, base_note = base_ev_column(df)
    work = apply_filters(df, filt).copy()
    ensure_columns(work, ["Unique ID", "project", delta_col])

    # drop NAs, sort desc
    work = work.dropna(subset=[delta_col])
    work = work.sort_values(by=delta_col, ascending=False).head(N)

    # Metrics
    mean_val = float(work[delta_col].mean()) if not work.empty else float("nan")
    median_val = float(work[delta_col].median()) if not work.empty else float("nan")
    total_val = float(work[delta_col].sum()) if not work.empty else float("nan")

    # Plot
    fig, ax = plt.subplots()
    ax.barh(work["project"], work[delta_col])  # no explicit color
    ax.invert_yaxis()  # largest at top
    ax.set_xlabel("Delta EV (scenario vs base)")
    ax.set_title(f"Top-{min(N, len(work))} Delta EV — {scenario}")

    # Caption & metadata
    filters_text = ", ".join([f"{k}={v}" for k, v in (filt or {}).items()]) or "all projects"
    caption = (
        f"Top-{min(N, len(work))} EV uplift contributors under {scenario} for {filters_text}. "
        f"Mean Delta EV = {format_num(mean_val)}, median = {format_num(median_val)}; "
        f"total uplift = {format_num(total_val)}. Counterfactual results."
    )
    if fallback_note:
        caption += f" Note: {fallback_note}"
    if base_note:
        caption += f" Note: {base_note}"

    # Sidecar JSON
    sidecar = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "csv_path": csv_path,
        "scenario": scenario,
        "filters": filt or {},
        "top_n": int(N),
        "metrics": {
            "mean_delta_ev": mean_val,
            "median_delta_ev": median_val,
            "total_delta_ev": total_val,
        },
        "ids": list(map(int, work["Unique ID"].tolist())),
        "fallback_notes": [n for n in [fallback_note, base_note] if n],
        "caption": caption,
    }

    # Filename
    base = f"{today_stamp()}_{slugify(topic)}_{slugify(scenario)}_topnbar"
    if filt and len(json.dumps(filt)) > 40:
        base += f"_filtered_{short_hash(filt)}"
    out_path = os.path.join(output_dir, f"{base}.png")

    save_with_sidecar(fig, out_path, sidecar)
    plt.close(fig)
    return out_path, caption


def chart_hist_delta_ev(
    df: pd.DataFrame,
    scenario: str,
    bins: int = 30,
    filt: dict | None = None,
    topic: str = "distribution_uplift",
    output_dir: str = OUTPUT_DIR_DEFAULT,
    csv_path: str = CSV_PATH_DEFAULT,
):
    """Histogram of delta_EV for a scenario with P1-P99 clipping; record unclipped min/max in sidecar."""
    cols = scenario_to_cols(scenario)
    delta_col = cols["delta_ev"]
    fallback_note = None
    if (delta_col is None) or (delta_col not in df.columns) or df[delta_col].isna().all():
        if "delta_EV_combined" in df.columns:
            delta_col = "delta_EV_combined"
            fallback_note = f"delta_EV for '{scenario}' not found; fell back to 'combined'."
        else:
            raise ValueError(f"No delta_EV column available for scenario '{scenario}' and no fallback.")

    work = apply_filters(df, filt).copy()
    ensure_columns(work, [delta_col])
    series = work[delta_col].dropna()

    if series.empty:
        raise ValueError("No data after filters for histogram.")

    # Record unclipped extrema
    unclipped_min = float(series.min())
    unclipped_max = float(series.max())

    # Clip to P1-P99
    lo, hi = np.percentile(series, [1, 99])
    clipped = series.clip(lower=lo, upper=hi)

    mean_val = float(series.mean())
    median_val = float(series.median())

    # Plot
    fig, ax = plt.subplots()
    ax.hist(clipped, bins=bins)  # no explicit color
    ax.set_xlabel("Delta EV (scenario vs base)")
    ax.set_ylabel("Count")
    ax.set_title(f"Delta EV Distribution — {scenario}")

    # Caption & metadata
    filters_text = ", ".join([f"{k}={v}" for k, v in (filt or {}).items()]) or "all projects"
    caption = (
        f"Distribution of Delta EV under {scenario} for {filters_text}. "
        f"Mean = {format_num(mean_val)}, median = {format_num(median_val)}. "
        f"Values clipped to P1-P99 to limit outlier distortion."
    )
    if fallback_note:
        caption += f" Note: {fallback_note}"

    sidecar = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "csv_path": csv_path,
        "scenario": scenario,
        "filters": filt or {},
        "metrics": {
            "mean_delta_ev": mean_val,
            "median_delta_ev": median_val,
            "unclipped_min": unclipped_min,
            "unclipped_max": unclipped_max,
            "clip_bounds": {"p1": float(lo), "p99": float(hi)},
        },
        "fallback_notes": [fallback_note] if fallback_note else [],
        "caption": caption,
    }

    base = f"{today_stamp()}_{slugify(topic)}_{slugify(scenario)}_hist"
    if filt and len(json.dumps(filt)) > 40:
        base += f"_filtered_{short_hash(filt)}"
    out_path = os.path.join(output_dir, f"{base}.png")

    save_with_sidecar(fig, out_path, sidecar)
    plt.close(fig)
    return out_path, caption


def chart_dumbbell_sideby(
    df: pd.DataFrame,
    scenario: str,
    compare_ids: list[int],
    filt: dict | None = None,
    topic: str = "side_by_side",
    output_dir: str = OUTPUT_DIR_DEFAULT,
    csv_path: str = CSV_PATH_DEFAULT,
):
    """Dumbbell plot for exactly two projects: base EV vs scenario EV."""
    if not isinstance(compare_ids, (list, tuple)) or len(compare_ids) != 2:
        raise ValueError("compare_ids must contain exactly two Unique ID values.")

    cols = scenario_to_cols(scenario)
    ev_col = cols["ev"]
    fallback_note = None
    if (ev_col is None) or (ev_col not in df.columns) or df[ev_col].isna().all():
        if "EV_combined" in df.columns:
            ev_col = "EV_combined"
            fallback_note = f"EV for '{scenario}' not found; fell back to 'combined'."
        else:
            raise ValueError(f"No EV column available for scenario '{scenario}' and no fallback.")

    base_col, base_note = base_ev_column(df)

    work = apply_filters(df, filt).copy()
    work = work[work["Unique ID"].isin(compare_ids)]
    ensure_columns(work, ["Unique ID", "project", base_col, ev_col])

    if len(work) != 2:
        raise ValueError("Exactly two rows must match the provided compare_ids after filters.")

    # Plot
    fig, ax = plt.subplots()
    y_positions = np.arange(2)
    # draw lines between base and scenario values for each project
    base_vals = work[base_col].values.astype(float)
    scen_vals = work[ev_col].values.astype(float)
    for i, (b, s) in enumerate(zip(base_vals, scen_vals)):
        x_vals = [b, s]
        y_vals = [y_positions[i], y_positions[i]]
        ax.plot(x_vals, y_vals, marker="o")  # no explicit color

    ax.set_yticks(y_positions)
    ax.set_yticklabels(work["project"].tolist())
    ax.set_xlabel("EV")
    ax.set_title(f"Base vs {scenario} — Dumbbell")

    filters_text = ", ".join([f"{k}={v}" for k, v in (filt or {}).items()]) or "all projects"
    caption = (
        f"Base EV vs {scenario} EV for two projects ({compare_ids}) under {filters_text}. "
        f"Counterfactual results."
    )
    if fallback_note:
        caption += f" Note: {fallback_note}"
    if base_note:
        caption += f" Note: {base_note}"

    sidecar = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "csv_path": csv_path,
        "scenario": scenario,
        "filters": filt or {},
        "compare_ids": list(map(int, compare_ids)),
        "columns": {"base_ev_col": base_col, "scenario_ev_col": ev_col},
        "fallback_notes": [n for n in [fallback_note, base_note] if n],
        "caption": caption,
    }

    base = f"{today_stamp()}_{slugify(topic)}_{slugify(scenario)}_dumbbell_{compare_ids[0]}_{compare_ids[1]}"
    if filt and len(json.dumps(filt)) > 40:
        base += f"_filtered_{short_hash(filt)}"
    out_path = os.path.join(output_dir, f"{base}.png")

    save_with_sidecar(fig, out_path, sidecar)
    plt.close(fig)
    return out_path, caption


# ---------- Minimal demo runner ----------

def demo_run(csv_path: str = CSV_PATH_DEFAULT, output_dir: str = OUTPUT_DIR_DEFAULT):
    """Run a quick demo of all three MVP charts using default params."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"CSV not found at '{csv_path}'. Upload 'energy_nation_flat_dataset_briefs_ready.csv' "
            "to the current working directory or set EN_BRIEFS_CSV env var."
        )
    df = pd.read_csv(csv_path)

    # choose a scenario with available delta_EV, fallback to 'combined'
    scenarios_try = ["mpo", "combined", "indigenous"]
    chosen = None
    for sc in scenarios_try:
        cols = scenario_to_cols(sc)
        if cols["delta_ev"] in df.columns:
            chosen = sc
            break
    if chosen is None:
        chosen = "combined"

    # 1) Top-N bar
    p1, c1 = chart_topn_delta_ev_bar(df, scenario=chosen, N=10, filt=None, topic="portfolio_uplift", output_dir=output_dir, csv_path=csv_path)

    # 2) Histogram
    p2, c2 = chart_hist_delta_ev(df, scenario=chosen, bins=30, filt=None, topic="distribution_uplift", output_dir=output_dir, csv_path=csv_path)

    # 3) Dumbbell side-by-side: pick any two valid IDs
    ids = df["Unique ID"].dropna().astype(int).unique().tolist()[:2]
    if len(ids) >= 2:
        p3, c3 = chart_dumbbell_sideby(df, scenario=chosen, compare_ids=ids[:2], filt=None, topic="side_by_side", output_dir=output_dir, csv_path=csv_path)
    else:
        p3, c3 = None, "Not enough projects for dumbbell plot."

    return {
        "topn_bar": {"path": p1, "caption": c1},
        "hist": {"path": p2, "caption": c2},
        "dumbbell": {"path": p3, "caption": c3},
    }


if __name__ == "__main__":
    results = demo_run(CSV_PATH_DEFAULT, OUTPUT_DIR_DEFAULT)
    print(json.dumps(results, indent=2))
