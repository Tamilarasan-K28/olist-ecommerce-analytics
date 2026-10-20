# Module 3: Exploratory Findings and Limitations

All figures measured on the Olist data via PostgreSQL / Pandas (see reconciliation in docs/sql_python_reconciliation.md). Revenue = sum of item price for non-canceled, non-unavailable orders (rule R18). Currency is not stated in the dataset.

## Findings
| # | Finding | Evidence | Type |
|---|---|---|---|
| F1 | Orders and revenue are continuous from 2017-01 to 2018-08; the months outside are sparse | 99,092 of 99,441 orders (99.65%) fall in the window; 2016-09 to 2016-12 and 2018-09 to 2018-10 have 1 to 324 orders per month | Measured |
| F2 | Single-month peak in 2017-11 | 7,544 orders, revenue 1,003,862.14 | Measured |
| F3 | 2018 is a plateau | Orders between 6,167 and 7,269 per month, Jan to Aug 2018 | Measured |
| F4 | Late deliveries are associated with lower review scores | Gap -1.729; -1.715 within state; -1.727 within category | Association |
| F5 | The gap does not depend on the latest-review rule | Excluding 189 conflicting-review orders: -1.730 | Measured |
| F6 | Payments are dominated by credit card | 78.34% of payment value; boleto 17.92% | Measured |
| F7 | Seller revenue is concentrated | Top 10% of sellers hold 67.4% of revenue | Measured |
| F8 | Category revenue is less concentrated | Largest category 9.3%; top 7 hold 49.9% | Measured |

## Your reading of the monthly chart
(TODO: write 2 to 3 sentences in your own words after viewing reports/figures/monthly_orders_revenue.png.)

## Limitations
- L1: Lateness and low review scores are associated; the data cannot show that lateness causes low scores.
- L2: The category control uses only item 1 of each order and covers 7,344 of 7,661 late orders.
- L3: The state control covers 7,637 of 7,661 late orders; groups under 30 orders per side are dropped (author's threshold).
- L4: The November 2017 peak has no explanation in the dataset.
- L5: The 2018 plateau is described, not explained.
- L6: Review scores by payment type are not tested statistically; the not_defined group has 3 orders.
- L7: 303 orders have payment totals that differ from items plus freight by more than one cent; the cause is not determined.
- L8: The dataset is a single marketplace over about two years; results should not be generalised.