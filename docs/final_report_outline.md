# Intelligent E-Commerce Analytics and Decision Support System Using Machine Learning and Business Intelligence

## Abstract
(150-200 words) Dataset and aim; pipeline (Python, PostgreSQL, Power BI); 3 headline findings (late deliveries associated with 1.7 lower review points; revenue concentrated in few sellers; 3.12% repeat customers); model result from docs/ml_model_card.md; main limitation.

## 1. Introduction, problem statement, motivation, objectives
Use the project objective in the brief. Problem: marketplace data is spread over nine related tables and easy to mis-aggregate (items, payments, reviews are one-to-many). Objectives: reproducible pipeline, validated SQL model, dashboards, delivery analysis, leakage-safe prediction.

## 2. Literature review (write this yourself)
Cover 5 to 8 real sources you have read: e-commerce analytics, RFM segmentation, customer review and delivery performance, gradient boosting, evaluation on imbalanced data. Candidates to verify before citing: Friedman (2001) gradient boosting, Annals of Statistics; Pedregosa et al. (2011) scikit-learn, JMLR; Saito and Rehmsmeier (2015) precision-recall vs ROC, PLoS ONE; Hughes (1994) Strategic Database Marketing (RFM). Check every reference details yourself.

## 3. Methodology
Data and license; table grain and keys; cleaning rules R1-R19 (docs/cleaning_rules.md); revenue and KPI definitions (docs/kpi_definitions.md); SQL model; analysis methods; time-based ML split and leakage controls (docs/ml_problem_definition.md).

## 4. Architecture
docs/architecture.md diagram; layers and tools.

## 5. Implementation
5.1 Data engineering and quality (counts, orphans, duplicates). 5.2 PostgreSQL schema (docs/database_schema.md). 5.3 SQL library. 5.4 Python analysis. 5.5 Power BI (docs/powerbi_guide.md, screenshots). 5.6 ML pipeline. 5.7 Testing (tests/, run_validation.ps1, docs/bug_log.md).

## 6. Results
6.1 Data quality (docs/data_quality_report.md). 6.2 Trends and KPIs (docs/module3_findings.md). 6.3 Customers and delivery (docs/module4_findings.md). 6.4 Dashboards. 6.5 Model (docs/ml_model_card.md: comparison with baselines, intervals, by month). 6.6 Reconciliation (docs/reconciliation_python_sql_powerbi.md).

## 7. Limitations
Copy the limitation lists from docs/module3_findings.md, docs/module4_findings.md and the model card. State that rules are author choices and unexplained items stay unexplained (303 payment/item mismatches, wave-like late rates).

## 8. Conclusion and future work
What was achieved; what the data cannot say; future work: seller and carrier-level data, richer features, calibration to the monthly level, refresh automation.

## References
(add verified references; dataset: Olist, Brazilian E-Commerce Public Dataset, Kaggle, CC BY-NC-SA 4.0)