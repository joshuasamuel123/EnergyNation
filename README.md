# EnergyNation — MPI Project Risk Intelligence

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)
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
   → [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)
3. **Review the data** — see `/data` and the data dictionary for field definitions and derived features.

> If you encounter “file not found” errors, ensure the dataset path in notebooks/scripts matches your folder layout.

---

## Repository contents
- `risk_engines/` — notebooks and scripts for the Bayesian scorecard and Cox model; outputs include Probability of Construction (≤ 3y) and a Priority Index.
- `data/` — cleaned MPI dataset, scored outputs, and `data_dictionary.md`.
- `dashboard/` or `app/` — files for the interactive dashboard (if included for local development).
- `papers/` — articles on methodology and findings.
- `README.md` — this document.

---

## License
- **Code:** MIT  
- **Data & Papers:** CC BY 4.0

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## Feedback
Questions or suggestions are welcome. 
