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
APP_TITLE = os.getenv("APP_TITLE", "Energy Nation Dashboard — MPI Probability")
APP_NOTICE_MD = os.getenv("APP_NOTICE_MD", "")  # Markdown-supported notice
APP_LINKS_SPEC = os.getenv("APP_LINKS_SPEC", "")  # "Label|URL;Label2|URL2"

HERE = Path(__file__).parent
def _xlsx_in_here():
    return sorted([p for p in HERE.glob("*.xlsx") if not p.name.startswith("~$")])

# Optional override path via env
DATAFILE = os.getenv("DATAFILE", "").strip()

# Remember last source and any load issues
LAST_SOURCE, LAST_ERRORS = None, []

def _candidate_paths():
    # Prefer a specific file name if set
    ordered = []
    if DATAFILE:
        dp = Path(DATAFILE)
        if dp.exists():
            ordered.append(dp)

    # Prefer ./data if present (skip because we want "beside" app)
    # Then prefer anything sitting next to app.py
    files_here = _xlsx_in_here()

    # If we saw a specifically named file, put it first
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
        except Exception as e:
            LAST_ERRORS.append(f"{pth.name}: {e}")
    raise FileNotFoundError(f"No suitable Excel file found next to app.py. Checked: {[str(p) for p in CANDIDATES]}")

# ============================================================
# App init
# ============================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Try to load, but do not crash the app if missing; keep a schema warning
SCHEMA_INIT_MSG = ""
try:
    df = _load_default_or_raise()
except Exception as e:
    df = pd.DataFrame()
    SCHEMA_INIT_MSG = str(e)

# ============================================================
# Data expectations and normalization
# ============================================================
EXPECTED_COLUMNS = [
    "unique_id", "company", "project", "province", "sector", "group",
    "status", "year", "project_cost", "company_type", "cleantech",
    "prob_3yr", "abbreviation"
]

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    # Lower/underscored
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
    # Fill expected columns if missing
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    # Trim whitespace for strings
    for col in ["unique_id","company","project","province","sector","group","status","company_type","cleantech","abbreviation"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Clean types
    if "year" in df.columns:
        try:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")
        except Exception:
            pass
    if "project_cost" in df.columns:
        try:
            df["project_cost"] = pd.to_numeric(df["project_cost"], errors="coerce")
        except Exception:
            pass
    if "prob_3yr" in df.columns:
        try:
            df["prob_3yr"] = pd.to_numeric(df["prob_3yr"], errors="coerce")
        except Exception:
            pass

    # Normalize cleantech to Yes/No/Unknown
    if "cleantech" in df.columns:
        df["cleantech"] = df["cleantech"].str.strip().str.title()
        df.loc[~df["cleantech"].isin(["Yes","No","Unknown"]), "cleantech"] = "Unknown"

    # Normalize company type to Public/Private/Unknown
    if "company_type" in df.columns:
        df["company_type"] = df["company_type"].str.strip().str.title()
        df.loc[~df["company_type"].isin(["Public","Private","Unknown"]), "company_type"] = "Unknown"

    # Province, Sector, Group text case
    for col in ["province", "sector", "group", "status"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.title()

    return df

df = _normalize_columns(df)

# Safe defaults if empty
if df.empty:
    # create a minimal schema so UI renders
    df = pd.DataFrame({c: [] for c in EXPECTED_COLUMNS})

# ============================================================
# Derived lists for filters
# ============================================================
COMPANIES = sorted([c for c in df["company"].dropna().unique().tolist() if c])
PROJECTS = sorted([c for c in df["project"].dropna().unique().tolist() if c])
PROVINCES = sorted([c for c in df["province"].dropna().unique().tolist() if c])
SECTORS = sorted([c for c in df["sector"].dropna().unique().tolist() if c])
GROUPS = sorted([c for c in df["group"].dropna().unique().tolist() if c])
STATUSES = sorted([c for c in df["status"].dropna().unique().tolist() if c])
COMPANY_TYPES = ["Public","Private","Unknown"]
CLEAN_TECH = ["All","Yes","No","Unknown"]

MIN_YEAR = int(pd.to_numeric(df["year"], errors="coerce").dropna().min()) if not df.empty else 2000
MAX_YEAR = int(pd.to_numeric(df["year"], errors="coerce").dropna().max()) if not df.empty else 2035
MIN_COST = int(np.nan_to_num(df["project_cost"].min(), nan=0.0)) if not df.empty else 0
MAX_COST = int(np.nan_to_num(df["project_cost"].max(), nan=0.0)) if not df.empty else 1_000_000_000

AGG_DEFAULT = "mean"
TOPN_DEFAULT = 15

def sidebar_static():
    return html.Div([
        html.H5("Filters", className="mt-2"),
        html.Label("Company"),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in COMPANIES], value=[], id="f-company", multi=True),

        html.Label("Project", style={"marginTop":"8px"}),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in PROJECTS], value=[], id="f-project", multi=True),

        html.Label("Province", style={"marginTop":"8px"}),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in PROVINCES], value=[], id="f-province", multi=True),

        html.Label("Sector", style={"marginTop":"8px"}),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in SECTORS], value=[], id="f-sector", multi=True),

        html.Label("Group", style={"marginTop":"8px"}),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in GROUPS], value=[], id="f-group", multi=True),

        html.Label("Cleantech", style={"marginTop":"8px"}),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in CLEAN_TECH], value="All", id="f-cleantech", multi=False, clearable=False),

        html.Label("Status", style={"marginTop":"8px"}),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in STATUSES], value=[], id="f-status", multi=True),

        html.Label("Company Type", style={"marginTop":"8px"}),
        dcc.Dropdown(options=[{"label": c, "value": c} for c in COMPANY_TYPES], value=[], id="f-company-type", multi=True),

        html.Label("Year Range", style={"marginTop":"8px"}),
        dcc.RangeSlider(MIN_YEAR, MAX_YEAR, value=[MIN_YEAR, MAX_YEAR], id="f-year", marks={int(y): str(int(y)) for y in range(MIN_YEAR, MAX_YEAR+1)}),

        html.Label("Project Cost Range ($)", style={"marginTop":"8px"}),
        dcc.RangeSlider(MIN_COST, MAX_COST, value=[MIN_COST, MAX_COST], id="f-cost", tooltip={"placement":"bottom"}, marks=None),

        html.Hr(),
        html.Div([
            html.Button("Reset All", id="btn-reset", className="btn btn-outline-secondary", style={"marginTop":"10px","marginRight":"8px"}),
            html.Button("Download filtered CSV", id="btn-download", className="btn btn-primary", style={"marginTop":"10px"}),
            dcc.Download(id="download-dataframe-csv"),
        ]),
    ], style={"height":"100%"} )

