# SQL vs Python Reconciliation

All values below were produced independently in Python (src/reconcile.py, raw CSVs) and in PostgreSQL (sql/05_analytics_checks.sql, analytics schema).

| Metric | Python | PostgreSQL |
|---|---|---|
| Revenue (sum of price, excl. canceled/unavailable) | 13,494,400.74 | 13,494,400.74 |
| Total freight | 2,251,909.54 | 2,251,909.54 |
| Total payment value | 16,008,872.12 | 16,008,872.12 |
| Revenue-eligible orders | 98,199 | 98,199 |
| Delivery-eligible orders | 96,470 | 96,470 |
| Late delivered orders | 7,826 | 7,826 |
| Distinct customer_unique_id | 96,096 | 96,096 |
| Orders with a review | 98,673 | 98,673 |

Row counts of all 12 loaded tables equal the CSV row counts (src/load_staging.py). Four views at four grains each sum to 13,494,400.74.

Limit: this shows PostgreSQL reproduces the Python results; it does not prove the business rules are correct.