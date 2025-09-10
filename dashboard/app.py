import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output, State, ctx as dash_ctx
import dash_bootstrap_components as dbc
# ============================================================
# Default data loading (auto-discover *.xlsx beside app.py; ignore /data)
# ============================================================
from pathlib import Path
import os
# --- Header configuration via environment variables (safe defaults) ---
APP_TITLE = os.getenv("APP_TITLE", "Energy Nation — MPI Probability (≤3 Years)")
APP_NOTICE_MD = os.getenv("APP_NOTICE_MD", "")  # Markdown allowed
APP_LINKS_SPEC = os.getenv("APP_LINKS_SPEC", "")  # "Label|URL;Label2|URL2"


HERE = Path(__file__).parent
LAST_SOURCE = None
LAST_ERRORS = []

def _xlsx_in_here():
    # Ignore temporary Excel files like "~$foo.xlsx"
    return sorted([p for p in HERE.glob("*.xlsx") if not p.name.startswith("~$")])

# Optional override via env var: DATAFILE=mpi_2024_scored.xlsx
_ENV_CHOICE = os.getenv("DATAFILE")

# Preference order: env var (if provided), then these names if present, then any other *.xlsx
_PREFERRED_NAMES = ["mpi_2024_ev_dev_combined.xlsx", "mpi_2024_scored.xlsx", "sample_mpi.xlsx"]

def _candidate_paths():
    files_here = _xlsx_in_here()
    by_name = {p.name: p for p in files_here}

    ordered = []
    if _ENV_CHOICE:
        # If DATAFILE points to a file name or absolute/relative path
        env_path = (HERE / _ENV_CHOICE) if not os.path.isabs(_ENV_CHOICE) else Path(_ENV_CHOICE)
        if env_path.exists() and env_path.suffix.lower() == ".xlsx":
            ordered.append(env_path)

    # Add preferred names if present
    for name in _PREFERRED_NAMES:
        if name in by_name:
            ordered.append(by_name[name])

    # Add any remaining discovered *.xlsx not already included
    for pth in files_here:
        if pth not in ordered:
            ordered.append(pth)

    return ordered

CANDIDATES = _candidate_paths()

def _read_any(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, engine="openpyxl")

def _load_default_or_raise() -> pd.DataFrame:
    global LAST_SOURCE, LAST_ERRORS
    LAST_SOURCE, LAST_ERRORS = None, []
    for pth in CANDIDATES:
        try:
            if pth.exists():
                df = _read_any(pth)
                LAST_SOURCE = str(pth)
                return df
            else:
                LAST_ERRORS.append(f"missing: {pth}")
        except Exception as e:
            LAST_ERRORS.append(f"error reading {pth}: {e}")
    raise FileNotFoundError("; ".join(LAST_ERRORS) if LAST_ERRORS else "No candidates found.")

# ============================================================
# Helpers
# ============================================================
REQUIRED_COLUMNS = [
    "province","sector","group","cleantech",
    "start_year","end_year","project_cost",
    "current_survival","end_success",
    "start_status","end_status",
    "latitude_1","longitude_1",
    "company","project",
    "blended_prob","priority_index","power_ranking"
]

COLORBLIND = px.colors.qualitative.Safe

def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    num_cols = ["start_year","end_year","project_cost","latitude_1","longitude_1","blended_prob","priority_index","power_ranking"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "current_survival" in df.columns:
        df["current_survival"] = pd.to_numeric(df["current_survival"], errors="coerce").fillna(0).astype(int)
    if "end_success" in df.columns:
        df["end_success"] = pd.to_numeric(df["end_success"], errors="coerce").fillna(0).astype(int)
    if "cleantech" in df.columns:
        df["cleantech"] = df["cleantech"].astype(str).str.strip().str.title().replace({"Yes":"Yes","No":"No"})
    return df

def _validate_schema(df: pd.DataFrame) -> list:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]

def add_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "project_cost" in df.columns:
        df["cost_mm"] = (pd.to_numeric(df["project_cost"], errors="coerce") * 1).round(0).astype("Int64")
    for c in ["blended_prob","priority_index","power_ranking"]:
        if c in df.columns:
            df[c+"_2dp"] = pd.to_numeric(df[c], errors="coerce").round(2)
    return df

def sector_color_map(df):
    sectors = sorted(df["sector"].dropna().unique().tolist()) if "sector" in df else []
    color_map = {}
    for i, s in enumerate(sectors):
        color_map[s] = COLORBLIND[i % len(COLORBLIND)]
    return color_map

def fmt_millions_from_billions(x):
    try:
        val_m = int(round(float(x) * 1, 0))
        return f"{val_m:,}"
    except Exception:
        return "0"

def truncate(s, n=36):
    s = str(s)
    return s if len(s) <= n else s[: n-1] + "…"