def kpi_row():
    center_style = {"textAlign":"center"}
    return dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Projects (Planned)"), dbc.CardBody(html.Div("0", id="kpi-total", className="card-title", style=center_style))])),
        dbc.Col(dbc.Card([dbc.CardHeader("Total Investment ($)"), dbc.CardBody(html.Div("—", id="kpi-invest", className="card-title", style=center_style))])),
        dbc.Col(dbc.Card([dbc.CardHeader("Probability of Construction (3-yr)"), dbc.CardBody(html.Div("—", id="kpi-prob", className="card-title", style=center_style))])),
    ])

def tabs():
    return dcc.Tabs(id="tabs", value="t-province", children=[
        dcc.Tab(label="Top-N by Province", value="t-province"),
        dcc.Tab(label="Top-N by Sector", value="t-sector"),
        dcc.Tab(label="Top-N by Company", value="t-company"),
        dcc.Tab(label="Top-N by Project", value="t-project"),
        dcc.Tab(label="By Cleantech & Company Type", value="t-type"),
    ])

def _filter_df(
    company, province, sector, group, cleantech, status, company_type, company_select, project_select, year_range, cost_range, agg_mode, top_n
):
    df2 = df.copy()
    # Multi filters
    if company: df2 = df2[df2["company"].isin(company)]
    if project_select: df2 = df2[df2["project"].isin(project_select)]
    if province: df2 = df2[df2["province"].isin(province)]
    if sector: df2 = df2[df2["sector"].isin(sector)]
    if group: df2 = df2[df2["group"].isin(group)]
    if status: df2 = df2[df2["status"].isin(status)]
    if company_type: df2 = df2[df2["company_type"].isin(company_type)]

    if cleantech and cleantech != "All":
        df2 = df2[df2["cleantech"] == cleantech]

    yl, yr = year_range or [MIN_YEAR, MAX_YEAR]
    df2 = df2[(df2["year"] >= yl) & (df2["year"] <= yr)]

    cl, cr = cost_range or [MIN_COST, MAX_COST]
    df2 = df2[(df2["project_cost"] >= cl) & (df2["project_cost"] <= cr)]

    # topN and aggregation will occur in graph builders
    return df2

