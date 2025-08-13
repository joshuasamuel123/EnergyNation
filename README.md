# EnergyNation — MPI Project Risk Intelligence

Open, no‑paywall tools to explore the **probability** and **urgency** of major infrastructure projects in Canada (MPI).

<<<<<<< HEAD
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb)
[![Hugging Face — Dashboard](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/EnergyNation/MPI-Dashboard)

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

> If your file layout differs, adjust paths/links accordingly.
=======
**What’s here**
- **Dashboard** (Hugging Face): interactive views of Probability vs. Urgency and Top‑N rankings  
  → https://huggingface.co/spaces/EnergyNation/MPI-Dashboard
- **Risk Engines** (Python): Bayesian scorecard + Cox model, runnable in Colab  
  → ./risk_engines
- **Dataset**: cleaned MPI data + derived fields and a data dictionary  
  → ./data
- **Papers**: short, readable PDFs on methods, findings, and policy implications  
  → ./papers
- **Updates & explainers** (Substack)  
  → https://substack.com/@energynation
>>>>>>> 4424e9dd2b2b86e51d01c0b0c0532d135bc49095

---

## Quick start
1. **Kick the tires:** open the dashboard on Hugging Face—no install required.  
   → https://huggingface.co/spaces/EnergyNation/MPI-Dashboard
2. **Run the models:** click the Colab badge above to open the main notebook and press **Runtime → Run all**.
3. **Explore the data:** grab files under `/data` and read the `data_dictionary.md`.
4. **Read the background:** see `/papers` or the Substack posts for context.

---

## Run locally (optional)
```bash
# 1) Create a fresh environment (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

<<<<<<< HEAD
# 2) Install packages (versions tested together)
pip install --upgrade pip
pip install dash==2.16.1 jupyter-dash==0.4.2 pandas plotly kaleido numpy

# 3) Launch a local app or run notebooks
# Example for Dash apps (if present):
python app.py
# Or work directly in the Colab/Notebook equivalents
```
If you see a “file not found” error for the dataset, place the Excel/CSV in the same directory as the app/notebook or update the path in the code.

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
=======
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](
  https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v02.ipynb
)
>>>>>>> 4424e9dd2b2b86e51d01c0b0c0532d135bc49095

---

## License
- **Code:** MIT (free to use/modify; please credit)
- **Data & Papers:** CC BY 4.0 (free with attribution)

See the LICENSE files for details.

---

## Contact
Feedback is welcome—please open a GitHub issue or comment on Substack.  
Happy to hop on a quick Zoom/Teams walkthrough if helpful.
