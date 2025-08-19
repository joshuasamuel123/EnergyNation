# Model Card: Canada Major Projects Inventory 2024 — Pre-Construction Dashboard (v1.1)

## Model Details
- **Name:** Canada Major Projects Inventory 2024 — Pre-Construction Dashboard  
- **Version:** **1.1** (2025-08-19)  
- **Author:** Joshua Samuel (Energy Nation)  
- **Framework:** Python 3.11, Plotly Dash, Pandas, NumPy, Plotly Express, Dash Bootstrap Components  
- **License:** Code MIT; dataset licensing per source of the underlying Excel file.  
- **Repo/Space:** GitHub: *(insert link)* · Hugging Face Space: *(insert link)*

> This interactive dashboard visualizes the 2024 MPI for **pre-construction** projects, enabling exploration of probability of construction, urgency (priority), portfolio rankings, sectoral/provincial trends, and map views.

---

## Intended Use
- **Policy analysts & planners:** triage portfolios; identify high-priority, high-probability projects.  
- **Investors & utilities:** surface near-term, construction-ready opportunities.  
- **Researchers & public:** explore regional and sectoral patterns.

Key interactions:
- Rich filters (company, province, sector, group, cleantech, status, cost, year range).  
- KPIs for **total projects**, **total investment (CAD$ MM)**, **mean probability (≤3y)**.  
- Export filtered CSV.

---

## Data
**Input:** Excel (`.xlsx`) discovered in this priority:
1) `DATAFILE` env var → 2) `mpi_2024_scored.xlsx` → 3) `sample_mpi.xlsx` → 4) *any* `.xlsx` in app directory.

**Required columns:**  
`province`, `sector`, `group`, `cleantech`, `start_year`, `end_year`, `project_cost`,  
`current_survival`, `end_success`, `start_status`, `end_status`, `latitude_1`, `longitude_1`,  
`company`, `project`, `blended_prob`, `priority_index`, `power_ranking`

**Additional columns used:**  
- `urgency_scale_(0-1)` (now the **source of Priority/urgency**)  
- `company_type` (Ownership donut: Public/Private)

---

## Preprocessing & Display Logic (what the app does)
- Type coercion for numerics; cost presented in **CAD$ MM**.  
- Display helpers produce two-decimal rounded fields for charts/hover.  
- **Priority wiring change:**  
  - The app maps `urgency_scale_(0-1)` → `priority_index` **before** display fields are computed.  
  - All Priority visuals (e.g., Tab 1 scatter; Top-N Priority bar) now reflect **0–1 urgency** while keeping the **“Priority Index”** label for continuity.
- Sector color mapping for consistent legends.

---

## UI Overview (tabs)
1) **Probability & Ranking**  
   - **Scatter:** Probability (≤3y) vs **Priority Index (0–1 urgency)** with quadrant guides.
2) **Power Ranking**  
   - Three Top-N bars: **Power Ranking**, **Probability**, **Priority Index** (urgency).
3) **Facts and Figures**  
   - **Row 1 (toggle)**:  
     - Projects by **Sector** (stacked by Group) — **Count/Cost**  
     - Projects by **Province** (stacked by Sector) — **Count/Cost**
   - **Row 2 (fixed Cost)**:  
     - Total Project Value by **Sector** (CAD$ MM)  
     - Total Project Value by **Province** (CAD$ MM)
   - **Row 3 (toggle)**:  
     - **Cleantech** donut — **Count/Cost**  
     - **Ownership** donut (from `company_type`) — **Count/Cost**
   - **Row 4 (toggle)**:  
     - **Vintage** (start_year, stacked by sector) — **Count/Cost**
   - The **Count vs Cost** sidebar control drives **Row 1, Row 3, Row 4**. Row 2 always shows **Cost**.
4) **Map**  
   - Proportional markers (cost) for geocoded projects.  
5) **Stage Flow**  
   - Start → End status flow diagram.

---

## Performance & Assumptions
This dashboard is an **exploratory UI**—it **does not** generate predictions; it visualizes pre-scored fields:
- `blended_prob` (probability of construction within a defined horizon)  
- `priority_index` (now **urgency_scale_(0-1)**)  
- `power_ranking` (composite score)

**KPIs:**  
- Total projects (filtered)  
- Total investment (CAD$ MM)  
- Mean probability (≤3y)

Accuracy depends on source data correctness and update cadence.

---

## Limitations
- Visualizations inherit all **biases, omissions, and staleness** present in the input spreadsheet.  
- Non-geocoded projects don’t render on the map.  
- Category names must be consistently coded (e.g., sector, group, cleantech).  
- The **interpretation** of probability/priority/ranking should be contextualized with the methodology that produced them.

---

## Ethical Considerations
- Displayed probabilities and rankings can influence investment and policy; treat as **decision support**, not ground truth.  
- Publish or link the **methodology** used to compute `blended_prob`, `power_ranking`, and urgency to support transparency and reproducibility.  
- Ensure compliance with licensing and any confidentiality constraints in project metadata.

---

## How to Run
```bash
# 1) Place a target .xlsx next to app.py (or set DATAFILE)
# 2) Install
pip install pandas numpy plotly dash dash-bootstrap-components openpyxl
# 3) Launch
python app.py
# 4) Browse
# http://localhost:7860
```

---

## Changelog
- **v1.1 (2025-08-19):**  
  - **Priority wiring:** `urgency_scale_(0-1)` now drives **Priority Index (0–1)** across the app.  
  - **Tabs:** Top-N moved to **Power Ranking**; new **Facts & Figures** grid; **Count vs Cost** toggle wired to Rows **1, 3, 4**; Row 2 fixed to Cost.  
  - Ownership donuts use **`company_type`**.  
- **v1.0:** Initial release. 
