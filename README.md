# EnergyNation — MPI Project Risk Intelligence

[![Risk Engines](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)
[![Hugging Face — Dashboard](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dashboard-blue)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)
[![Substack](https://img.shields.io/badge/Substack-Updates-orange)](https://substack.com/@energynation)
[![Issues](https://img.shields.io/badge/GitHub-Issues-informational)](https://github.com/joshuasamuel123/EnergyNation/issues)

---

## Overview
EnergyNation provides reproducible tools to assess the **probability** of construction (≤ 3 years) and the **urgency** (time‑to‑event priority) of major infrastructure projects in Canada. The repository combines a cleaned MPI dataset, two complementary risk engines (Bayesian scorecard and Cox proportional hazards), and an interactive dashboard.

---

## How to use
1. **Explore the dashboard** — interactive Probability vs. Priority views, Top‑N rankings, and maps.  
   → [![Hugging Face — Dashboard](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Open-blue)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)
2. **Run the models in Colab** — open the notebook and run all cells (no local setup required).  
   → [![Risk Engines](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)
3. **Review the data** — see `/data` and the data dictionary for field definitions and derived features.

---

## Repository contents
- `risk_engines/` — notebooks and scripts for the Bayesian scorecard and Cox model; outputs include Probability of Construction (≤ 3y), a Priority Index and Power Ranking
- `data/` — cleaned MPI dataset, scored outputs, and `data_dictionary.md`.
- `dashboard/` or `app/` — files for the interactive dashboard.
- `papers/` — articles on methodology and findings.
- `README.md` — this document.

---

## Overview
EnergyNation combines a cleaned MPI dataset, two complementary risk engines (a **Bayesian scorecard** and a **Cox proportional hazards model**), and a lightweight dashboard so anyone can quickly evaluate which projects are **likely to be built soon** and which are **most urgent** to watch.

---

## What’s in this repo
- **Dashboard (Hugging Face):** Interactive views of Probability vs. Urgency, Top‑N rankings, maps, and drill‑downs → https://huggingface.co/spaces/EnergyNation/MPI-Dashboard
- **Risk Engines (Python/Colab):** Reproducible notebooks and scripts to compute Probability of Construction (≤3y) and a Priority Index → `./risk_engines`
- **Dataset:** Cleaned MPI data, derived fields, and a data dictionary → `./data`
- **Papers / Notes:** Short, readable write‑ups on methodology, findings, and policy implications → `./papers`
- **Updates & explainers (Substack):** https://substack.com/@energynation

---

## Quick start
1. **Kick the tires:** open the dashboard on Hugging Face—no install required.  
   → https://huggingface.co/spaces/EnergyNation/MPI-Dashboard
2. **Run the models:** click the Colab badge above to open the main notebook and press **Runtime → Run all**.
3. **Explore the data:** grab files under `/data` and read the `data_dictionary.md`.
4. **Read the background:** see `/papers` or the Substack posts for context.

---

## Repo layout (typical)
```
EnergyNation/
├─ data/                # Cleaned MPI data, scored outputs, data dictionary
├─ risk_engines/        # Notebooks & scripts (Bayes scorecard, Cox model)
├─ papers/              # Short PDFs/notes on methods & findings
├─ app/ or dashboard/   # (If present) Dash app for local run
└─ README.md
```

---

## License
- **Code:** MIT  
- **Data & Papers:** CC BY 4.0

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## Feedback
Questions or suggestions are welcome. 
=======
- **Code:** MIT (free to use/modify; please credit)
- **Data & Papers:** CC BY 4.0 (free with attribution)

See the LICENSE files for details.

---

## Contact
Feedback is welcome.  