def normalize_power_score(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return s.fillna(0.0)
    smin, smax = s.min(), s.max()
    if smin >= 0 and smax <= 1:
        return s.fillna(0.0)
    unique_frac = s.nunique(dropna=True) / max(len(s.dropna()), 1)
    looks_like_rank = unique_frac < 0.5 and smin >= 1 and smax < 1e7
    if looks_like_rank:
        s = smax - s + smin
    if smax == smin:
        return s.fillna(1.0)
    return (s - s.min()) / (s.max() - s.min())

def attach_customdata_by_trace(fig, df, color_col):
    for tr in fig.data:
        val = getattr(tr, "name", None)
        if val is None:
            tr.customdata = build_common_customdata(df)
            tr.hovertemplate = COMMON_HOVER_TMPL
            continue
        mask = (df[color_col] == val)
        subdf = df[mask] if mask.any() else df.iloc[0:0]
        tr.customdata = build_common_customdata(subdf)
        tr.hovertemplate = COMMON_HOVER_TMPL

def build_year_marks(min_year, max_year, step=1):
    return {int(y): str(int(y)) for y in range(int(min_year), int(max_year)+1, step)}

def _unique_sorted(df, col):
    if col not in df.columns:
        return []
    return sorted([v for v in df[col].dropna().astype(str).unique().tolist() if str(v).strip() != "" ])

# NEW: helper to wrap long tick/category labels with <br>
def _wrap_label(s, width=14):
    import textwrap
    try:
        s_str = str(s)
        return "<br>".join(textwrap.wrap(s_str, width=width)) if len(s_str) > width else s_str
    except Exception:
        return s

# ============================================================
# App init & sidebar defaults (static)
# ============================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.config.suppress_callback_exceptions = True
server = app.server

try:
    INIT_RAW = _coerce_types(_load_default_or_raise())
    if "urgency_scale_(0-1)" in INIT_RAW.columns:
        INIT_RAW["priority_index"] = pd.to_numeric(INIT_RAW["urgency_scale_(0-1)"], errors="coerce").clip(0,1)
    INIT_DF = add_display_columns(INIT_RAW)
    SCHEMA_INIT_MSG = ""
except Exception as e:
    INIT_DF = pd.DataFrame(columns=REQUIRED_COLUMNS)
    SCHEMA_INIT_MSG = str(e)


# Sidebar option lists (static; from initial data)
PROVINCES = _unique_sorted(INIT_DF, "province")
SECTORS   = _unique_sorted(INIT_DF, "sector")
GROUPS    = _unique_sorted(INIT_DF, "group")
COMPANIES = _unique_sorted(INIT_DF, "company")
PROJECTS  = _unique_sorted(INIT_DF, "project")
STATUSES  = _unique_sorted(INIT_DF, "end_status")

# Defaults (static)
COMPANY_DEFAULT   = []          # no filter
COMP_SEL_DEFAULT  = []          # no filter
PROJ_SEL_DEFAULT  = []          # no filter
PROVINCE_DEFAULT  = []          # all
SECTOR_DEFAULT    = []          # all
GROUP_DEFAULT     = []          # all
STATUS_DEFAULT    = []          # all
CLEAN_DEFAULT     = []          # All means no filter
TOPN_DEFAULT      = 10
AGG_DEFAULT       = "count"

# Year/Cost ranges (static from initial data)
def _safe_int(x, d): 
    try: return int(x)
    except: return d
def _safe_float(x, d): 
    try: return float(x)
    except: return d

MIN_YEAR = _safe_int(INIT_DF["start_year"].min() if "start_year" in INIT_DF else 2000, 2000)
MAX_YEAR = _safe_int(INIT_DF["end_year"].max() if "end_year" in INIT_DF else 2025, 2025)
if MIN_YEAR > MAX_YEAR: MIN_YEAR, MAX_YEAR = 2000, 2025

MIN_COST = _safe_float(INIT_DF["project_cost"].min() if "project_cost" in INIT_DF else 0.0, 0.0)
MAX_COST = _safe_float(INIT_DF["project_cost"].max() if "project_cost" in INIT_DF else 1.0, 1.0)
if not np.isfinite(MIN_COST) or not np.isfinite(MAX_COST) or MIN_COST > MAX_COST:
    MIN_COST, MAX_COST = 0.0, 1.0


def header():
    title_block = html.H3(APP_TITLE, className="mb-2")

    notice = None
    if APP_NOTICE_MD.strip():
        notice = dbc.Alert(
            dcc.Markdown(APP_NOTICE_MD),
            color="warning",
            className="py-2 px-3 mb-2",
            style={"whiteSpace": "pre-wrap"}
        )

    link_buttons = []
    if APP_LINKS_SPEC.strip():
        for item in [p.strip() for p in APP_LINKS_SPEC.split(";") if p.strip()]:
            if "|" in item:
                label, url = item.split("|", 1)
                link_buttons.append(
                    dbc.Button(
                        label.strip(),
                        href=url.strip(),
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="me-2",
                        target="_blank"
                    )
                )
    links_bar = html.Div(link_buttons, className="mb-1") if link_buttons else None

    return html.Div([title_block, links_bar, notice])

# ============================================================
# Sidebar (STATIC) and Layout with Tabs
# ============================================================
def sidebar_static():
    return dbc.Card([
        dbc.CardHeader("Filters"),
        dbc.CardBody([
            html.Small(f"Loaded: {LAST_SOURCE or 'N/A'}", className="text-muted"),
            html.Hr(),

            html.Label("Company"),
            dcc.Dropdown(options=COMPANIES, value=COMPANY_DEFAULT, id="f-company", multi=True, placeholder="All companies"),

            html.Label("Province", style={"marginTop":"8px"}),
            dcc.Dropdown(options=PROVINCES, value=PROVINCE_DEFAULT, id="f-province", multi=True),

            html.Label("Sector", style={"marginTop":"8px"}),
            dcc.Dropdown(options=SECTORS, value=SECTOR_DEFAULT, id="f-sector", multi=True),

            html.Label("Group", style={"marginTop":"8px"}),
            dcc.Dropdown(options=GROUPS, value=GROUP_DEFAULT, id="f-group", multi=True),

            html.Label("Cleantech (All / Yes / No)", style={"marginTop":"8px"}),
            dcc.Dropdown(options=["All","Yes","No"], value=CLEAN_DEFAULT, id="f-cleantech", multi=True),

            html.Label("Status (end_status)", style={"marginTop":"8px"}),
            dcc.Dropdown(options=STATUSES, value=STATUS_DEFAULT, id="f-status", multi=True),

            html.Hr(),
            html.Label("Company / Project"),
            html.Label("Select by Company", style={"marginTop":"4px"}),
            dcc.Dropdown(options=COMPANIES, value=COMP_SEL_DEFAULT, id="f-company-select", multi=True, placeholder="Optional"),
            html.Label("Select by Project Name", style={"marginTop":"8px"}),
            dcc.Dropdown(options=PROJECTS, value=PROJ_SEL_DEFAULT, id="f-project-select", multi=True, placeholder="Optional"),

            html.Hr(),
            html.Label("Year Range"),
            dcc.RangeSlider(MIN_YEAR, MAX_YEAR, value=[MIN_YEAR, MAX_YEAR], id="f-year", tooltip={"placement":"bottom"}, step=1, marks=build_year_marks(MIN_YEAR, MAX_YEAR)),

            html.Label("Cost Range (C$ MM)", style={"marginTop":"8px"}),
            dcc.RangeSlider(MIN_COST, MAX_COST, value=[MIN_COST, MAX_COST], id="f-cost", tooltip={"placement":"bottom"}),

            # hidden placeholder to preserve signature if used elsewhere
            dcc.Checklist(id="f-logcost", options=[{"label":"(hidden)","value":"log"}], value=[], style={"display":"none"}),

            html.Hr(),
            html.Div([
                html.Label("Count vs Cost (some charts)"),
                dcc.RadioItems(id="agg-mode", options=[{"label":"Count","value":"count"},{"label":"Cost","value":"cost"}], value=AGG_DEFAULT, inline=True),
            ]),

            html.Label("Top-N (Power Ranking)"),
            dcc.Slider(min=5, max=20, step=None, value=TOPN_DEFAULT, marks={5:"5",10:"10",15:"15",20:"20"}, id="top-n"),

            html.Div([
                html.Button("Reset All", id="btn-reset", className="btn btn-outline-secondary", style={"marginTop":"10px","marginRight":"8px"}),
                html.Button("Download filtered CSV", id="btn-download", className="btn btn-primary", style={"marginTop":"10px"}),
                dcc.Download(id="download-dataframe-csv"),
            ]),
        ])
    ], style={"height":"100%"} )

def kpi_row():
    center_style = {"textAlign":"center"}
    return dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Projects (Pre-Construction)", style=center_style), dbc.CardBody(html.H4(id="kpi-total", className="card-title", style=center_style))])),
        dbc.Col(dbc.Card([dbc.CardHeader("Total Investment (C$ MM)",        style=center_style), dbc.CardBody(html.H4(id="kpi-invest", className="card-title", style=center_style))])),
        dbc.Col(dbc.Card([dbc.CardHeader("Probability of Construction (≤3 Years)", style=center_style), dbc.CardBody(html.H4(id="kpi-prob", className="card-title", style=center_style))])),
        dbc.Col(dbc.Card([dbc.CardHeader("Expected Value (C$ MM, 2025–27)", style=center_style), dbc.CardBody(html.H4(id="kpi-evcum", className="card-title", style=center_style))])),
        dbc.Col(dbc.Card([dbc.CardHeader("Risk-Adjusted Break-Even Multiple", style=center_style), dbc.CardBody(html.H4(id="kpi-kstar", className="card-title", style=center_style))])),
    ])

