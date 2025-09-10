<<<<<<< HEAD
=======

>>>>>>> 070276b69b126f743360c1ee971a00f4116bd139
# exec_view.py
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
import dash_bootstrap_components as dbc

# ==========
# Formatting
# ==========
<<<<<<< HEAD
_FMT_INT0 = lambda v: f"{int(round(v, 0)):,}"
=======
_FMT_INT0 = lambda v: f"{int(round(float(v or 0), 0)):,}"
>>>>>>> 070276b69b126f743360c1ee971a00f4116bd139

def _as_num(s):
    return pd.to_numeric(s, errors="coerce")

def _notes_block(title: str, body_md: str, block_id: str):
<<<<<<< HEAD
    # Simple collapsible notes; caller ensures unique block_id
=======
    # Collapsible notes; caller ensures unique block_id
>>>>>>> 070276b69b126f743360c1ee971a00f4116bd139
    return html.Div([
        html.Details([
            html.Summary(html.Span(["Notes ▾"], style={"cursor":"pointer"})),
            dcc.Markdown(body_md, className="mt-2")
        ], id=block_id, open=False, style={"marginBottom":"6px"})
    ])

# =========================
# Shared helpers (Top-10…)
# =========================
def _top10_groups_map(df: pd.DataFrame, topn: int = 10) -> pd.Series:
    # On filtered data, rank by EV_cum
    ev_by_group = df.groupby("group", dropna=False)["EV_cum"].sum().sort_values(ascending=False)
    top = ev_by_group.head(topn).index.tolist()
    return df["group"].where(df["group"].isin(top), other="Other")

def _expected_fids_by_year(df: pd.DataFrame) -> pd.Series:
    # Sum of annual probabilities per year across filtered projects
    return pd.Series({
        2025: _as_num(df.get("annual_p_2025")).fillna(0).sum(),
        2026: _as_num(df.get("annual_p_2026")).fillna(0).sum(),
        2027: _as_num(df.get("annual_p_2027")).fillna(0).sum(),
    })

def _years_list():
    return [2025, 2026, 2027]

def _millions_axis(fig, axis="y"):
    ax = dict(
        title="C$ MM",
        ticks="outside",
        tickformat=",d",
        showgrid=True
    )
    if axis == "y":
        fig.update_yaxes(**ax)
    else:
        fig.update_xaxes(**ax)
    return fig

def _style_common(fig, title):
    fig.update_layout(
        title=title,
        template="plotly",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hoverlabel=dict(bgcolor="white", font_size=12),
        margin=dict(l=40, r=25, t=60, b=40),
        height=560
    )
    return fig

# ======================
# 1) EV & FIDs by year
# ======================
def make_ev_fids_by_year(df: pd.DataFrame) -> go.Figure:
    yrs = _years_list()
    # EV sums from EV_YYYY (already in millions)
    ev_series = pd.Series({y: _as_num(df.get(f"EV_{y}")).fillna(0).sum() for y in yrs})
    fids = _expected_fids_by_year(df)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=yrs, y=ev_series.values,
        name="Cumulative EV (C$ MM)",
        text=[_FMT_INT0(v) for v in ev_series.values],
        textposition="outside"
    ))
    fig.add_trace(go.Scatter(
        x=yrs, y=fids.values, name="Expected FIDs (count)",
        mode="lines+markers", yaxis="y2"
    ))
    fig.update_layout(
        yaxis=dict(title="Cumulative EV (C$ MM)", ticks="outside", tickformat=",d", showgrid=True),
        yaxis2=dict(title="Expected FIDs (count)", overlaying="y", side="right", ticks="outside", showgrid=False),
        xaxis=dict(ticks="outside"),
    )
    return _style_common(fig, "Expected EV and Expected FIDs by Year")

