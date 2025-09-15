
#!/usr/bin/env python3
"""
EV (Expected Value) + Developer Engine — N‑year version (default: 5 years)

This script generalizes your previous 3‑year engine to an arbitrary horizon.
It allocates a chosen total probability (p_bayes / p_cox / blended_prob) across
a list of candidate FID years and computes EV by year, cumulative EV, discounted EV,
and developer metrics (PV_MOIC_k, k_star, IRR_k, k_star_adj) using an S‑curve
spend path to FID.

Key properties:
- EV horizon is configurable: --ev-horizon-years (default 5).
- Candidate years are BASE_YEAR+1 .. BASE_YEAR+horizon.
- Annual probabilities are allocated with a softmax that favors earlier years when
  urgency is high and years_remaining is small. If inputs are missing, allocation defaults
  to equal shares.
- Developer engine auto-detects annual_p_* columns to compute blended_prob, E_FID_year,
  PV sums, PV_MOIC_k, k_star, IRR_k, and k_star_adj.
- Recomputes annual_p_* and EV_* on every run (deterministic behavior from this script alone).
- No placeholders; fully runnable via CLI or by importing run_combined().

CLI example:
  python ev_engine_dev_combined_5y.py \
    --input mpi_2024_scored.csv \
    --output mpi_2024_ev_dev_combined_5y.csv \
    --p-source blended_prob \
    --value-mode capex \
    --dev-fee-rate 0.05 \
    --ev-discount 0.00 \
    --dev-discount 0.13 \
    --dev-cost-pct 0.03 \
    --k 1.0 \
    --scurve S \
    --scurve-steepness 6.0 \
    --ev-horizon-years 5

Outputs:
- Writes a CSV with original columns + annual_p_YYYY, EV_YYYY, EV_cum, EV_disc,
  and developer metrics (blended_prob, E_FID_year, cost_basis, DevCost,
  PV_OUT_per_DevCost, PV_IN_per_DevCost_k, PV_MOIC_k, k_star, IRR_k, k_star_adj).

Notes:
- Numeric misses are left as NaN; text misses as "".
- BASE_YEAR is 2024 by default; can be overridden via CLI.
"""

from __future__ import annotations
import argparse
import math
from typing import Dict, List

import numpy as np
import pandas as pd

# =============================
# Defaults & Globals
# =============================
BASE_YEAR_DEFAULT = 2024

# EV engine defaults
DEFAULT_P_SOURCE = "blended_prob"    # or: p_bayes, p_cox
DEFAULT_VALUE_MODE = "capex"         # or: dev_fee, count
DEFAULT_DEV_FEE_RATE = 0.05          # for value_mode == dev_fee
DEFAULT_EV_DISCOUNT = 0.0            # EV discount (often 0.0)
DEFAULT_ALPHA0 = 0.75                # allocation softmax hyperparam
DEFAULT_ALPHA1 = 2.0                 # allocation softmax hyperparam
DEFAULT_EV_HORIZON_YEARS = 5         # <-- 5-year EV allocation by default

# Developer engine defaults
DEFAULT_DEV_DISCOUNT = 0.13          # developer PV discount
DEFAULT_DEV_COST_PCT = 0.03          # DevCost = dev_cost_pct * cost_basis
DEFAULT_K = 1.0                      # reimbursement-only MOIC at FID
DEFAULT_SCURVE = "S"                 # S-curve to FID
DEFAULT_SCURVE_STEEPNESS = 6.0       # logistic steepness for S-curve


# =============================
# Utilities
# =============================
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


def _ev_years(base_year: int, horizon_years: int) -> List[int]:
    start = int(base_year) + 1
    return list(range(start, start + int(horizon_years)))