def tabs():
    return dcc.Tabs(id="tabs", value="tab-exec", children=[
        dcc.Tab(label="Executive View", value="tab-exec"),
        dcc.Tab(label="Probability & Priority", value="tab-1"),
        dcc.Tab(label="Power Ranking", value="tab-2"),
        dcc.Tab(label="Facts & Figures", value="tab-3"),
        dcc.Tab(label="Map", value="tab-4"),
        dcc.Tab(label="Stage Flow", value="tab-5"),
    ])

# ===== Layout: header full-width, KPIs full-width, then sidebar + tabs aligned =====
app.layout = dbc.Container([
    dcc.Store(id="filtered"),
    # Header & description now full width
    dbc.Row([dbc.Col(header(), width=12)], align="center", className="mt-2"),
    # KPIs spread across the full page width
    dbc.Row([dbc.Col(kpi_row(), width=12)], className="mt-2"),
    # Sidebar flush with tabs (KPIs are above this row)
    dbc.Row([
        dbc.Col(sidebar_static(), width=3),
        dbc.Col([tabs(), html.Div(id="tab-content")], width=9)
    ], className="mt-2"),
    # Schema / init message (kept, moved below for full-width header)
    dbc.Row([dbc.Col(html.Div(SCHEMA_INIT_MSG, id="schema-msg", className="text-danger"), width=12)])
], fluid=True)