# ===========================
# 2) Cumulative EV by Province
# ===========================
def make_cum_ev_by_province(df: pd.DataFrame) -> go.Figure:
    g = df.groupby("province", dropna=False)["EV_cum"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(g, x="EV_cum", y="province", orientation="h", text=g["EV_cum"].map(_FMT_INT0))
    fig.update_traces(textposition="outside")
    _millions_axis(fig, axis="x")
    fig.update_yaxes(categoryorder="total ascending")  # horizontal bars: largest on top
    return _style_common(fig, "Cumulative EV by Province")

# =======================================
# 3) Cumulative EV by Top-10 Group + Other
# =======================================
def make_cum_ev_by_top_groups(df: pd.DataFrame, topn: int = 10) -> go.Figure:
    bucket = _top10_groups_map(df, topn)
    g = df.assign(group_bucket=bucket).groupby("group_bucket", dropna=False)["EV_cum"].sum()
    g = g.sort_values(ascending=False).reset_index()
    fig = px.bar(g, x="EV_cum", y="group_bucket", orientation="h", text=g["EV_cum"].map(_FMT_INT0))
    fig.update_traces(textposition="outside")
    _millions_axis(fig, axis="x")
    fig.update_yaxes(categoryorder="total ascending")
    return _style_common(fig, "Cumulative EV by Top 10 Group + Other")

# =============================================
# 4) Median EV per Expected FID by Province
# =============================================
def make_median_ev_per_fid_province(df: pd.DataFrame) -> go.Figure:
    den = _as_num(df.get("annual_p_2025")).fillna(0) + _as_num(df.get("annual_p_2026")).fillna(0) + _as_num(df.get("annual_p_2027")).fillna(0)
    ratio = _as_num(df.get("EV_cum")).where(den > 0, np.nan) / den.where(den > 0, np.nan)
    tmp = pd.DataFrame({"province": df["province"], "ratio": ratio})
    g = tmp.dropna().groupby("province", dropna=False)["ratio"].median().sort_values(ascending=False).reset_index()
    fig = px.bar(g, x="province", y="ratio", text=g["ratio"].map(_FMT_INT0))
    fig.update_traces(textposition="outside")
    _millions_axis(fig, axis="y")
    fig.update_layout(yaxis_title="Median EV per Expected FID (C$ MM)")
    return _style_common(fig, "Median EV per Expected FID by Province")

# ==================================================
# 5) Median EV per Expected FID by Top-10 Group + Other
# ==================================================
def make_median_ev_per_fid_top_groups(df: pd.DataFrame, topn: int = 10) -> go.Figure:
    bucket = _top10_groups_map(df, topn)
    den = _as_num(df.get("annual_p_2025")).fillna(0) + _as_num(df.get("annual_p_2026")).fillna(0) + _as_num(df.get("annual_p_2027")).fillna(0)
    ratio = _as_num(df.get("EV_cum")).where(den > 0, np.nan) / den.where(den > 0, np.nan)
    tmp = pd.DataFrame({"group_bucket": bucket, "ratio": ratio})
    g = tmp.dropna().groupby("group_bucket", dropna=False)["ratio"].median().sort_values(ascending=False).reset_index()
    fig = px.bar(g, x="ratio", y="group_bucket", orientation="h", text=g["ratio"].map(_FMT_INT0))
    fig.update_traces(textposition="outside")
    _millions_axis(fig, axis="x")
    fig.update_layout(xaxis_title="Median EV per Expected FID (C$ MM)")
    fig.update_yaxes(categoryorder="total ascending")
    return _style_common(fig, "Median EV per Expected FID by Top 10 Group + Other")

# ===================================================
# 6) Heat Map — Cumulative EV (Group × Province)
# ===================================================
def make_heat_cum_ev_group_province(df: pd.DataFrame, topn: int = 10) -> go.Figure:
    bucket = _top10_groups_map(df, topn)
    pv = (df.assign(group_bucket=bucket)
            .groupby(["province", "group_bucket"], dropna=False)["EV_cum"].sum()
            .reset_index()
            .pivot(index="province", columns="group_bucket", values="EV_cum")
         )
    # province alpha order; columns in EV rank order + Other last
    cols = pv.sum(axis=0).sort_values(ascending=False).index.tolist()
    if "Other" in cols:
        cols = [c for c in cols if c != "Other"] + ["Other"]
    pv = pv.reindex(sorted(pv.index, key=lambda x: str(x)), axis=0)[cols]
    z = pv.fillna(0)

    text = z.applymap(lambda v: "" if v == 0 else f"{int(round(v,0)):,}")
    fig = px.imshow(z, text_auto=False, aspect="auto", color_continuous_scale="Blues")
<<<<<<< HEAD
    fig.update_traces(text=text.values)
=======
    fig.update_traces(text=text.values, hovertemplate="Province %{y}<br>Group %{x}<br>EV: C$%{z:,.0f} MM<extra></extra>")
>>>>>>> 070276b69b126f743360c1ee971a00f4116bd139
    fig.update_layout(coloraxis_colorbar=dict(title="C$ MM"))
    fig.update_xaxes(side="top", tickangle=45)
    fig.update_yaxes(autorange="reversed")
    return _style_common(fig, "Heat Map — Cumulative EV by Group and Province")

# ============================================================
# 7) Heat Map — Risk-Adjusted Break-Even Multiple (k*_adj)
# ============================================================
def make_heat_kstar_group_province(df: pd.DataFrame, topn: int = 10) -> go.Figure:
    bucket = _top10_groups_map(df, topn)
    pv = (df.assign(group_bucket=bucket)
            .groupby(["province", "group_bucket"], dropna=False)["k_star_adj"].median()
            .reset_index()
            .pivot(index="province", columns="group_bucket", values="k_star_adj")
         )
    cols = pv.median(axis=0, skipna=True).sort_values(ascending=False).index.tolist()
    if "Other" in cols:
        cols = [c for c in cols if c != "Other"] + ["Other"]
    pv = pv.reindex(sorted(pv.index, key=lambda x: str(x)), axis=0)[cols]

    z = pv.copy()
    # Cap color range at p95 for robustness (hover shows true values)
    finite_vals = _as_num(z.values.flatten())
    finite_vals = finite_vals[np.isfinite(finite_vals)]
    if len(finite_vals):
        p95 = np.nanpercentile(finite_vals, 95)
        cmin, cmax = float(np.nanmin(finite_vals)), float(p95)
    else:
        cmin, cmax = 0.0, 1.0

    fig = px.imshow(z, text_auto=False, aspect="auto", color_continuous_scale="Reds", zmin=cmin, zmax=cmax)
    # Hide zeros in text; show 1 decimal in hover
    text = z.applymap(lambda v: "" if (pd.isna(v) or v == 0) else f"{v:.1f}×")
    fig.update_traces(text=text.values, hovertemplate="Province %{y}<br>Group %{x}<br>RABE-MOIC: %{z:.1f}×<extra></extra>")
    fig.update_layout(coloraxis_colorbar=dict(title="Multiple (× DevCost)"))
    fig.update_xaxes(side="top", tickangle=45)
    fig.update_yaxes(autorange="reversed")
    return _style_common(fig, "Heat Map — Risk-Adjusted Break-Even Multiple by Group and Province")

# ===========================
# Page renderer (one per row)
# ===========================
def render_exec_view(df: pd.DataFrame, topn: int = 10) -> html.Div:
    # Defensive: ensure required cols present
    need = {"EV_cum","EV_2025","EV_2026","EV_2027","annual_p_2025","annual_p_2026","annual_p_2027","province","group","k_star_adj"}
    missing = sorted(list(need - set(df.columns)))
    if missing:
        return html.Div(f"Missing columns for Exec View: {', '.join(missing)}", className="text-danger")

    # Charts (one per row)
    fig1 = make_ev_fids_by_year(df)
    fig2 = make_cum_ev_by_province(df)
    fig3 = make_cum_ev_by_top_groups(df, topn)
    fig4 = make_median_ev_per_fid_province(df)
    fig5 = make_median_ev_per_fid_top_groups(df, topn)
    fig6 = make_heat_cum_ev_group_province(df, topn)
    fig7 = make_heat_kstar_group_province(df, topn)

<<<<<<< HEAD
    # Notes placeholders (you’ll add copy in app)
    notes1 = _notes_block("Notes-1", "Add your short methods note here (softmax year allocation; sums of annual probabilities).", "notes-1")
    notes2 = _notes_block("Notes-2", "Add context on province EV aggregation and units (C$ MM).", "notes-2")
    notes3 = _notes_block("Notes-3", "Explain Top-10 + Other construction (based on filtered EV_cum).", "notes-3")
    notes4 = _notes_block("Notes-4", "Median of project-level EV/FID ratios; denominator is Σ annual_p_YYYY.", "notes-4")
    notes5 = _notes_block("Notes-5", "Same ratio as above, bucketed by Top-10 + Other.", "notes-5")
    notes6 = _notes_block("Notes-6", "Zeros hidden in cell text; hover still shows 0; province alphabetical.", "notes-6")
=======
    # Notes placeholders
    notes1 = _notes_block("Notes-1", "Add your methods note here (softmax year allocation; sums of annual probabilities).", "notes-1")
    notes2 = _notes_block("Notes-2", "Province EV aggregation and units (C$ MM).", "notes-2")
    notes3 = _notes_block("Notes-3", "Top-10 + Other construction (based on filtered EV_cum).", "notes-3")
    notes4 = _notes_block("Notes-4", "Median of project-level EV/FID ratios; denominator is Σ annual_p_YYYY.", "notes-4")
    notes5 = _notes_block("Notes-5", "Same ratio as above, bucketed by Top-10 + Other.", "notes-5")
    notes6 = _notes_block("Notes-6", "Zeros hidden in cell text; hover shows 0; province alphabetical.", "notes-6")
>>>>>>> 070276b69b126f743360c1ee971a00f4116bd139
    notes7 = _notes_block("Notes-7", "Color scale capped at p95; hover shows true k* values.", "notes-7")

    return html.Div([
        notes1, dcc.Graph(figure=fig1), html.Br(),
        notes2, dcc.Graph(figure=fig2), html.Br(),
        notes3, dcc.Graph(figure=fig3), html.Br(),
        notes4, dcc.Graph(figure=fig4), html.Br(),
        notes5, dcc.Graph(figure=fig5), html.Br(),
        notes6, dcc.Graph(figure=fig6), html.Br(),
        notes7, dcc.Graph(figure=fig7)
    ])