# =============================
# EV ENGINE (annual probs + EV by year)
# =============================
def _softmax_weights_n(t_years_remaining: float, urgency_01: float,
                       alpha0: float, alpha1: float, n: int) -> np.ndarray:
    """
    Generalized softmax allocator over n candidate years (0..n-1 index),
    favoring earlier years as urgency increases and years_remaining decreases.
    """
    t = max(0.25, float(t_years_remaining))
    u = float(urgency_01)
    if n <= 1:
        return np.array([1.0], dtype=float)

    idx = np.arange(n, dtype=float)
    denom = max(1.0, n - 1.0)
    # Score declines with later idx; rises with urgency; lower t boosts early years.
    scores = alpha0 * (u * (1.0 - (idx / denom)) + 1.0 / (t + 0.5 * idx))
    scores *= float(alpha1)
    # Stable softmax
    m = scores.max()
    e = np.exp(scores - m)
    w = e / e.sum()
    return w.astype(float)


def _allocate_annual_probs_n(row: pd.Series, p_total: float, years: List[int],
                             alpha0: float, alpha1: float) -> List[float]:
    n = len(years)
    if not (p_total and p_total > 0):
        return [0.0] * n

    yrs = _safe_float(row.get("years_remaining"))
    urg = _safe_float(row.get("urgency_scale_(0-1)"))
    if not (math.isnan(yrs) or math.isnan(urg)):
        w = _softmax_weights_n(yrs, urg, alpha0, alpha1, n)
    else:
        w = np.full(n, 1.0 / n, dtype=float)
    return [float(p_total * wi) for wi in w]


def _pick_p_total(row: pd.Series, p_source: str) -> float:
    if p_source == "p_bayes":
        return _safe_float(row.get("p_bayes"), 0.0)
    if p_source == "p_cox":
        return _safe_float(row.get("p_cox"), 0.0)
    return _safe_float(row.get("blended_prob"), 0.0)  # default


def _value_proxy_amount(row: pd.Series, value_mode: str, dev_fee_rate: float) -> float:
    capex = _safe_float(row.get("project_cost"), np.nan)
    if value_mode == "dev_fee":
        return capex * float(dev_fee_rate) if not math.isnan(capex) else np.nan
    if value_mode == "count":
        return 1.0
    # default: capex
    return capex


def compute_ev_fields(df: pd.DataFrame,
                      base_year: int,
                      p_source: str = DEFAULT_P_SOURCE,
                      value_mode: str = DEFAULT_VALUE_MODE,
                      dev_fee_rate: float = DEFAULT_DEV_FEE_RATE,
                      discount_rate: float = DEFAULT_EV_DISCOUNT,
                      alpha0: float = DEFAULT_ALPHA0,
                      alpha1: float = DEFAULT_ALPHA1,
                      horizon_years: int = DEFAULT_EV_HORIZON_YEARS) -> pd.DataFrame:
    df = df.copy()

    # Ensure numeric
    _ensure_numeric(df, [
        "project_cost", "years_remaining", "urgency_scale_(0-1)",
        "blended_prob", "p_bayes", "p_cox",
    ])

    # Compute value proxy explicitly
    df["value_mode"] = value_mode
    df["value_proxy_amount"] = df.apply(lambda r: _value_proxy_amount(r, value_mode, dev_fee_rate), axis=1)

    # Choose total probability and allocate over dynamic years
    df["p_source_used"] = p_source
    years = _ev_years(base_year, horizon_years)
    allocs = df.apply(
        lambda r: _allocate_annual_probs_n(
            r,
            _pick_p_total(r, p_source),
            years,
            alpha0, alpha1
        ),
        axis=1
    )

    # Materialize annual_p_YYYY columns
    for i, y in enumerate(years):
        df[f"annual_p_{y}"] = allocs.apply(lambda a: a[i])

    # EV per year = P(year) * value_proxy_amount
    for y in years:
        df[f"EV_{y}"] = df[f"annual_p_{y}"].astype(float) * df["value_proxy_amount"].astype(float)

    # Cumulative EV and discounted EV to base_year
    ev_cols = [f"EV_{y}" for y in years]
    df["EV_cum"] = df[ev_cols].sum(axis=1, min_count=1)

    if discount_rate and discount_rate != 0.0:
        def _pv_row(r: pd.Series) -> float:
            total = 0.0
            for y in years:
                ev_y = _safe_float(r.get(f"EV_{y}"), 0.0)
                total += ev_y / ((1.0 + discount_rate) ** (y - base_year))
            return total
        df["EV_disc"] = df.apply(_pv_row, axis=1)
    else:
        df["EV_disc"] = df["EV_cum"]

    return df