# ============================================================
# Reset All (no sidebar rebuild)
# ============================================================
@app.callback(
    Output("f-company", "value"),
    Output("f-province", "value"),
    Output("f-sector", "value"),
    Output("f-group", "value"),
    Output("f-cleantech", "value"),
    Output("f-status", "value"),
    Output("f-company-select", "value"),
    Output("f-project-select", "value"),
    Output("f-year", "value"),
    Output("f-cost", "value"),
    Output("agg-mode", "value"),
    Output("top-n", "value"),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True
)
def do_reset(n):
    return (
        COMPANY_DEFAULT,
        PROVINCE_DEFAULT,
        SECTOR_DEFAULT,
        GROUP_DEFAULT,
        CLEAN_DEFAULT,
        STATUS_DEFAULT,
        COMP_SEL_DEFAULT,
        PROJ_SEL_DEFAULT,
        [MIN_YEAR, MAX_YEAR],
        [MIN_COST, MAX_COST],
        AGG_DEFAULT,
        TOPN_DEFAULT,
    )

# ============================================================
# Filtering (no sidebar rebuild)
# ============================================================
@app.callback(
    Output("filtered", "data"),
    Output("schema-msg", "children"),
    Input("f-company", "value"),
    Input("f-province", "value"),
    Input("f-sector", "value"),
    Input("f-group", "value"),
    Input("f-cleantech", "value"),
    Input("f-status", "value"),
    Input("f-company-select", "value"),
    Input("f-project-select", "value"),
    Input("f-year", "value"),
    Input("f-cost", "value"),
)
def compute_filtered(companies, provinces, sectors, groups, cleantechs, statuses, comp_sel, proj_sel, years, costs):
    try:
        raw = _coerce_types(_load_default_or_raise())
        if "urgency_scale_(0-1)" in raw.columns:
            raw["priority_index"] = pd.to_numeric(raw["urgency_scale_(0-1)"], errors="coerce").clip(0,1)
        df = add_display_columns(raw)

        schema_msg = ""
    except Exception as e:
        empty = pd.DataFrame(columns=REQUIRED_COLUMNS)
        return empty.to_json(date_format="iso", orient="split"), str(e)

    def _apply_in(frame, col, selected):
        if selected is None or len(selected) == 0:
            return frame
        return frame[frame[col].astype(str).isin([str(s) for s in selected])]

    # Apply filters (Company/Project first)
    df = _apply_in(df, "company", companies)
    df = _apply_in(df, "company", comp_sel)
    df = _apply_in(df, "project", proj_sel)
    df = _apply_in(df, "province", provinces)
    df = _apply_in(df, "sector", sectors)
    df = _apply_in(df, "group", groups)

    if cleantechs and "All" not in cleantechs:
        df = _apply_in(df, "cleantech", cleantechs)

    df = _apply_in(df, "end_status", statuses)

    if years:
        df = df[(df["start_year"] >= years[0]) & (df["end_year"] <= years[1])]
    if costs is not None:
        df = df[(df["project_cost"] >= costs[0]) & (df["project_cost"] <= costs[1])]

    return df.to_json(date_format="iso", orient="split"), schema_msg


# ============================================================
# KPIs (total projects, total investment, avg probability)
# ============================================================
@app.callback(
    Output("kpi-total", "children"),
    Output("kpi-invest", "children"),
    Output("kpi-prob", "children"),
    Output("kpi-evcum", "children"),
    Output("kpi-kstar", "children"),
    Input("filtered", "data")
)
def update_kpis(filtered_json):
    if not filtered_json:
        return "-", "-", "-", "-", "-"
    df = pd.read_json(filtered_json, orient="split")
    if df.empty:
        return "0", "0", "0%", "0", "0×"

    # Existing KPIs
    total_projects = len(df)
    total_investment_mm = f"{int(pd.to_numeric(df['project_cost'], errors='coerce').fillna(0).sum()):,}" if 'project_cost' in df.columns else "0"
    prob = pd.to_numeric(df.get("blended_prob", pd.Series(dtype=float)), errors="coerce")
    prob_pct = int(round(prob.mean() * 100, 0)) if prob.notna().any() else 0

    # NEW: Expected Value (EV_cum in C$ MM, 2025–27)
    evcum_series = pd.to_numeric(df.get("EV_cum", pd.Series(dtype=float)), errors="coerce")
    evcum_mm = f"{int(round(evcum_series.fillna(0).sum(), 0)):,}" if evcum_series.notna().any() else "0"

    # NEW: Risk-Adjusted Break-Even Multiple (median k_star_adj)
    kstar_series = pd.to_numeric(df.get("k_star_adj", pd.Series(dtype=float)), errors="coerce")
    if kstar_series.notna().any():
        kstar_med = f"{kstar_series.median():.1f}×"
    else:
        kstar_med = "0×"

    return f"{total_projects:,}", total_investment_mm, f"{prob_pct}%", evcum_mm, kstar_med

