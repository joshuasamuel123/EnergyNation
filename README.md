# Energy Nation — AI-Assisted Portfolio Triage for Canada’s Major Projects Planned, 2024 to 2034

---

## Overview
EnergyNation offers data-driven tools to evaluate the probability of construction (within 3 years), urgency (time-to-event priority), and power ranking of major infrastructure projects in Canada. The repository integrates cleaned Major Projects Inventory datasets, two complementary risk engines (a Bayesian scorecard and a Cox proportional hazards model), an interactive dashboard, and supporting papers. 

---

## Quick Start

1. **Explore the Dashboard** — view interactive Probability vs. Priority plots, Top-N Power Rankings, charts and figures, and geographic maps.
   → [![Hugging Face — Dashboard](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Open-blue)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)
   
2. **Read the Papers** — explore the full series, from foundational literature review through forecasting, power ranking, and dashboard deployment. 

3. **Run the Models in Colab** — open the notebook and execute all cells (no local setup required).
   → [![Risk Engines](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)

4. **Review and Analyze the Data** — download the files and data dictionaries in /data for your own analysis, or explore them using AI data-analysis tools. 

5. **Subscribe on Substack** — follow for articles, notes, and updates.
   → [![Substack](https://img.shields.io/badge/Substack-Updates-orange)](https://energynation.substack.com/)

---

## Repository Contents

* `risk_engines/` — notebooks and scripts for the Bayesian scorecard and Cox proportional hazards model; outputs include Probability of Construction (≤ 3 years), Priority Index, and Power Ranking.
* `data/` — cleaned MPI dataset, scored outputs, and `data_dictionary.md`.
* `dashboard/` — source files for the interactive dashboard.
* `papers/` — articles detailing the methodology and findings.
* `README.md` — this document.

---

## License

* **Code:** Licensed for educational and research purposes only under a modified MIT license (non-commercial use).
* **Data & Papers:** Licensed under CC BY-NC 4.0 (non-commercial use).

See the LICENSE files for full terms.

[![MIT License — Non-Commercial](https://img.shields.io/badge/License-MIT%20\(NC\)-green.svg)](https://opensource.org/licenses/MIT)
[![CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

---

## Acknowledgements & Official MPI Resources

**Energy Nation** builds on publicly available materials from **Natural Resources Canada (NRCan)**’s **Major Projects Inventory (MPI)**.  
We are not affiliated with NRCan; any analysis, modeling, or opinions in this repository are our own.  

For the authoritative MPI materials, please consult the official NRCan resources:

[![NRCan — MPI Report](https://img.shields.io/badge/NRCan-MPI_Report-0b5fff)](https://natural-resources.canada.ca/science-data/data-analysis/natural-resources-major-projects-planned-under-construction-2024-2034)
[![NRCan — Interactive Map](https://img.shields.io/badge/NRCan-Interactive_Map-0b5fff)](https://nrcan-rncan.maps.arcgis.com/apps/dashboards/5ab61c54487e4d05a4ff83c84e018cde)
[![Open Canada — Dataset](https://img.shields.io/badge/Open_Canada-Dataset-0b5fff)](https://open.canada.ca/data/en/dataset/f5f2db55-31e4-42fb-8c73-23e1c44de9b2)

- **NRCan MPI Report (2024–2034):** Overview of planned and under-construction natural resource projects, methodology, and key findings.  
- **NRCan Interactive Map:** Official ArcGIS dashboard for exploring projects geographically and filtering by sector, status, and region.  
- **Open Canada Dataset:** Downloadable MPI data and metadata for independent analysis.

### How this repo relates to MPI
This repository provides complementary tooling (lightweight forecasting models, dashboards, and documentation) to explore portfolio-level questions.  
While we reference the MPI, our derived metrics, transformations, and interpretations are independent of NRCan and may differ from the official presentation.

### Use & Attribution
Please consult the **Open Canada** dataset page for terms of use and attribution guidance.  
When citing MPI materials, consider a format such as:

> Natural Resources Canada (NRCan). *Major Projects Inventory (MPI), 2024–2034.* Ottawa, Canada. Official report, interactive map, and dataset available via NRCan and Open Canada.

If you use this repository, a citation such as the following helps others find the work:

> Samuel, J. (Energy Nation). *MPI Risk Tools & Dashboard (Open Research Repository).* GitHub: joshuasamuel123/EnergyNation.


## About Energy Nation

**Energy Nation** is a research project by Joshua Samuel to fill a critical gap in data-driven intelligence on the development of major projects, leveraging machine learning and AI-assisted tools.  

**Joshua Samuel** is an executive in energy infrastructure and strategic development with 20 years’ experience delivering over C$820M in renewable energy and clean fuel projects, including hydrogen, RNG, LNG, CCUS, energy storage, and district energy, totaling 21 PJ/year (670 MW th) capacity. He specializes in project finance, feasibility, front-end engineering, and regulatory approvals from site selection through FID/COD, with a proven record in securing funding, negotiating complex agreements, and leading multidisciplinary teams. Known for strategic direction, stakeholder engagement, and technical excellence, Joshua brings expertise in business case structuring, investment analysis, and market development across regional and emerging markets.  

---

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Contact%20Us-blue?logo=linkedin)](https://www.linkedin.com/in/jlsamuel/)
[![Substack](https://img.shields.io/badge/Substack-Updates-orange?logo=substack)](https://energynation.substack.com/)
[![Issues](https://img.shields.io/badge/GitHub-Issues-informational)](https://github.com/joshuasamuel123/EnergyNation/issues)
