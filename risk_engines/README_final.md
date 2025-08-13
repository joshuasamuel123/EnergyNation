# MPI Risk Engines

## 📝 Overview
The MPI Risk Engines repository contains statistical models and workflows to assess the **probability** and **urgency** of major infrastructure projects in Canada. 
These models use data from the Major Projects Inventory (MPI) to generate key indicators such as:
- Probability of construction within 3 years
- Priority and urgency indices
- Composite power ranking scores

The repository is designed for researchers, policymakers, and analysts who want to quickly score projects using pre-trained Bayesian and Cox proportional hazards models.

This folder contains two statistical models for assessing the probability and urgency of major infrastructure projects in Canada, based on the Major Projects Inventory (MPI) dataset.

---

## 📊 Models Included

1. **Bayesian Likelihood-Ratio Scorecard**
   - Estimates the probability that a project will proceed to construction within the next 3 years.
   - Uses a logistic-likelihood approach with features such as:
     - Cleantech flag
     - Cost quintile
     - Sector, province, group
     - Start year bin
     - Province–sector interaction terms

2. **Cox Proportional Hazards Model**
   - Estimates the urgency of a project using time-to-event analysis.
   - Calculates a hazard-based probability for construction within 3 years.
   - Features include:
     - Cleantech flag
     - Cost quintile (derived from `cost_percentile`)
     - Sector, province

---

## 🛠 How It Works

The workflow is implemented in `mpi_risk_engine_v01.py` and expects:

- **Bayes coefficients file**: `bayes_lr_regenerated_coefficients.csv`  
  (`feature_name`, `LR`)
- **Cox coefficients file**: `cox_coefficients_with_references.csv`  
  (`covariate`, `coef`)
- **MPI input dataset**: `mpi_2024_input.xlsx`

The script:
1. Loads coefficients and the MPI dataset.
2. Computes:
   - `p_bayes` — Bayesian probability
   - `p_cox` — Cox model probability
   - `blended_prob` — Weighted average (60% Bayes, 40% Cox)
   - `priority_index` — Blended probability divided by years remaining
   - `urgency_scale_(0-1)` — Normalized urgency
   - `power_ranking` — Combined priority score (60% probability, 40% urgency scale)
3. Saves scored dataset as:
   - `mpi_2024_scored.csv`
   - `mpi_2024_scored.xlsx`

---

## 🚀 Run the Risk Engine in Google Colab

You can run the MPI Risk Engine directly in your browser using **Google Colab** — no installation required.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](
  https://colab.research.google.com/github/joshuasamuel123/EnergyNation/blob/main/risk_engines/EnergyNation_Risk_Engine_Colab_v01.ipynb
)

### Steps
1. **Click the badge above** to open the Colab notebook.
2. **Run the first few cells** to install dependencies and create the engine script.
3. When prompted, **upload the three required input files**:
   - `bayes_lr_regenerated_coefficients.csv`
   - `cox_coefficients_with_references.csv`
   - `mpi_2024_input.xlsx`
4. Run the “Execute engine” cell.
5. **Preview results** in Colab or download:
   - `mpi_2024_scored.csv`
   - `mpi_2024_scored.xlsx`

💡 *Tip:* You can also mount Google Drive in Colab (cell provided in the notebook) to read inputs or save outputs directly there.
## 📥 Inputs

| File | Description |
|------|-------------|
| `bayes_lr_regenerated_coefficients.csv` | Likelihood ratios for Bayesian features |
| `cox_coefficients_with_references.csv` | Coefficients for Cox model covariates |
| `mpi_2024_input.xlsx` | MPI dataset with project attributes |

---

## 📤 Outputs

| Column | Description |
|--------|-------------|
| `p_bayes` | Probability from Bayesian model |
| `p_cox` | Probability from Cox model |
| `blended_prob` | Weighted probability score |
| `priority_index` | Probability ÷ years remaining |
| `urgency_scale_(0-1)` | Min–max normalized priority index |
| `power_ranking` | Final composite score |

---

## 🔍 Reproducibility Tips

- Freeze package versions in Colab using `pip install package==version` if you want consistent results over time.
- Keep the coefficient files consistent with the MPI dataset version.
- Ensure input feature names match the keys in the coefficient files.

---

## 📜 License

See the root repository for code and data licensing terms.