# ============================================================
# Hovers & shared customdata (unchanged visuals)
# ============================================================
def build_common_customdata(df: pd.DataFrame):
    cols = ["company","project","province","sector","group",
            "cost_mm","blended_prob_2dp","priority_index_2dp","power_ranking_2dp"]
    tmp = df.copy()
    for c in cols:
        if c not in tmp.columns:
            tmp[c] = None
    import numpy as _np
    return _np.stack([
        tmp["company"].astype(object).to_numpy(),
        tmp["project"].astype(object).to_numpy(),
        tmp["province"].astype(object).to_numpy(),
        tmp["sector"].astype(object).to_numpy(),
        tmp["group"].astype(object).to_numpy(),
        tmp["cost_mm"].to_numpy(),
        tmp["blended_prob_2dp"].to_numpy(),
        tmp["priority_index_2dp"].to_numpy(),
        tmp["power_ranking_2dp"].to_numpy()
    ], axis=-1)

COMMON_HOVER_TMPL = (
    "<b>%{customdata[1]}</b><br>"
    "Company: %{customdata[0]}<br>"
    "Province: %{customdata[2]}<br>"
    "Sector: %{customdata[3]}<br>"
    "Group: %{customdata[4]}<br>"
    "Cost (C$ MM): %{customdata[5]:,.0f}<br>"
    "Probability of Construction (≤ 3 Years): %{customdata[6]:.2f}<br>"
    "Priority (Time-to-Event Urgency): %{customdata[7]:.2f}<br>"
    "Power Ranking: %{customdata[8]:.2f}"
    "<extra></extra>"
)

def quadrant_labels_flushed(fig):
    y_bottom = -0.14
    y_top = 1.08
    ann = [
        dict(xref="paper", yref="paper", x=1.0, y=y_top, xanchor="right", yanchor="bottom",
             text="<b>HIGH PROBABILITY</b><br><i>HIGH PRIORITY</i>", bgcolor="white",
             bordercolor="#2ca02c", borderwidth=2, font=dict(size=11), showarrow=False),
        dict(xref="paper", yref="paper", x=0.0, y=y_top, xanchor="left", yanchor="bottom",
             text="<b>HIGH PROBABILITY</b><br><i>LOW PRIORITY</i>", bgcolor="white",
             bordercolor="#1f77b4", borderwidth=2, font=dict(size=11), showarrow=False),
        dict(xref="paper", yref="paper", x=1.0, y=y_bottom, xanchor="right", yanchor="top",
             text="<b>LOW PROBABILITY</b><br><i>HIGH PRIORITY</i>", bgcolor="white",
             bordercolor="#ff7f0e", borderwidth=2, font=dict(size=11), showarrow=False),
        dict(xref="paper", yref="paper", x=0.0, y=y_bottom, xanchor="left", yanchor="top",
             text="<b>LOW PROBABILITY</b><br><i>LOW PRIORITY</i>", bgcolor="white",
             bordercolor="#d62728", borderwidth=2, font=dict(size=11), showarrow=False),
    ]
    fig.update_layout(annotations=ann, margin=dict(l=100, r=100, t=110, b=110))

# ===== Exec View (inlined) =====
_FMT_INT0 = lambda v: f"{int(round(v, 0)):,}"

def _as_num(s):
    return pd.to_numeric(s, errors="coerce")

def _notes_block(title: str, body_md: str, block_id: str):
    # Simple collapsible notes; caller ensures unique block_id
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
    fig.update_yaxes(categoryorder="total ascending", automargin=True)  # ensure space for labels
    return _style_common(fig, "Cumulative EV by Province")

