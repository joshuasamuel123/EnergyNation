
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

HERE = Path(__file__).parent
LAST_SOURCE = None
LAST_ERRORS = []

def _xlsx_in_here():
    # Ignore temporary Excel files like "~$foo.xlsx"
    return sorted([p for p in HERE.glob("*.xlsx") if not p.name.startswith("~$")])

# Optional override via env var: DATAFILE=mpi_2024_scored.xlsx
_ENV_CHOICE = os.getenv("DATAFILE")

# Preference order: env var (if provided), then these names if present, then any other *.xlsx
_PREFERRED_NAMES = ["mpi_2024_scored.xlsx", "sample_mpi.xlsx"]

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

# ============================================================
# App init & sidebar defaults (static)
# ============================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.config.suppress_callback_exceptions = True
server = app.server

try:
    INIT_DF = add_display_columns(_coerce_types(_load_default_or_raise()))
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

            html.Label("Cost Range (CAD$ MM)", style={"marginTop":"8px"}),
            dcc.RangeSlider(MIN_COST, MAX_COST, value=[MIN_COST, MAX_COST], id="f-cost", tooltip={"placement":"bottom"}),

            # hidden placeholder to preserve signature if used elsewhere
            dcc.Checklist(id="f-logcost", options=[{"label":"(hidden)","value":"log"}], value=[], style={"display":"none"}),

            html.Hr(),
            html.Div([
                html.Label("Count vs Cost (some charts)"),
                dcc.RadioItems(id="agg-mode", options=[{"label":"Count","value":"count"},{"label":"Cost","value":"cost"}], value=AGG_DEFAULT, inline=True),
            ]),

            html.Label("Top‑N (Power Ranking)"),
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
        dbc.Col(dbc.Card([dbc.CardHeader("Total Investment (CAD$ MM)", style=center_style), dbc.CardBody(html.H4(id="kpi-invest", className="card-title", style=center_style))])),
        dbc.Col(dbc.Card([dbc.CardHeader("Probability of Construction (≤3 Years)", style=center_style), dbc.CardBody(html.H4(id="kpi-prob", className="card-title", style=center_style))])),
    ])

def tabs():
    return dcc.Tabs(id="tabs", value="tab-1", children=[
        dcc.Tab(label="Probability & Ranking", value="tab-1"),
        dcc.Tab(label="Sector & Cleantech", value="tab-2"),
        dcc.Tab(label="Start-Year & Cost", value="tab-3"),
        dcc.Tab(label="Map", value="tab-4"),
        dcc.Tab(label="Stage Flow", value="tab-5"),
    ])