def _agg_series(series, mode="mean"):
    s = pd.to_numeric(series, errors="coerce")
    if mode == "median":
        return float(np.nanmedian(s))
    if mode == "sum":
        return float(np.nansum(s))
    return float(np.nanmean(s))

def _build_topn(df2, group_col, agg_col="prob_3yr", mode="mean", topn=TOPN_DEFAULT):
    g = df2.groupby(group_col)[agg_col].apply(lambda s: _agg_series(s, mode)).reset_index()
    g = g.sort_values(agg_col, ascending=False).head(int(topn))
    return g

def _format_currency(x):
    try:
        return f"${int(x):,}"
    except Exception:
        return "—"

def _format_pct(x):
    try:
        return f"{100*float(x):.1f}%"
    except Exception:
        return "—"

def fig_topn_by(df2, by="province", agg_mode="mean", topn=TOPN_DEFAULT):
    g = _build_topn(df2, by, "prob_3yr", agg_mode, topn)
    fig = px.bar(g, x="prob_3yr", y=by, orientation="h", text=g["prob_3yr"].apply(lambda v: f"{100*v:.1f}%"))
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        xaxis_title="3-yr Probability",
        yaxis_title=by.title(),
        margin=dict(l=10, r=10, t=30, b=10),
        height=420
    )
    return fig

def fig_topn_by_company(df2, agg_mode="mean", topn=TOPN_DEFAULT):
    return fig_topn_by(df2, by="company", agg_mode=agg_mode, topn=topn)

def fig_topn_by_project(df2, agg_mode="mean", topn=TOPN_DEFAULT):
    return fig_topn_by(df2, by="project", agg_mode=agg_mode, topn=topn)