# =======================================
# 3) Cumulative EV by Top-10 Group + Other
# =======================================
def make_cum_ev_by_top_groups(df: pd.DataFrame, topn: int = 10) -> go.Figure:
    bucket = _top10_groups_map(df, topn)
    g = df.assign(group_bucket=bucket).groupby("group_bucket", dropna=False)["EV_cum"].sum()
    g = g.sort_values(ascending=False).reset_index()
    # Wrap long category names
    g["group_bucket_wrapped"] = g["group_bucket"].apply(lambda s: _wrap_label(s, 14))
    fig = px.bar(g, x="EV_cum", y="group_bucket_wrapped", orientation="h", text=g["EV_cum"].map(_FMT_INT0))
    fig.update_traces(textposition="outside")
    _millions_axis(fig, axis="x")
    fig.update_yaxes(categoryorder="total ascending", automargin=True)
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
    # Wrap long category names
    g["group_bucket_wrapped"] = g["group_bucket"].apply(lambda s: _wrap_label(s, 14))
    fig = px.bar(g, x="ratio", y="group_bucket_wrapped", orientation="h", text=g["ratio"].map(_FMT_INT0))
    fig.update_traces(textposition="outside")
    _millions_axis(fig, axis="x")
    fig.update_layout(xaxis_title="Median EV per Expected FID (C$ MM)")
    fig.update_yaxes(categoryorder="total ascending", automargin=True)
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

    # Wrap column labels to avoid title run-in
    wrapped_cols = [_wrap_label(c, 12) for c in z.columns]
    z.columns = wrapped_cols

    text = z.applymap(lambda v: "" if v == 0 else f"{int(round(v,0)):,}")
    fig = px.imshow(z, text_auto=False, aspect="auto", color_continuous_scale="Blues")
    fig.update_traces(text=text.values, xgap=1, ygap=1)

    # Apply the common style first
    fig = _style_common(fig, "Heat Map — Cumulative EV by Group and Province")

    # Prevent title/label run-in on top x-axis
    fig.update_layout(
        # override _style_common's t=60
        margin=dict(t=140, r=25, b=60, l=90),
        title=dict(x=0, xanchor="left", y=0.995, yanchor="top", pad=dict(t=6, b=0)),
        coloraxis_colorbar=dict(title="C$ MM", lenmode="pixels", len=220)
    )
    fig.update_xaxes(side="top", tickangle=0, automargin=True)
    fig.update_yaxes(autorange="reversed", automargin=True)

    return fig

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

    # Wrap column labels to avoid title run-in
    wrapped_cols = [_wrap_label(c, 12) for c in z.columns]
    z.columns = wrapped_cols

    fig = px.imshow(z, text_auto=False, aspect="auto",
                    color_continuous_scale="Reds", zmin=cmin, zmax=cmax)
    fig.update_traces(
        text=text.values,
        hovertemplate="Province %{y}<br>Group %{x}<br>RABE-MOIC: %{z:.1f}×<extra></extra>",
        xgap=1, ygap=1
    )

    # Apply the common style first
    fig = _style_common(fig, "Heat Map — Risk-Adjusted Break-Even Multiple by Group and Province")

    # Prevent title/label run-in on top x-axis
    fig.update_layout(
        margin=dict(t=140, r=25, b=60, l=90),  # override _style_common
        title=dict(x=0, xanchor="left", y=0.995, yanchor="top", pad=dict(t=6, b=0)),
        coloraxis_colorbar=dict(title="Multiple (× DevCost)", lenmode="pixels", len=220)
    )
    fig.update_xaxes(side="top", tickangle=0, automargin=True)
    fig.update_yaxes(autorange="reversed", automargin=True)

    return fig

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

    # Notes placeholders (kept as in original)
    notes1 = _notes_block("Notes-1", "Add your short methods note here (softmax year allocation; sums of annual probabilities).", "notes-1")
    notes2 = _notes_block("Notes-2", "Add context on province EV aggregation and units (C$ MM).", "notes-2")
    notes3 = _notes_block("Notes-3", "Explain Top-10 + Other construction (based on filtered EV_cum).", "notes-3")
    notes4 = _notes_block("Notes-4", "Median of project-level EV/FID ratios; denominator is Σ annual_p_YYYY.", "notes-4")
    notes5 = _notes_block("Notes-5", "Same ratio as above, bucketed by Top-10 + Other.", "notes-5")
    notes6 = _notes_block("Notes-6", "Zeros hidden in cell text; hover still shows 0; province alphabetical.", "notes-6")
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