app.layout = dbc.Container([
    dcc.Store(id="filtered"),
    dbc.Row([
        dbc.Col(html.H3("Canada Major Projects Inventory 2024 — Pre-Construction Dashboard"), width=9),
        dbc.Col(html.Div(SCHEMA_INIT_MSG, id="schema-msg", className="text-danger"), width=3)
    ], align="center", className="mt-2"),
    dbc.Row([
        dbc.Col(sidebar_static(), width=3),
        dbc.Col([kpi_row(), html.Br(), tabs(), html.Div(id="tab-content")], width=9)
    ], className="mt-2")
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
        df = add_display_columns(_coerce_types(_load_default_or_raise()))
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
    Input("filtered", "data")
)
def update_kpis(filtered_json):
    if not filtered_json:
        return "-", "-", "-"
    df = pd.read_json(filtered_json, orient="split")
    if df.empty:
        return "0", "0", "0%"
    total_projects = len(df)
    total_investment_b = pd.to_numeric(df["project_cost"], errors="coerce").fillna(0).sum()
    try:
        total_investment_mm = f"{int(round(total_investment_b, 0)):,}"
    except Exception:
        total_investment_mm = "0"
    prob = pd.to_numeric(df["blended_prob"], errors="coerce")
    prob_pct = int(round(prob.mean() * 100, 0)) if prob.notna().any() else 0
    return f"{total_projects:,}", total_investment_mm, f"{prob_pct}%"
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
    "Cost (CAD$ MM): %{customdata[5]:,.0f}<br>"
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

    if active_tab == "tab-1":
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

        score = normalize_power_score(df["power_ranking"] if "power_ranking" in df.columns else pd.Series(dtype=float))
        tmp = df.copy()
        tmp["score01"] = score
        tmp["prob2dp"] = df["blended_prob"].round(2)
        tmp["cost_mm"] = (df["project_cost"] * 1).round(0).astype("Int64")
        tmp["label"] = tmp["project"].apply(lambda x: truncate(x, 36))

        top = tmp.sort_values("score01", ascending=False).head(topn if topn else 10)

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=top["score01"],
            y=top["label"],
            orientation="h",
            text=top["score01"].map(lambda v: f"{v:.2f}"),
            textposition="auto",
            customdata=build_common_customdata(top),
            hovertemplate=COMMON_HOVER_TMPL
        ))
        fig_bar.update_layout(
            title=f"Top {topn if topn else 10} by Power Ranking",
            xaxis=dict(range=[0,1], title="Score (0–1)"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10,r=10,t=50,b=40),
            template=template
        )

        # Build Top‑N Probability and Priority
        score = normalize_power_score(df["power_ranking"] if "power_ranking" in df.columns else pd.Series(dtype=float))
        tmp2 = df.copy()
        tmp2["score01"] = score
        tmp2["prob2dp"] = pd.to_numeric(tmp2["blended_prob"], errors="coerce").round(2)
        tmp2["cost_mm"] = pd.to_numeric(tmp2["project_cost"], errors="coerce").round(0).astype("Int64")
        tmp2["label"] = tmp2["project"].apply(lambda x: truncate(x, 36))

        # Top‑N by Probability
        prob_sorted = tmp2.sort_values('prob2dp', ascending=False).head(topn if topn else 10)
        fig_prob = go.Figure()
        fig_prob.add_trace(go.Bar(
            x=prob_sorted['prob2dp'],
            y=prob_sorted['label'],
            orientation='h',
            text=prob_sorted['prob2dp'].map(lambda v: f"{v:.2f}"),
            textposition='auto',
            customdata=build_common_customdata(prob_sorted),
            hovertemplate=COMMON_HOVER_TMPL
        ))
        fig_prob.update_layout(
            title=f"Top {topn if topn else 10} by Probability of Construction (≤ 3 Years)",
            xaxis=dict(range=[0,1], title="Probability (0–1)"),
            yaxis=dict(autorange='reversed'),
            margin=dict(l=10,r=10,t=50,b=40),
            template=template
        )

        # Top‑N by Priority Index
        prio_sorted = tmp2.sort_values('priority_index', ascending=False).head(topn if topn else 10)
        fig_prio = go.Figure()
        fig_prio.add_trace(go.Bar(
            x=pd.to_numeric(prio_sorted['priority_index'], errors='coerce'),
            y=prio_sorted['label'],
            orientation='h',
            text=prio_sorted['priority_index'].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else ""),
            textposition='auto',
            customdata=build_common_customdata(prio_sorted),
            hovertemplate=COMMON_HOVER_TMPL
        ))
        fig_prio.update_layout(
            title=f"Top {topn if topn else 10} by Priority Index (Time to Event Urgency)",
            xaxis=dict(title="Priority Index"),
            yaxis=dict(autorange='reversed'),
            margin=dict(l=10,r=10,t=50,b=40),
            template=template
        )

        content = html.Div([
            dcc.Graph(figure=fig_scatter),
            html.Br(),
            dcc.Graph(figure=fig_bar),
            html.Br(),
            dcc.Graph(figure=fig_prob),
            html.Br(),
            dcc.Graph(figure=fig_prio),
        ])

    elif active_tab == "tab-2":
        if agg_mode == "cost":
            dfg = df.groupby(["sector","group"], dropna=False)["project_cost"].sum().reset_index()
            ycol, ylab = "project_cost", "Total Cost (B)"
        else:
            dfg = df.groupby(["sector","group"], dropna=False).size().reset_index(name="count")
            ycol, ylab = "count", "Count"
        fig_stack = px.bar(dfg, x="sector", y=ycol, color="group", barmode="stack",
                           labels={ycol: ylab}, title="Projects by Sector (stacked by Group)", template=template)

        dp = df.groupby(["province","sector"], dropna=False).size().reset_index(name="count")
        dp = dp.sort_values("province")
        fig_pxsec = px.bar(dp, x="province", y="count", color="sector", barmode="stack",
                           color_discrete_map=cmap, title="Projects by Province (stacked by Sector)", template=template)

        dct = df.groupby("cleantech").size().reset_index(name="count")
        fig_donut = px.pie(dct, names="cleantech", values="count", hole=0.55, title="Cleantech vs Not", template=template)

        content = html.Div([
            dbc.Row([dbc.Col(dcc.Graph(figure=fig_stack), width=6), dbc.Col(dcc.Graph(figure=fig_pxsec), width=6)]),
            html.Br(),
            dbc.Row([dbc.Col(dcc.Graph(figure=fig_donut), width=6)])
        ])

    elif active_tab == "tab-3":
        dsy = df.dropna(subset=["start_year"])
        dsy = dsy.groupby(["start_year","sector"], dropna=False).size().reset_index(name="count")
        fig_year = px.bar(dsy, x="start_year", y="count", color="sector", barmode="stack",
                          color_discrete_map=cmap, title="Projects Started by Year (stacked by Sector)", template=template)

        fig_hist = px.histogram(df, x="cost_mm", nbins=30, title="Project Cost Distribution (CAD$ MM)", template=template)
        fig_box = px.box(df, x="sector", y="cost_mm", title="Cost by Sector (CAD$ MM)", template=template)

        content = html.Div([
            dcc.Graph(figure=fig_year),
            html.Br(),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_hist.update_yaxes(tickformat=",")), width=6),
                dbc.Col(dcc.Graph(figure=fig_box.update_yaxes(tickformat=",")), width=6)
            ]),
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
