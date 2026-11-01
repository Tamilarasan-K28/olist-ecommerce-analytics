# Python, SQL and Power BI Reconciliation

| Metric | Python | SQL | Power BI | Status |
|---|---|---|---|---|
| Revenue | 13,494,400.74 | 13,494,400.74 | 13,494,400.74 (cards, Products and Sellers totals) | Match |
| Revenue-eligible orders | 98,199 | 98,199 | 98,199 | Match |
| AOV | 137.42 | 137.42 | 137.42 | Match |
| Late rate | 8.11% | 8.11% | 8.11% | Match |
| Late orders | 7,826 | 7,826 | 7,826 (card and QA check) | Match |
| Average review score | 4.086 | 4.086 | 4.09 (display rounding) | Match |
| Repeat customer rate | 3.12% | 3.12% | 3.12% | Match |
| Freight (eligible orders) | 2,241,126.29 | n/a | 2,241,126.29 | Match |
| Revenue 2018-05 | 992,871.75 | 992,871.75 | 992,871.75 | Match |
| Payment value (all) | 16,008,872.12 | 16,008,872.12 | donut shares match; total not read | Pending |
| Items sold (eligible orders) | 112,101 expected | not run | 112,101 | Pending SQL check |
| Late rate, state SP | 5.89% (Q6) | 5.89% | not read | Pending |
| Four QA cards | n/a | n/a | PASS x4 | Match |

Method: Python from raw CSV (src/reconcile.py), SQL on the analytics schema (sql/05, sql/07, tests/test_db_integration.py), Power BI cards and tables read from the report. Pending rows must be completed before submission.