# ============================================================
# Tabs (preserved)
# ============================================================
@app.callback(
    Output("tab-content", "children"),
    Input("filtered", "data"),
    Input("tabs", "value"),
    Input("agg-mode", "value"),
    Input("top-n", "value"),
    Input("f-logcost", "value")
)
def render_tabs(filtered_json, active_tab, agg_mode, topn, logcost):
    if not filtered_json:
        return html.Div("No data with current filters.", className="text-muted")
    df = pd.read_json(filtered_json, orient="split")
    if df.empty:
        return html.Div("No data with current filters.", className="text-muted")

    cmap = sector_color_map(df)
    template = "plotly"

    if active_tab == "tab-exec":
        content = render_exec_view(df, topn=topn)

    elif active_tab == "tab-1":
        fig_scatter = px.scatter(
            df,
            x="priority_index_2dp",
            y="blended_prob_2dp",
            color="sector",
            color_discrete_map=cmap,
            size="project_cost",
            size_max=22,
            labels={
                "priority_index_2dp": "Priority Index (Time to Event Urgency)",
                "blended_prob_2dp": "Probability of Construction (≤ 3 Years)"
            },
            template=template,
            height=700
        )
        attach_customdata_by_trace(fig_scatter, df, color_col="sector")
        fig_scatter.update_layout(hoverlabel=dict(bgcolor="white", font_size=12))
        fig_scatter.update_xaxes(tickformat=".2f")
        fig_scatter.update_yaxes(tickformat=".2f")
        if len(df):
            x_med = df["priority_index"].mean()
            y_med = df["blended_prob"].mean()
            fig_scatter.add_vline(x=x_med, line_dash="dash", line_color="black")
            fig_scatter.add_hline(y=y_med, line_dash="dash", line_color="black")
            quadrant_labels_flushed(fig_scatter)

        content = html.Div([ dcc.Graph(figure=fig_scatter) ])

    elif active_tab == "tab-2":
        # Build Top-N bars: Power Ranking, Probability, Priority Index
        score = normalize_power_score(df["power_ranking"] if "power_ranking" in df.columns else pd.Series(dtype=float))
        tmp = df.copy()
        tmp["score01"] = score
        tmp["prob2dp"] = pd.to_numeric(tmp["blended_prob"], errors="coerce").round(2)
        tmp["cost_mm"] = pd.to_numeric(tmp["project_cost"], errors="coerce").round(0).astype("Int64")
        tmp["label"] = tmp["project"].apply(lambda x: truncate(x, 36))

        N = topn if topn else 10

        # Top-N by Power Ranking
        top_power = tmp.sort_values("score01", ascending=False).head(N)
        fig_power = go.Figure()
        fig_power.add_trace(go.Bar(
            x=top_power["score01"],
            y=top_power["label"],
            orientation="h",
            text=top_power["score01"].map(lambda v: f"{v:.2f}"),
            textposition="auto",
            customdata=build_common_customdata(top_power),
            hovertemplate=COMMON_HOVER_TMPL
        ))
        fig_power.update_layout(
            title=f"Top {N} by Power Ranking",
            xaxis=dict(range=[0,1], title="Score (0–1)"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10,r=10,t=50,b=40),
            template=template
        )

        # Top-N by Probability
        top_prob = tmp.sort_values("prob2dp", ascending=False).head(N)
        fig_prob = go.Figure()
        fig_prob.add_trace(go.Bar(
            x=top_prob['prob2dp'],
            y=top_prob['label'],
            orientation='h',
            text=top_prob['prob2dp'].map(lambda v: f"{v:.2f}"),
            textposition='auto',
            customdata=build_common_customdata(top_prob),
            hovertemplate=COMMON_HOVER_TMPL
        ))
        fig_prob.update_layout(
            title=f"Top {N} by Probability of Construction (≤ 3 Years)",
            xaxis=dict(range=[0,1], title="Probability (0–1)"),
            yaxis=dict(autorange='reversed'),
            margin=dict(l=10,r=10,t=50,b=40),
            template=template
        )

        # Top-N by Priority Index (uses urgency_scale_(0-1) mapped to priority_index)
        top_prio = tmp.sort_values('priority_index', ascending=False).head(N)
        fig_prio = go.Figure()
        fig_prio.add_trace(go.Bar(
            x=pd.to_numeric(top_prio['priority_index'], errors='coerce'),
            y=top_prio['label'],
            orientation='h',
            text=top_prio['priority_index'].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else ""),
            textposition='auto',
            customdata=build_common_customdata(top_prio),
            hovertemplate=COMMON_HOVER_TMPL
        ))
        fig_prio.update_layout(
            title=f"Top {N} by Priority Index (Time to Event Urgency)",
            xaxis=dict(range=[0,1], title="Priority Index"),
            yaxis=dict(autorange='reversed'),
            margin=dict(l=10,r=10,t=50,b=40),
            template=template
        )

        content = html.Div([
            dcc.Graph(figure=fig_power),
            html.Br(),
            dcc.Graph(figure=fig_prob),
            html.Br(),
            dcc.Graph(figure=fig_prio),
        ])

    elif active_tab == "tab-3":
        template = "plotly"
        cmap = sector_color_map(df)

        # Ensure numeric project_cost
        if "project_cost" in df.columns:
            df["project_cost"] = pd.to_numeric(df["project_cost"], errors="coerce")

        # Decide aggregation based on agg_mode
        use_cost = (agg_mode == "cost")
        val_col  = "project_cost" if use_cost else "count"
        y_label_sector = "Total Project Value (C$ MM)" if use_cost else "Project Count"
        y_label_prov   = "Total Project Value (C$ MM)" if use_cost else "Project Count"
        title_suffix   = " (Cost)" if use_cost else " (Count)"
        pie_title_ct   = "Project Value by Cleantech (C$ MM)" if use_cost else "Project Count by Cleantech"
        pie_title_own  = "Project Value by Ownership (C$ MM)" if use_cost else "Project Count by Ownership"
        vintage_ylabel = "Total Project Value (C$ MM)" if use_cost else "Project Count"
        vintage_title  = "Projects by Vintage (stacked by Sector)" + title_suffix

        # ---------- Row 1 (toggle Count/Cost) ----------
        if use_cost:
            g1 = df.groupby(["sector","group"], dropna=False)["project_cost"].sum().reset_index(name="project_cost")
            g2 = df.groupby(["province","sector"], dropna=False)["project_cost"].sum().reset_index(name="project_cost").sort_values("province")
        else:
            g1 = df.groupby(["sector","group"], dropna=False).size().reset_index(name="count")
            g2 = df.groupby(["province","sector"], dropna=False).size().reset_index(name="count").sort_values("province")

        fig_sector_group = px.bar(
            g1, x="sector", y=val_col, color="group", barmode="stack",
            template=template, title=f"Projects by Sector (stacked by Group){title_suffix}",
        )
        fig_sector_group.update_yaxes(title=y_label_sector)

        fig_prov_sector = px.bar(
            g2, x="province", y=val_col, color="sector", barmode="stack",
            color_discrete_map=cmap, template=template,
            title=f"Projects by Province (stacked by Sector){title_suffix}",
        )
        fig_prov_sector.update_yaxes(title=y_label_prov)

        # ---------- Row 2 (totals remain fixed to Cost per your spec) ----------
        g3 = df.groupby("sector", dropna=False)["project_cost"].sum().reset_index()
        fig_cost_sector = px.bar(g3, x="sector", y="project_cost", template=template,
                                 title="Total Project Value by Sector (C$ MM)")

        g4 = df.groupby("province", dropna=False)["project_cost"].sum().reset_index()
        fig_cost_prov = px.bar(g4, x="province", y="project_cost", template=template,
                               title="Total Project Value by Province (C$ MM)")

        # ---------- Row 3 (toggle Count/Cost in donuts) ----------
        if use_cost:
            g5 = df.groupby("cleantech", dropna=False)["project_cost"].sum().reset_index(name="project_cost")
        else:
            g5 = df.groupby("cleantech", dropna=False).size().reset_index(name="count")
        fig_cleantech = px.pie(
            g5, names="cleantech", values=("project_cost" if use_cost else "count"), hole=0.55,
            title=pie_title_ct, template=template
        )

        if "company_type" in df.columns:
            if use_cost:
                g6 = df.groupby("company_type", dropna=False)["project_cost"].sum().reset_index(name="project_cost")
            else:
                g6 = df.groupby("company_type", dropna=False).size().reset_index(name="count")
            fig_ownership = px.pie(
                g6, names="company_type", values=("project_cost" if use_cost else "count"), hole=0.55,
                title=pie_title_own, template=template
            )
        else:
            fig_ownership = go.Figure().update_layout(title=pie_title_own + " (company_type missing)")

        # ---------- Row 4 (toggle Count/Cost on Vintage) ----------
        dsy = df.dropna(subset=["start_year"])
        if use_cost:
            g7 = dsy.groupby(["start_year","sector"], dropna=False)["project_cost"].sum().reset_index(name="project_cost")
        else:
            g7 = dsy.groupby(["start_year","sector"], dropna=False).size().reset_index(name="count")

        fig_vintage = px.bar(
            g7, x="start_year", y=("project_cost" if use_cost else "count"),
            color="sector", barmode="stack",
            color_discrete_map=cmap, template=template, title=vintage_title
        )
        fig_vintage.update_yaxes(title=vintage_ylabel)

        content = html.Div([
            dbc.Row([dbc.Col(dcc.Graph(figure=fig_sector_group), width=6),
                     dbc.Col(dcc.Graph(figure=fig_prov_sector),   width=6)]),
            html.Br(),
            dbc.Row([dbc.Col(dcc.Graph(figure=fig_cost_sector),  width=6),
                     dbc.Col(dcc.Graph(figure=fig_cost_prov),    width=6)]),
            html.Br(),
            dbc.Row([dbc.Col(dcc.Graph(figure=fig_cleantech),    width=6),
                     dbc.Col(dcc.Graph(figure=fig_ownership),    width=6)]),
            html.Br(),
            dbc.Row([dbc.Col(dcc.Graph(figure=fig_vintage),      width=12)]),
        ])

    
    elif active_tab == "tab-4":
        for col in ["latitude_1", "longitude_1"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        dfm = df.dropna(subset=["latitude_1","longitude_1"])
        if dfm.empty:
            fig_map = px.scatter_mapbox(lat=[56], lon=[-96], zoom=2, height=600, template=template)
            fig_map.update_layout(mapbox_style="open-street-map", title="Project Map", hoverlabel=dict(bgcolor="white", font_size=12))
            fig_map.add_annotation(text="No geocoded points in current filters", x=0.5, xref="paper", y=0.5, yref="paper", showarrow=False)
            content = dcc.Graph(figure=fig_map)
        else:
            dfm2 = dfm.copy()
            dfm2["project_cost"] = pd.to_numeric(dfm2["project_cost"], errors="coerce")
            fill_val = float(dfm2["project_cost"].median()) if dfm2["project_cost"].notna().any() else 1.0
            dfm2["project_cost"] = dfm2["project_cost"].fillna(fill_val)

            # Precompute pixel sizes to enforce a minimum of 8px (and ~22px max)
            cmin = float(dfm2["project_cost"].min())
            cmax = float(dfm2["project_cost"].max())
            if not (cmax > cmin):
                scale = (dfm2["project_cost"]*0 + 1.0)
            else:
                scale = (dfm2["project_cost"] - cmin) / (cmax - cmin)
            dfm2["bubble_size"] = 8.0 + 14.0 * scale  # 8..22 px

            fig_map = px.scatter_mapbox(
                dfm2, lat="latitude_1", lon="longitude_1",
                color="sector", color_discrete_map=cmap,
                size="bubble_size",
                zoom=2, height=600, template=template
            )
            fig_map.update_layout(mapbox_style="open-street-map", title="Project Map", hoverlabel=dict(bgcolor="white", font_size=12))
            attach_customdata_by_trace(fig_map, dfm2, color_col="sector")
            content = dcc.Graph(figure=fig_map)

    else:
        try:
            links = df.groupby(["start_status","end_status"]).size().reset_index(name="value")
            nodes = pd.Index(sorted(set(links["start_status"]).union(set(links["end_status"])))).tolist()
            l2i = {l:i for i,l in enumerate(nodes)}
            src = [l2i[s] for s in links["start_status"]]
            tgt = [l2i[t] for t in links["end_status"]]
            vals = links["value"].tolist()
            labels = nodes
        except Exception:
            src=tgt=vals=[]
            labels=["No data"]
        fig_sankey = go.Figure(data=[go.Sankey(
            node=dict(pad=12, thickness=12, line=dict(color="black", width=0.5), label=labels),
            link=dict(source=src, target=tgt, value=vals)
        )])
        fig_sankey.update_layout(title_text="Stage Flow: Start → End Status", font_size=12, template=template)
        content = dcc.Graph(figure=fig_sankey)

    return content

# ============================================================
# Download filtered CSV (unchanged)
# ============================================================
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download", "n_clicks"),
    State("filtered", "data"),
    prevent_initial_call=True
)
def download_csv(n, filtered_json):
    if not n or not filtered_json:
        return
    df = pd.read_json(filtered_json, orient="split")
    return dcc.send_data_frame(df.to_csv, "filtered_projects.csv", index=False)

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=7860, debug=False)
