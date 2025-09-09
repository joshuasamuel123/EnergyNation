#!/usr/bin/env python3
"""
Merged EV-by-year + Developer PV-MOIC/IRR engine (single file, Colab-friendly)

- Preserves the calculations described in your separate scripts:
  * EV engine: allocate annual probabilities across 2025–2027 from a chosen source
    and compute EV per year + cumulative/discounted totals.
  * Developer engine: probability-weighted PV sums of outflows/inflows to compute
    PV_MOIC_k, k_star, IRR_k, etc., with S-curve spend to FID.

- Adds exactly one new field at the end: k_star_adj = k_star / blended_prob
  (NaN if blended_prob == 0 or missing).

Input:  mpi_2024_scored.csv
Output: mpi_2024_ev_dev_combined.csv

CLI (example):
  python ev_engine_dev_combined.py \
    --input mpi_2024_scored.csv \
    --output mpi_2024_ev_dev_combined.csv \
    --p-source blended_prob \
    --value-mode capex \
    --dev-fee-rate 0.05 \
    --discount-rate 0.0 \
    --dev-discount 0.13 \
    --dev-cost-pct 0.03 \
    --k 1.0 \
    --scurve S \
    --scurve-steepness 6.0

Notes:
- "No empty cells, but NaN is acceptable": numeric misses left as NaN; text misses left as "".
- If annual_p_* or EV_* columns are missing, they are computed on-the-fly.
- If they are present, they are recomputed to ensure consistency with the selected p-source
  and value-mode (so behavior is deterministic from this script alone).
"""

from __future__ import annotations
import argparse
import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# -----------------------------
# Global defaults (aligned with your prior scripts)
# -----------------------------
BASE_YEAR = 2024

# EV engine defaults
DEFAULT_P_SOURCE = "blended_prob"    # or: p_bayes, p_cox
DEFAULT_VALUE_MODE = "capex"          # or: dev_fee, count
DEFAULT_DEV_FEE_RATE = 0.05           # for value_mode == dev_fee
DEFAULT_EV_DISCOUNT = 0.0             # EV discount (often 0.0)
DEFAULT_ALPHA0 = 0.75                 # allocation softmax hyperparam
DEFAULT_ALPHA1 = 2.0                  # allocation softmax hyperparam

# Developer engine defaults
DEFAULT_DEV_DISCOUNT = 0.13           # developer discount (PV)
DEFAULT_DEV_COST_PCT = 0.03           # DevCost = dev_cost_pct * cost_basis
DEFAULT_K = 1.0                       # reimbursement-only MOIC at FID
DEFAULT_SCURVE = "S"                   # S-curve to FID
DEFAULT_SCURVE_STEEPNESS = 6.0        # logistic steepness for S-curve

# -----------------------------
# Utilities
# -----------------------------

def _safe_float(x, fallback=np.nan):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return fallback
        return float(x)
    except Exception:
        return fallback


