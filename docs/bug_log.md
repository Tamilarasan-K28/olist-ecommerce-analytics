# Bug and Issue Log

| ID | Where | Problem | Found by | Fix (commit) |
|---|---|---|---|---|
| B1 | clean_data.py | Zero-weight lines landed in clean_payments instead of clean_products; 2 tests failed and the pipeline crashed | pytest | Moved to clean_products (293d385) |
| B2 | requirements.txt | Frozen from system Python (venv activation failed) and written as UTF-16 | Package versions did not match the venv | Regenerated from the venv as UTF-8 (bb0a41a, d7bdce6) |
| B3 | sql/*.sql | UTF-8 byte-order mark written by PowerShell broke psql | psql syntax error | Rewrote files without BOM (c796013) |
| B4 | .gitignore | A pattern was appended to the last line (no trailing newline), so it did not ignore the file | git commit showed 1 insertion and 1 deletion | Rewrote the file cleanly (c84ef3b) |
| B5 | Module 2 | SQL files were never created, so the staging load failed | Loader error: relation does not exist | Created the files |
| B6 | Reconciliation | Payment vs item mismatch counted 378, 423 and 303 depending on rounding | Compared three runs | Documented; 250 orders (> 1 unit) is the stable figure |
| B7 | Documentation | Wrong statements corrected: 551 vs 547 orders with several reviews; 9 vs 10 checks; cause of the 24 vs 25 month gap | Re-reading outputs | Corrected in later messages |
| B8 | Power BI | Table names carried a schema prefix, so DAX could not resolve them | DAX error | Renamed tables |
| B9 | Power BI | Date relationship used the timestamp, so only one month matched | Chart showed one bar | Relationship rebuilt on purchase_date |
| B10 | Power BI | order_id appeared empty in fact_order_items | Empty relationship column | Resolved after reloading; exact cause not recorded |
| B11 | Power BI | Matrix and RFM chart used the measure People (96,096 everywhere) instead of the column | Screenshot review | Used the table column |
| B12 | Power BI | Sellers table showed Orders (All), 99,441 per row | Screenshot review | Switch to Orders (Item Grain); confirm |

Open items: B12 confirmation, pending reconciliation rows, the commit 19dd4cf script (src/export_for_powerbi.py) should be read once before submission.
## Findings that changed conclusions
| ID | Finding | Evidence | Treatment |
|---|---|---|---|
| F-ML1 | The pre-declared boosted model did not generalise to the test months | Test PR-AUC 0.0707 vs 0.3020 on validation; logreg_base 0.0947 | Reported in the model card; no re-selection on test |
| F-ML2 | Late rates change by month (1.36% to 21.36%), so validation and test base rates differ (11.74% vs 5.48%) | Monthly late-rate query | Documented as a limitation |
| F-ML3 | The cross-state rule reversed in the test months | Test ROC-AUC 0.371 | Reported; cause not investigated |
| B13 | tests/test_ml.py was not created on the first run, so git add failed | pathspec error | Created and committed |