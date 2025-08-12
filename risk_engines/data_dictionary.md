# Data Dictionary — MPI_2024_Input.xlsx

This file contains the cleaned and pre-processed Major Projects Inventory (MPI) dataset used as input to the MPI Risk Engines.

| Column | Type | Description |
|--------|------|-------------|
| `Unique ID` | int | Unique project identifier assigned in the MPI dataset. |
| `company` | string | Name of the company or sponsor responsible for the project. |
| `project` | string | Official project name. |
| `province` | string | Canadian province or territory where the project is located (e.g., ON, BC, AB). |
| `company_type` | string | Type/category of the sponsoring company (e.g., Public, Private, Crown Corporation). |
| `sector` | string | Economic sector classification (e.g., Power, Oil & Gas, Transportation). |
| `group` | string | Sub-sector or group classification within the sector (e.g., Wind, Transmission, LNG). |
| `start_status` | string | Status of the project when first recorded in MPI (e.g., Announced, Under Review). |
| `end_status` | string | Most recent known status in MPI (e.g., Under Construction, Completed, Cancelled). |
| `start_year` | int | Year the project first appeared in MPI records. |
| `end_year` | int | Most recent year the project status was updated in MPI. |
| `project_cost` | float | Estimated total project cost in CAD dollars. |
| `cost_percentile` | float | Project cost percentile (0–1) relative to all MPI projects, used in Cox model. |
| `cleantech` | string | “Yes” or “No” flag indicating whether the project involves clean technology. |
| `reporting_years` | float | Number of years the project has been tracked in MPI. |
| `p_bayes` | float | Probability of construction within 3 years from the Bayesian model (added by risk engine). |
| `risk_score` | float | Hazard score from Cox proportional hazards model (added by risk engine). |
| `p_cox` | float | Probability of construction within 3 years from Cox model (added by risk engine). |
| `blended_prob` | float | Weighted probability (60% Bayesian, 40% Cox) (added by risk engine). |
| `priority_index` | float | Blended probability divided by years remaining (added by risk engine). |
| `urgency_scale_(0-1)` | float | Min–max scaled urgency value (added by risk engine). |
| `power_ranking` | float | Final composite ranking metric (60% probability, 40% urgency scale) (added by risk engine). |

---

## Notes

- Costs are expressed in CAD dollars; may be nominal or adjusted values depending on MPI source.
- Percentile-based fields (`cost_percentile`) are calculated relative to the dataset version and may change when dataset updates.
- Probability and ranking fields (`p_bayes` onward) are **not** in the raw MPI data; they are produced by running the MPI Risk Engine.
- Missing values are blank unless otherwise noted.

---

## Version

This data dictionary applies to **MPI_2024_Input.xlsx** used in model version **v01**.
