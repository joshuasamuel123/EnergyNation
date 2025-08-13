# EnergyNation — MPI Project Risk Intelligence

[![Risk Engines](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)
[![Hugging Face — Dashboard](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dashboard-blue)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)
[![Substack](https://img.shields.io/badge/Substack-Updates-orange)](https://substack.com/@energynation)
[![Issues](https://img.shields.io/badge/GitHub-Issues-informational)](https://github.com/joshuasamuel123/EnergyNation/issues)

---

## Overview
EnergyNation offers data-driven tools to evaluate the probability of construction (within 3 years), urgency (time-to-event priority), and power ranking of major infrastructure projects in Canada. The repository integrates a cleaned MPI datasets, two complementary risk engines (a Bayesian scorecard and a Cox proportional hazards model), an interactive dashboard, and supporting papers. 

---

## How to Use

1. **Explore the Dashboard** — view interactive Probability vs. Priority charts, Top-N rankings, chart, and geographic maps.
   → [![Hugging Face — Dashboard](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Open-blue)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)

2. **Run the Models in Colab** — open the notebook and execute all cells (no local setup required).
   → [![Risk Engines](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)

3. **Review the Data** — browse the `/data` directory and consult the data dictionary for field definitions and derived features.

---

## Repository Contents

* `risk_engines/` — notebooks and scripts for the Bayesian scorecard and Cox proportional hazards model; outputs include Probability of Construction (≤ 3 years), Priority Index, and Power Ranking.
* `data/` — cleaned MPI dataset, scored outputs, and `data_dictionary.md`.
* `dashboard/` or `app/` — source files for the interactive dashboard.
* `papers/` — articles detailing the methodology and findings.
* `README.md` — this document.

---

## Quick Start

1. **Open the Dashboard** — launch the interactive view on Hugging Face (no installation required).
   → [https://huggingface.co/spaces/EnergyNation/MPI-Dashboard](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)

2. **Run the Models** — click the Colab badge above to open the main notebook, then select **Runtime → Run all** to execute.

3. **Review the Data** — access files in `/data` and consult `data_dictionary.md` for field definitions and derived features.

4. **Read the Background** — explore `/papers` or related Substack posts for methodology and context.

---

## Repo layout (typical)
EnergyNation/
├─ data/                # Cleaned MPI dataset, scored outputs, and data dictionary
├─ risk_engines/        # Notebooks and scripts (Bayesian scorecard, Cox model)
├─ papers/              # PDF articles on methods, results, discussion, and conclusions
├─ app/ or dashboard/   # Dash application for local use
└─ README.md            # Project overview and usage instructions

---

## License

* **Code:** Licensed for educational and research purposes only under a modified MIT license (non-commercial use).
* **Data & Papers:** Licensed under CC BY-NC 4.0 (non-commercial use).

See the LICENSE files for full terms.

[![MIT License — Non-Commercial](https://img.shields.io/badge/License-MIT%20\(NC\)-green.svg)](https://opensource.org/licenses/MIT)
[![CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

---

## Contact
Feedback is welcome.  