def fig_by_type(df2, agg_mode="mean"):
    # Cleantech Yes/No/Unknown and Company Type buckets
    cleantech_g = df2.groupby("cleantech")["prob_3yr"].apply(lambda s: _agg_series(s, agg_mode)).reset_index()
    company_g = df2.groupby("company_type")["prob_3yr"].apply(lambda s: _agg_series(s, agg_mode)).reset_index()

    cleantech_g = cleantech_g.sort_values("cleantech")
    company_g = company_g.sort_values("company_type")

    fig1 = px.bar(cleantech_g, x="prob_3yr", y="cleantech", orientation="h", text=cleantech_g["prob_3yr"].apply(lambda v: f"{100*v:.1f}%"))
    fig1.update_traces(textposition="outside", cliponaxis=False)
    fig1.update_layout(
        xaxis_title="3-yr Probability",
        yaxis_title="Cleantech",
        title="By Cleantech",
        height=360,
        margin=dict(l=10, r=10, t=30, b=10),
    )

    fig2 = px.bar(company_g, x="prob_3yr", y="company_type", orientation="h", text=company_g["prob_3yr"].apply(lambda v: f"{100*v:.1f}%"))
    fig2.update_traces(textposition="outside", cliponaxis=False)
    fig2.update_layout(
        xaxis_title="3-yr Probability",
        yaxis_title="Company Type",
        title="By Company Type",
        height=360,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig1, fig2

def controls_row():
    return dbc.Row([
        dbc.Col([
            html.Label("Aggregation", style={"marginTop":"8px"}),
            dcc.Dropdown(options=[{"label":"Mean","value":"mean"},{"label":"Median","value":"median"},{"label":"Sum","value":"sum"}], value=AGG_DEFAULT, id="agg-mode", multi=False, clearable=False),
        ], width=3),
        dbc.Col([
            html.Label("Top-N", style={"marginTop":"8px"}),
            dcc.Input(id="top-n", type="number", value=TOPN_DEFAULT, min=5, max=50, step=1, className="form-control"),
        ], width=3),
    ])

def header():
    # Title
    title_block = html.H3(APP_TITLE, className="mb-2")

    # Optional notice (Markdown allowed)
    notice = None
    if APP_NOTICE_MD.strip():
        notice = dbc.Alert(
            dcc.Markdown(APP_NOTICE_MD),
            color="warning",
            className="py-2 px-3 mb-2",
            style={"whiteSpace": "pre-wrap"}
        )

    # Optional links row — parse APP_LINKS_SPEC = "Label|URL;Label2|URL2"
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

app.layout = dbc.Container([
    dcc.Store(id="filtered"),
    dbc.Row([
        dbc.Col(header(), width=9),
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
    Output("f-company-type", "value"),
    Output("f-project", "value"),
    Output("f-year", "value"),
    Output("f-cost", "value"),
    Output("agg-mode", "value"),
    Output("top-n", "value"),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True
)
def do_reset(n):
    return (
        [], [], [], [], "All", [], [], [], [MIN_YEAR, MAX_YEAR], [MIN_COST, MAX_COST], AGG_DEFAULT, TOPN_DEFAULT
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
    Input("f-company-type", "value"),
    Input("f-project", "value"),
    Input("f-year", "value"),
    Input("f-cost", "value"),
    Input("agg-mode", "value"),
    Input("top-n", "value"),
)
def do_filter(company, province, sector, group, cleantech, status, company_type, project_select, year_range, cost_range, agg_mode, top_n):
    try:
        df2 = _filter_df(
            company, province, sector, group, cleantech, status, company_type, None, project_select, year_range, cost_range, agg_mode, top_n
        )
        msg = f"Loaded from: {LAST_SOURCE}" if LAST_SOURCE else SCHEMA_INIT_MSG
        return (df2.to_dict("records"), msg)
    except Exception as e:
        return ([], f"Filter error: {e}")

# ============================================================
# KPIs
# ============================================================
@app.callback(
    Output("kpi-total", "children"),
    Output("kpi-invest", "children"),
    Output("kpi-prob", "children"),
    Input("filtered", "data"),
    prevent_initial_call=False
)
def update_kpis(rows):
    try:
        df2 = pd.DataFrame(rows)
        total = len(df2)
        invest = _format_currency(np.nansum(pd.to_numeric(df2["project_cost"], errors="coerce")))
        prob = _format_pct(np.nanmean(pd.to_numeric(df2["prob_3yr"], errors="coerce")))
        return (f"{total:,}", invest, prob)
    except Exception:
        return ("0", "—", "—")

# ============================================================
# Tabs content
# ============================================================
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("filtered", "data"),
    Input("agg-mode", "value"),
    Input("top-n", "value"),
    prevent_initial_call=False
)
def render_tabs(tab, rows, agg_mode, topn):
    df2 = pd.DataFrame(rows)

    if tab == "t-province":
        fig = fig_topn_by(df2, by="province", agg_mode=agg_mode, topn=topn)
        return dcc.Graph(figure=fig)

    if tab == "t-sector":
        fig = fig_topn_by(df2, by="sector", agg_mode=agg_mode, topn=topn)
        return dcc.Graph(figure=fig)

    if tab == "t-company":
        fig = fig_topn_by_company(df2, agg_mode=agg_mode, topn=topn)
        return dcc.Graph(figure=fig)

    if tab == "t-project":
        fig = fig_topn_by_project(df2, agg_mode=agg_mode, topn=topn)
        return dcc.Graph(figure=fig)

    if tab == "t-type":
        fig1, fig2 = fig_by_type(df2, agg_mode=agg_mode)
        return html.Div([
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig1), width=6),
                dbc.Col(dcc.Graph(figure=fig2), width=6),
            ])
        ])

    return html.Div("Select a tab.")

# ============================================================
# Download filtered CSV
# ============================================================
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download", "n_clicks"),
    State("filtered", "data"),
    prevent_initial_call=True
)
def download_csv(n_clicks, rows):
    df2 = pd.DataFrame(rows)
    return dcc.send_data_frame(df2.to_csv, "mpi_probability_filtered.csv", index=False)

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=int(os.getenv("PORT", "7860")), debug=False)
