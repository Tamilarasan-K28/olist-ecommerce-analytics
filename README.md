# Intelligent E-Commerce Analytics and Decision Support System

B.Tech Artificial Intelligence and Data Science final-year project. End-to-end analytics on the Olist Brazilian E-Commerce Public Dataset: data engineering, PostgreSQL, statistical analysis, Power BI and a late-delivery prediction experiment.

## Key measured results
| Metric | Value |
|---|---|
| Orders / people / order items | 99,441 / 96,096 / 112,650 |
| Revenue (sum of item price, excl. canceled and unavailable) | 13,494,400.74 (currency not stated in the dataset) |
| AOV | 137.42 |
| Late delivery rate | 8.11% (7,826 of 96,470 delivered orders) |
| Average review score | 4.086; late orders 2.565 vs on-time 4.294 (association only) |
| Repeat customers | 3.12% of people |
| Top 10% of sellers | 67.4% of revenue |

The Python pipeline, PostgreSQL schema and Power BI report reconcile to the same totals (docs/reconciliation_python_sql_powerbi.md).

## Architecture
See docs/architecture.md (diagram).

## Dashboards
Screenshots are in docs/figures/. Report guide: docs/powerbi_guide.md. The PBIX is not stored in Git.

## Machine learning
Problem definition: docs/ml_problem_definition.md. Results and limits: docs/ml_model_card.md (generated from the single test evaluation).

## Setup (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
1. Download the Olist dataset from Kaggle (olistbr/brazilian-ecommerce) into data/raw/ (nine CSV files, unchanged).
2. Install PostgreSQL 17, create a database named olist, copy .env.example to .env and set PGPASSWORD.
3. Run in order:
```powershell
python src\verify_raw_data.py
python src\profile_raw_data.py
python src\clean_data.py
python src\reconcile.py
psql -U postgres -h localhost -d olist -f sql\01_create_schemas_and_staging.sql
psql -U postgres -h localhost -d olist -f sql\02_staging_remaining.sql
python src\load_staging.py
psql -U postgres -h localhost -d olist -v ON_ERROR_STOP=1 -f sql\04_build_analytics.sql
psql -U postgres -h localhost -d olist -f sql\06_views.sql
python -m pytest -q
```

## Repository layout
src/ (pipeline, analysis, ML), sql/ (schema and queries), tests/ (pytest), docs/ (rules, dictionary, reports), reports/ (aggregate outputs), powerbi/ (DAX), notebooks/.

## Limitations
Single marketplace, about two years, uneven monthly coverage (trend window 2017-01 to 2018-08). Lateness and review scores are associations, not causes. The model ranks risk; it does not explain it. Author-defined rules (revenue, review selection, RFM, zero weight, coordinate box) are documented in docs/cleaning_rules.md.

## Data and license
Raw data is not included. Dataset: Olist, CC BY-NC-SA 4.0, for non-commercial use with attribution and share-alike. Aggregated outputs here are derived from it.
## Late-delivery model (test split, evaluated once)
Time-based split (train 2017-01 to 2018-02, validation 2018-03 to 2018-05, test 2018-06 to 2018-08). On the test months (late rate 5.48%) the best of the compared models, logistic regression, reached ROC-AUC 0.687 and PR-AUC 0.0947, with a top-10% lift of 1.74. The pre-declared boosted model with time-aware features scored lower (ROC-AUC 0.611, PR-AUC 0.0707), and performance varied strongly by month. The models carry modest ranking signal at best and are not reliable enough for operational decisions; details and limits are in docs/ml_model_card.md.