# =============================
# DEVELOPER ENGINE (PV sums, k*, PV_MOIC_k, IRR_k)
# =============================
def pv_factor_to_base(year: int, base_year: int, r: float) -> float:
    """Present-value factor relative to base_year.
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
        w = np.exp(-0.8 * idx)           # more mass earlier
    elif shape == "back":
        w = np.exp(0.8 * idx)            # more mass later
    else:  # "S"
        s = float(steepness)
        w = 1.0 / (1.0 + np.exp(-s * x))  # 0..1 S-curve level
        w = np.diff(np.concatenate([[0.0], w]))  # convert to per-year increments
        w = np.clip(w, 1e-12, None)       # guard numerical

    w = w / w.sum()
    return {int(y): float(wi) for y, wi in zip(ys, w)}


def _robust_irr(cashflows: Dict[int, float], base_year: int, guess: float = 0.1,
                lo: float = -0.95, hi: float = 1.5, tol: float = 1e-6, iters: int = 200) -> float:
    """Bisection IRR on expected cashflows (practical and numerically stable)."""
    def npv_at(rate: float) -> float:
        return sum(val / ((1.0 + rate) ** (t - base_year)) for t, val in cashflows.items())

    npv_lo = npv_at(lo)
    npv_hi = npv_at(hi)
    if math.isnan(npv_lo) or math.isnan(npv_hi):
        return np.nan

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


def _pick_cost_basis(row: pd.Series) -> float:
    """Prefer project_cost → imputed_cost → value_proxy_amount."""
    for c in ("project_cost", "imputed_cost", "value_proxy_amount"):
        v = _safe_float(row.get(c), np.nan)
        if not math.isnan(v):
            return v
    return np.nan


def compute_dev_fields(df_ev: pd.DataFrame,
                       base_year: int,
                       discount_rate: float = DEFAULT_DEV_DISCOUNT,
                       dev_cost_pct: float = DEFAULT_DEV_COST_PCT,
                       k: float = DEFAULT_K,
                       scurve_shape: str = DEFAULT_SCURVE,
                       scurve_steepness: float = DEFAULT_SCURVE_STEEPNESS) -> pd.DataFrame:
    df = df_ev.copy()

    # Detect candidate FID years from annual_p_* columns
    ev_years = sorted(int(c.split("_")[-1]) for c in df.columns if c.startswith("annual_p_"))

    _ensure_numeric(df, [*(f"annual_p_{y}" for y in ev_years),
                         "start_year","end_year",
                         "project_cost","imputed_cost","value_proxy_amount"])

    rows = []
    for _, row in df.iterrows():
        # Build probability mass by candidate year
        p_by_y = {y: _safe_float(row.get(f"annual_p_{y}"), 0.0) for y in ev_years}
        p_by_y = {y: p for y, p in p_by_y.items() if p > 0}
        blended_prob = sum(p_by_y.values())

        start_year = int(_safe_float(row.get("start_year"), base_year))
        cost_basis = _pick_cost_basis(row)
        dev_cost = (dev_cost_pct * cost_basis) if not math.isnan(cost_basis) else np.nan

        e_fid = (sum(y * p for y, p in p_by_y.items()) / blended_prob) if blended_prob > 0 else np.nan

        # Unitized PV sums and per-year cashflow shares
        sum_pv_out_unit, sum_pv_in_unit = 0.0, 0.0
        per_year_out_share, per_year_in_share = {}, {}

        for y, p_y in p_by_y.items():
            # Spend path from start_year..y inclusive
            years = list(range(start_year, int(y) + 1))
            wts = scurve_weights(years, shape=scurve_shape, steepness=scurve_steepness)

            # PV of outflows (unitized) for scenario y
            pv_out_unit_y = 0.0
            for t, w in wts.items():
                pv = w * pv_factor_to_base(t, base_year=base_year, r=discount_rate)
                pv_out_unit_y += pv
                per_year_out_share[t] = per_year_out_share.get(t, 0.0) + p_y * w
            sum_pv_out_unit += p_y * pv_out_unit_y

            # PV of inflow (unitized) at FID year y
            pv_in_unit_y = pv_factor_to_base(int(y), base_year=base_year, r=discount_rate)
            sum_pv_in_unit += p_y * pv_in_unit_y
            per_year_in_share[int(y)] = per_year_in_share.get(int(y), 0.0) + p_y

        # Break-even multiple and PV_MOIC at k
        k_star = np.nan
        pv_moic_k = np.nan
        if sum_pv_in_unit > 0 and sum_pv_out_unit > 0:
            k_star = sum_pv_out_unit / sum_pv_in_unit
            pv_moic_k = (k * sum_pv_in_unit) / sum_pv_out_unit

        # Build expected cashflows for IRR (scale by DevCost)
        cashflows: Dict[int, float] = {}
        keys = per_year_out_share.keys() | per_year_in_share.keys()
        min_y = min(keys, default=base_year)
        max_y = max(keys, default=base_year)
        for t in range(min_y, max_y + 1):
            out_share = per_year_out_share.get(t, 0.0)
            in_share  = per_year_in_share.get(t, 0.0)
            cf_t = 0.0
            if not math.isnan(dev_cost):
                cf_t += -dev_cost * out_share
                cf_t +=  dev_cost * k * in_share
            cashflows[t] = cf_t

        irr_k = _robust_irr(cashflows, base_year=base_year, guess=0.1) if any(abs(v) > 0 for v in cashflows.values()) else np.nan

        rows.append({
            "blended_prob": blended_prob,
            "E_FID_year": e_fid,
            "cost_basis": cost_basis,
            "DevCost": dev_cost,
            "PV_OUT_per_DevCost": sum_pv_out_unit,
            "PV_IN_per_DevCost_k": sum_pv_in_unit,
            "PV_MOIC_k": pv_moic_k,
            "k_star": k_star,
            "IRR_k": irr_k,
        })

    met = pd.DataFrame(rows)
    with np.errstate(divide='ignore', invalid='ignore'):
        met["k_star_adj"] = met["k_star"] / met["blended_prob"]
        met.loc[(met["blended_prob"].fillna(0.0) == 0.0), "k_star_adj"] = np.nan

    return pd.concat([df.reset_index(drop=True), met.reset_index(drop=True)], axis=1)


# =============================
# Orchestration
# =============================
def run_combined(
    input_csv: str,
    output_csv: str,
    base_year: int = BASE_YEAR_DEFAULT,
    p_source: str = DEFAULT_P_SOURCE,
    value_mode: str = DEFAULT_VALUE_MODE,
    dev_fee_rate: float = DEFAULT_DEV_FEE_RATE,
    ev_discount_rate: float = DEFAULT_EV_DISCOUNT,
    alpha0: float = DEFAULT_ALPHA0,
    alpha1: float = DEFAULT_ALPHA1,
    ev_horizon_years: int = DEFAULT_EV_HORIZON_YEARS,
    dev_discount_rate: float = DEFAULT_DEV_DISCOUNT,
    dev_cost_pct: float = DEFAULT_DEV_COST_PCT,
    k: float = DEFAULT_K,
    scurve_shape: str = DEFAULT_SCURVE,
    scurve_steepness: float = DEFAULT_SCURVE_STEEPNESS,
) -> str:
    # Read input
    df_in = pd.read_csv(input_csv)

    # Compute EV fields (recomputed every run for determinism)
    df_ev = compute_ev_fields(
        df_in,
        base_year=base_year,
        p_source=p_source,
        value_mode=value_mode,
        dev_fee_rate=dev_fee_rate,
        discount_rate=ev_discount_rate,
        alpha0=alpha0,
        alpha1=alpha1,
        horizon_years=ev_horizon_years,
    )

    # Compute developer fields
    df_out = compute_dev_fields(
        df_ev,
        base_year=base_year,
        discount_rate=dev_discount_rate,
        dev_cost_pct=dev_cost_pct,
        k=k,
        scurve_shape=scurve_shape,
        scurve_steepness=scurve_steepness,
    )

    # Write output
    df_out.to_csv(output_csv, index=False)
    return output_csv


# =============================
# CLI
# =============================
def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="EV + Developer Engine (N-year horizon; default 5).")
    p.add_argument("--input",  required=True, help="Input CSV (e.g., mpi_2024_scored.csv)")
    p.add_argument("--output", required=True, help="Output CSV (e.g., mpi_2024_ev_dev_combined_5y.csv)")
    p.add_argument("--base-year", type=int, default=BASE_YEAR_DEFAULT, help="Base year for PV (default 2024)")
    p.add_argument("--p-source", choices=["blended_prob", "p_bayes", "p_cox"], default=DEFAULT_P_SOURCE,
                   help="Total probability source to allocate across candidate years")
    p.add_argument("--value-mode", choices=["capex", "dev_fee", "count"], default=DEFAULT_VALUE_MODE,
                   help="Value proxy for EV calculation (capex=project_cost; dev_fee=capex*rate; count=1 per FID)")
    p.add_argument("--dev-fee-rate", type=float, default=DEFAULT_DEV_FEE_RATE,
                   help="Dev fee rate when --value-mode=dev_fee (default 0.05)")
    p.add_argument("--ev-discount", type=float, default=DEFAULT_EV_DISCOUNT,
                   help="Discount rate for EV PV (default 0.0)")
    p.add_argument("--alpha0", type=float, default=DEFAULT_ALPHA0, help="Allocator hyperparam alpha0 (default 0.75)")
    p.add_argument("--alpha1", type=float, default=DEFAULT_ALPHA1, help="Allocator hyperparam alpha1 (default 2.0)")
    p.add_argument("--ev-horizon-years", type=int, default=DEFAULT_EV_HORIZON_YEARS,
                   help="Number of candidate FID years to allocate probability/EV over (default 5)")
    p.add_argument("--dev-discount", type=float, default=DEFAULT_DEV_DISCOUNT,
                   help="Developer PV discount rate (default 0.13)")
    p.add_argument("--dev-cost-pct", type=float, default=DEFAULT_DEV_COST_PCT,
                   help="DevCost percentage of cost_basis (default 0.03)")
    p.add_argument("--k", type=float, default=DEFAULT_K, help="Reimbursement multiple at FID for PV_MOIC_k (default 1.0)")
    p.add_argument("--scurve", choices=["S", "even", "front", "back"], default=DEFAULT_SCURVE,
                   help="Spend profile shape from start_year to FID year (default S)")
    p.add_argument("--scurve-steepness", type=float, default=DEFAULT_SCURVE_STEEPNESS,
                   help="Logistic steepness for S-curve (default 6.0)")
    return p


def main() -> None:
    ap = _build_cli()
    args = ap.parse_args()

    run_combined(
        input_csv=args.input,
        output_csv=args.output,
        base_year=args.base_year,
        p_source=args.p_source,
        value_mode=args.value_mode,
        dev_fee_rate=args.dev_fee_rate,
        ev_discount_rate=args.ev_discount,
        alpha0=args.alpha0,
        alpha1=args.alpha1,
        ev_horizon_years=args.ev_horizon_years,
        dev_discount_rate=args.dev_discount,
        dev_cost_pct=args.dev_cost_pct,
        k=args.k,
        scurve_shape=args.scurve,
        scurve_steepness=args.scurve_steepness,
    )


if __name__ == "__main__":
    main()