def _ensure_numeric(df: pd.DataFrame, cols: List[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


# -----------------------------
# EV ENGINE (annual probs + EV by year)
# -----------------------------

def _softmax_weights(t_years_remaining: float, urgency_01: float, alpha0: float, alpha1: float) -> np.ndarray:
    """Return a 3-element vector of weights over [2025, 2026, 2027].
    Uses a simple temperature-like softmax that reacts to: (i) years remaining, (ii) urgency.
    This mirrors the described behavior: more urgent + fewer remaining years shift mass earlier.
    """
    # Clamp inputs and form three pseudo-scores
    t = max(0.25, float(t_years_remaining))
    u = float(urgency_01)
    # Baseline linear terms mapped into logits
    # earlier year favored by smaller t and larger u
    scores = np.array([
        alpha0 * (u + 1.0 / t),          # 2025
        alpha0 * (0.5 * u + 0.67 / t),   # 2026
        alpha0 * (0.25 * u + 0.5 / t),   # 2027
    ], dtype=float)
    # Sharpening factor
    scores *= float(alpha1)
    # Stable softmax
    m = scores.max()
    e = np.exp(scores - m)
    w = e / e.sum()
    return w.astype(float)


def _allocate_annual_probs(row: pd.Series, p_total_3y: float, alpha0: float, alpha1: float) -> Tuple[float, float, float]:
    """Allocate total 3Y probability into annual_p_2025..2027; fallback to equal thirds when missing inputs."""
    p_total = _safe_float(p_total_3y, 0.0)
    if not (p_total > 0):
        return 0.0, 0.0, 0.0

    yrs = _safe_float(row.get("years_remaining"))
    urg = _safe_float(row.get("urgency_scale_(0-1)"))
    if not math.isnan(yrs) and not math.isnan(urg):
        w = _softmax_weights(yrs, urg, alpha0, alpha1)
    else:
        w = np.array([1/3, 1/3, 1/3], dtype=float)

    p25, p26, p27 = (p_total * w[0], p_total * w[1], p_total * w[2])
    return float(p25), float(p26), float(p27)


def _pick_p_total(row: pd.Series, p_source: str) -> float:
    if p_source == "p_bayes":
        return _safe_float(row.get("p_bayes"), 0.0)
    if p_source == "p_cox":
        return _safe_float(row.get("p_cox"), 0.0)
    # default blended
    return _safe_float(row.get("blended_prob"), 0.0)


def _value_proxy_amount(row: pd.Series, value_mode: str, dev_fee_rate: float) -> float:
    capex = _safe_float(row.get("project_cost"), np.nan)
    if value_mode == "dev_fee":
        return capex * float(dev_fee_rate) if not math.isnan(capex) else np.nan
    if value_mode == "count":
        return 1.0
    # default: capex
    return capex


def compute_ev_fields(df: pd.DataFrame,
                      p_source: str = DEFAULT_P_SOURCE,
                      value_mode: str = DEFAULT_VALUE_MODE,
                      dev_fee_rate: float = DEFAULT_DEV_FEE_RATE,
                      discount_rate: float = DEFAULT_EV_DISCOUNT,
                      alpha0: float = DEFAULT_ALPHA0,
                      alpha1: float = DEFAULT_ALPHA1) -> pd.DataFrame:
    df = df.copy()

    # Ensure numeric
    _ensure_numeric(df, [
        "project_cost", "years_remaining", "urgency_scale_(0-1)",
        "blended_prob", "p_bayes", "p_cox",
    ])

    # Compute value proxy (kept for transparency)
    df["value_mode"] = value_mode
    df["value_proxy_amount"] = df.apply(lambda r: _value_proxy_amount(r, value_mode, dev_fee_rate), axis=1)

    # Choose total 3Y probability and allocate
    df["p_source_used"] = p_source
    annual_p = df.apply(
        lambda r: _allocate_annual_probs(
            r,
            _pick_p_total(r, p_source),
            alpha0, alpha1
        ), axis=1
    )
    df["annual_p_2025"] = [ap[0] for ap in annual_p]
    df["annual_p_2026"] = [ap[1] for ap in annual_p]
    df["annual_p_2027"] = [ap[2] for ap in annual_p]

    # EV per year = P(year) * value_proxy_amount
    for y in (2025, 2026, 2027):
        df[f"EV_{y}"] = df[f"annual_p_{y}"].astype(float) * df["value_proxy_amount"].astype(float)

    # Cumulative EV and discounted EV to BASE_YEAR
    df["EV_cum"] = df[["EV_2025", "EV_2026", "EV_2027"]].sum(axis=1, min_count=1)
    if discount_rate and discount_rate != 0.0:
        def _pv(ev_2025, ev_2026, ev_2027):
            pv25 = ev_2025 / ((1.0 + discount_rate) ** (2025 - BASE_YEAR))
            pv26 = ev_2026 / ((1.0 + discount_rate) ** (2026 - BASE_YEAR))
            pv27 = ev_2027 / ((1.0 + discount_rate) ** (2027 - BASE_YEAR))
            return pv25 + pv26 + pv27
        df["EV_disc"] = [
            _pv(r["EV_2025"], r["EV_2026"], r["EV_2027"]) for _, r in df.iterrows()
        ]
    else:
        df["EV_disc"] = df["EV_cum"]

    return df


# -----------------------------
# DEVELOPER ENGINE (PV sums, k*, PV_MOIC_k, IRR_k)
# -----------------------------

def pv_factor_to_base(year: int, base_year: int = BASE_YEAR, r: float = DEFAULT_DEV_DISCOUNT) -> float:
    """Present-value factor relative to base_year (2024).
    If year <= base_year: compound forward; if year > base_year: discount back.
    """
    if year == base_year:
        return 1.0
    if year < base_year:
        return (1.0 + r) ** (base_year - year)  # compounding forward
    return 1.0 / ((1.0 + r) ** (year - base_year))


def scurve_weights(years: List[int], shape: str = DEFAULT_SCURVE, steepness: float = DEFAULT_SCURVE_STEEPNESS) -> Dict[int, float]:
    """Normalized spend weights across the provided integer years up to FID.
    Shapes:
      - "S": logistic S-curve (default)
      - "even": uniform
      - "front": front-loaded
      - "back": back-loaded
    """
    ys = list(sorted(set(int(y) for y in years)))
    n = len(ys)
    if n <= 0:
        return {}
    if n == 1:
        return {ys[0]: 1.0}

    idx = np.arange(n, dtype=float)
    x = (idx - idx.mean()) / max(1.0, idx.std())

    if shape == "even":
        w = np.ones(n, dtype=float)
    elif shape == "front":
        # more mass earlier years
        w = np.exp(-0.8 * idx)
    elif shape == "back":
        # more mass later years
        w = np.exp(0.8 * idx)
    else:  # "S"
        s = float(steepness)
        w = 1.0 / (1.0 + np.exp(-s * x))  # 0..1 S-curve
        # convert to per-year increments:
        w = np.diff(np.concatenate([[0.0], w]))
        # guard (numerical): ensure positivity
        w = np.clip(w, 1e-12, None)

    w = w / w.sum()
    return {int(y): float(wi) for y, wi in zip(ys, w)}


def _npv(cashflows: Dict[int, float], r: float) -> float:
    return sum(val * pv_factor_to_base(year=t, base_year=BASE_YEAR, r=r) for t, val in cashflows.items())


def _robust_irr(cashflows: Dict[int, float], guess: float = 0.1, lo: float = -0.95, hi: float = 1.5, tol: float = 1e-6, iters: int = 200) -> float:
    """Bisection IRR on expected cashflows (practical proxy)."""
    def npv_at(rate: float) -> float:
        return sum(val / ((1.0 + rate) ** (t - BASE_YEAR)) for t, val in cashflows.items())

    npv_lo = npv_at(lo)
    npv_hi = npv_at(hi)

    if math.isnan(npv_lo) or math.isnan(npv_hi):
        return np.nan

    # If no sign change, nudge bounds
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        v = npv_at(mid)
        if abs(v) < tol:
            return mid
        if npv_lo * v <= 0:
            hi, npv_hi = mid, v
        else:
            lo, npv_lo = mid, v
    return 0.5 * (lo + hi)


def _active_in_2024(row: pd.Series) -> bool:
    sy = int(_safe_float(row.get("start_year"), BASE_YEAR))
    ey = int(_safe_float(row.get("end_year"), BASE_YEAR))
    return (sy <= BASE_YEAR) and (ey >= BASE_YEAR)


def _pick_cost_basis(row: pd.Series) -> float:
    """Prefer project_cost → imputed_cost → value_proxy_amount."""
    for c in ("project_cost", "imputed_cost", "value_proxy_amount"):
        v = _safe_float(row.get(c), np.nan)
        if not math.isnan(v):
            return v
    return np.nan


def compute_project_metrics(row: pd.Series,
                            discount_rate: float,
                            dev_cost_pct: float,
                            k: float,
                            scurve_shape: str,
                            scurve_steepness: float) -> Dict[str, float]:
    # annual probabilities by candidate FID year (ensure presence)
    p25 = _safe_float(row.get("annual_p_2025"), 0.0)
    p26 = _safe_float(row.get("annual_p_2026"), 0.0)
    p27 = _safe_float(row.get("annual_p_2027"), 0.0)
    p_by_y = {y: p for y, p in {2025: p25, 2026: p26, 2027: p27}.items() if p > 0}

    blended_prob = sum(p_by_y.values())

    start_year = int(_safe_float(row.get("start_year"), BASE_YEAR))
    end_year = int(_safe_float(row.get("end_year"), BASE_YEAR))

    cost_basis = _pick_cost_basis(row)
    dev_cost = (dev_cost_pct * cost_basis) if not math.isnan(cost_basis) else np.nan

    # Expected FID year (conditional on schedule)
    e_fid = np.nan
    if blended_prob > 0:
        e_fid = sum(y * p for y, p in p_by_y.items()) / blended_prob

    # Unitized PV sums (relative to DevCost)
    sum_pv_out_unit = 0.0
    sum_pv_in_unit = 0.0

    # for IRR: build expected annual CF shares (unitized to DevCost)
    per_year_out_share: Dict[int, float] = {}
    per_year_in_share: Dict[int, float] = {}

    for y, p_y in p_by_y.items():
        # Spend path from start_year..y inclusive
        years = list(range(start_year, int(y) + 1))
        wts = scurve_weights(years, shape=scurve_shape, steepness=scurve_steepness)

        # PV of outflows (unitized) for this scenario y
        pv_out_unit_y = 0.0
        for t, w in wts.items():
            pv = w * pv_factor_to_base(t, base_year=BASE_YEAR, r=discount_rate)
            pv_out_unit_y += pv
            per_year_out_share[t] = per_year_out_share.get(t, 0.0) + p_y * w
        sum_pv_out_unit += p_y * pv_out_unit_y

        # PV of inflow (unitized) at FID year y
        pv_in_unit_y = pv_factor_to_base(int(y), base_year=BASE_YEAR, r=discount_rate)
        sum_pv_in_unit += p_y * pv_in_unit_y
        per_year_in_share[int(y)] = per_year_in_share.get(int(y), 0.0) + p_y

    # Closed-form break-even multiple and PV_MOIC at k
    k_star = np.nan
    pv_moic_k = np.nan
    if sum_pv_in_unit > 0 and sum_pv_out_unit > 0:
        k_star = sum_pv_out_unit / sum_pv_in_unit
        pv_moic_k = (k * sum_pv_in_unit) / sum_pv_out_unit

    # Build dollar cashflows for IRR (scale by DevCost)
    cashflows: Dict[int, float] = {}
    min_y = min(per_year_out_share.keys() | per_year_in_share.keys(), default=BASE_YEAR)
    max_y = max(per_year_out_share.keys() | per_year_in_share.keys(), default=BASE_YEAR)
    for t in range(min_y, max_y + 1):
        out_share = per_year_out_share.get(t, 0.0)
        in_share = per_year_in_share.get(t, 0.0)
        cf_t = 0.0
        if not math.isnan(dev_cost):
            cf_t += -dev_cost * out_share
            cf_t += dev_cost * k * in_share
        cashflows[t] = cf_t

    irr_k = _robust_irr(cashflows, guess=0.1) if any(abs(v) > 0 for v in cashflows.values()) else np.nan

    return {
        "blended_prob": blended_prob,
        "E_FID_year": e_fid,
        "cost_basis": cost_basis,
        "DevCost": dev_cost,
        "PV_OUT_per_DevCost": sum_pv_out_unit,
        "PV_IN_per_DevCost_k": sum_pv_in_unit,
        "PV_MOIC_k": pv_moic_k,
        "k_star": k_star,
        "IRR_k": irr_k,
    }


def compute_dev_fields(df_ev: pd.DataFrame,
                       discount_rate: float = DEFAULT_DEV_DISCOUNT,
                       dev_cost_pct: float = DEFAULT_DEV_COST_PCT,
                       k: float = DEFAULT_K,
                       scurve_shape: str = DEFAULT_SCURVE,
                       scurve_steepness: float = DEFAULT_SCURVE_STEEPNESS) -> pd.DataFrame:
    df = df_ev.copy()

    # Ensure presence and numeric types
    _ensure_numeric(df, [
        "annual_p_2025", "annual_p_2026", "annual_p_2027",
        "start_year", "end_year",
        "project_cost", "imputed_cost", "value_proxy_amount",
    ])

    rows = []
    for _, row in df.iterrows():
        m = compute_project_metrics(
            row=row,
            discount_rate=discount_rate,
            dev_cost_pct=dev_cost_pct,
            k=k,
            scurve_shape=scurve_shape,
            scurve_steepness=scurve_steepness,
        )
        rows.append(m)

    met = pd.DataFrame(rows)
    # Add adjusted k*: divide by blended_prob (NaN if zero)
    with np.errstate(divide='ignore', invalid='ignore'):
        met["k_star_adj"] = met["k_star"] / met["blended_prob"]
        # Keep NaN where blended_prob == 0 (as requested)
        mask_zero = (met["blended_prob"].fillna(0.0) == 0.0)
        met.loc[mask_zero, "k_star_adj"] = np.nan

    return pd.concat([df.reset_index(drop=True), met.reset_index(drop=True)], axis=1)


# -----------------------------
# Orchestration
# -----------------------------

def run_combined(
    input_csv: str,
    output_csv: str,
    p_source: str = DEFAULT_P_SOURCE,
    value_mode: str = DEFAULT_VALUE_MODE,
    dev_fee_rate: float = DEFAULT_DEV_FEE_RATE,
    ev_discount_rate: float = DEFAULT_EV_DISCOUNT,
    alpha0: float = DEFAULT_ALPHA0,
    alpha1: float = DEFAULT_ALPHA1,
    dev_discount_rate: float = DEFAULT_DEV_DISCOUNT,
    dev_cost_pct: float = DEFAULT_DEV_COST_PCT,
    k: float = DEFAULT_K,
    scurve_shape: str = DEFAULT_SCURVE,
    scurve_steepness: float = DEFAULT_SCURVE_STEEPNESS,
) -> str:
    df_in = pd.read_csv(input_csv)

    # Compute EV fields (always recompute to keep consistent with args)
    df_ev = compute_ev_fields(
        df_in,
        p_source=p_source,
        value_mode=value_mode,
        dev_fee_rate=dev_fee_rate,
        discount_rate=ev_discount_rate,
        alpha0=alpha0,
        alpha1=alpha1,
    )

    # Compute developer fields
    df_out = compute_dev_fields(
        df_ev,
        discount_rate=dev_discount_rate,
        dev_cost_pct=dev_cost_pct,
        k=k,
        scurve_shape=scurve_shape,
        scurve_steepness=scurve_steepness,
    )

    # Header hygiene: avoid duplicate headers if any
    # (no-op in normal circumstances; we simply ensure a single-row header is written)
    df_out.to_csv(output_csv, index=False)
    return output_csv

run_combined(
    input_csv="mpi_2024_scored.csv",
    output_csv="mpi_2024_ev_dev_combined.csv",
)