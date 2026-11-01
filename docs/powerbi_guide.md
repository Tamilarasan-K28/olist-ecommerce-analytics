# Power BI Report Guide

Report file: `powerbi/olist_dashboard.pbix` (not stored in Git; it contains imported order-level data).
Source: PostgreSQL database `olist`, schema `analytics`. Dataset: Olist Brazilian E-Commerce Public Dataset (CC BY-NC-SA 4.0). Currency is not stated in the dataset.

## 1. How to refresh

1. Start PostgreSQL (Windows Services, service `postgresql-x64-17` must be running).
2. Open `olist_dashboard.pbix` in Power BI Desktop.
3. Click **Home > Refresh**. Enter user `postgres` and the password if asked.
4. If the data in PostgreSQL was rebuilt, rerun the pipeline first, in this order:
   - `python src/clean_data.py`
   - `python src/load_staging.py`
   - `psql -U postgres -h localhost -d olist -f sql/04_build_analytics.sql`
5. After a refresh, open the **Definitions & QA** page and confirm every check card reads PASS.

Two small tables come from CSV files and are refreshed from files, not from the database: `rfm_summary` (`reports/rfm_summary.csv`) and `cohort_repeat_rates` (`reports/cohort_repeat_rates.csv`). If the path changes, use **Transform data > Data source settings**.

## 2. Data model

Star layout, all relationships one-to-many with single filter direction (the "one" side filters the "many" side):

| One side | Many side |
|---|---|
| `dim_customers[customer_id]` | `fact_orders[customer_id]` |
| `fact_orders[order_id]` | `fact_order_items[order_id]` |
| `fact_orders[order_id]` | `fact_payments[order_id]` |
| `dim_products[product_id]` | `fact_order_items[product_id]` |
| `dim_sellers[seller_id]` | `fact_order_items[seller_id]` |
| `Date[Date]` | `fact_orders[purchase_date]` |

`dim_geography`, `rfm_summary` and `cohort_repeat_rates` have no relationships. Measures are in the `_Measures` table and are saved in `powerbi/measures.dax`.

## 3. Pages

| # | Page | Purpose |
|---|---|---|
| 1 | Executive Overview | Six headline KPIs, monthly orders and revenue, state and year slicers, late vs on-time, review score distribution |
| 2 | Sales | Monthly revenue with MoM %, revenue by state, payment mix, revenue vs freight |
| 3 | Customers | People and repeat rate, people by state, RFM segments, cohort repeat-purchase matrix |
| 4 | Products | Top 10 categories, category table with share (item-level measures) |
| 5 | Sellers | Top 10 sellers, revenue by seller state, seller table (item-level measures) |
| 6 | Delivery | Late rate and delivery days by customer state, review score by delivery outcome, late orders by month |
| 7 | Definitions & QA | KPI definitions, reference values, model rules, PASS/FAIL check cards |

Hidden helper pages (not in the navigator):

| Page | Use |
|---|---|
| Seller Detail | Drill-through target: right-click a seller in the Sellers table |
| Category Detail | Drill-through target: right-click a category on the Products page |
| Month Tooltip | Report-page tooltip shown when hovering over a month on the Executive Overview chart |

## 4. Rule: order-level vs item-level measures

Filters flow from dimensions to facts in one direction. A seller or category filter reaches `fact_order_items` but not `fact_orders`.

| Measure type | Use on | Examples |
|---|---|---|
| Order-level (counts rows of `fact_orders`) | Pages 1, 2, 3, 6 (filters by customer state, date) | Revenue, Orders (Revenue-Eligible), AOV, Late Rate, Avg Review Score, People |
| Item-level (counts rows of `fact_order_items`) | Pages 4 and 5 and both detail pages (filters by category, seller) | Item Revenue, Items Sold, Orders (Item Grain), Category Share |

Do not put order-level measures on a seller or category visual: they ignore the filter and repeat the overall total. For example, `Orders (All)` shows 99,441 on every seller row. Use `Orders (Item Grain)` there. There is no seller-level late rate in this report; see `reports/seller_late_rates.csv`.

`Orders (Item Grain)` counts an order once per seller, so its total can exceed the order count when an order has items from more than one seller.

## 5. QA check cards (Definitions & QA page)

Four measures ignore all slicers and compare live values with the verified reference figures:

| Card | Expected value | Reference |
|---|---|---|
| QA Revenue Check | 13,494,400.74 | Python, SQL |
| QA Eligible Orders Check | 98,199 | Python, SQL |
| QA Late Orders Check | 7,826 | Python, SQL |
| QA People Check | 96,096 | Python, SQL |

All four must read PASS. If one reads FAIL, do not edit the measure to fit: the data or the model changed, so investigate the difference first.

## 6. Reference values

| KPI | Value |
|---|---|
| Revenue (sum of item price, excl. canceled/unavailable) | 13,494,400.74 |
| Revenue-eligible orders | 98,199 |
| AOV | 137.42 |
| Delivered orders (metric) | 96,470 |
| Late orders / late rate | 7,826 / 8.11% |
| Average delivery days | 12.56 |
| Average review score | 4.086 |
| People / repeat customer rate | 96,096 / 3.12% |
| Total payment value | 16,008,872.12 |
| Revenue, 2018-05 | 992,871.75 (checked in PostgreSQL) |
| Late rate, customer state SP | 5.89% |

## 7. Data limits and reading rules

- **Trend window:** trend charts use 2017-01 to 2018-08 (filter `Date[Trend Window] = In window`). Other months hold 1 to 324 orders per month, and 2016-11 has none. Window totals therefore differ from the full total (13,449,529.68 vs 13,494,400.74 revenue).
- **MoM %** is blank for 2017-01, for months outside the window and for the Total row.
- **RFM and cohort tables ignore slicers:** they come from separate files with no relationships.
- **RFM segments** are author-defined; "recent" means the more recent half of customers, and the snapshot date is 2018-10-18.
- **Cohort rates** are shown only when every member was observed for the full period; blanks are intentional. A return is any later order from the same person, of any status.
- **Late rate and review score** are associations, not proof of cause.
- **Small states:** states with fewer than 100 delivered orders can show unstable rates.
- **Revenue** excludes freight; payment value is used only for payment-method analysis.
- **Currency** is not stated in the dataset, so no currency symbol is used. Digit grouping follows the regional settings of the computer.

## 8. Related files

`docs/kpi_definitions.md`, `docs/data_dictionary.md`, `docs/database_schema.md`, `docs/cleaning_rules.md`, `docs/module3_findings.md`, `docs/module4_findings.md`, `powerbi/measures.dax`, screenshots in `docs/figures/`.