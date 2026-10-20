# Data Cleaning Rules (DRAFT)

Principles: raw files are never modified. Cleaning writes new files to data/processed/.
Problems are flagged rather than silently deleted. Every rule cites a measured number.

| ID | Table | Finding (measured) | Rule | Status |
|---|---|---|---|---|
| R1 | all | Blank values are stored as empty strings | Convert blank or whitespace-only text to NULL | Decided |
| R2 | orders, items, reviews | 0 unparseable timestamps in all 8 date columns | Parse as datetime (format YYYY-MM-DD HH:MM:SS) | Decided |
| R3 | customers, sellers, geolocation | All zips have length 5 | Keep zip as 5-character text; never convert to number | Decided |
| R4 | reviews | 789 review_ids repeat (814 extra rows); every group has identical score, message and date but different orders | Do NOT drop by review_id. Keep all 99,224 rows. Key = review_id + order_id | Decided |
| R5 | reviews | 547 orders have 2-3 review rows; 202 have differing scores | Build an order-level review table: review_count, has_conflicting_scores, and one score per order taken from the most recent review_answer_timestamp (ties: review_creation_date, then review_id) | Assumption |
| R6 | products | 610 products have blank category | Set english category to 'unknown'; keep a flag | Decided |
| R7 | products | 2 categories (13 products) are missing from the translation table | Add a documented manual mapping and keep the original Portuguese name | Assumption (translation is mine, to be reviewed) |
| R8 | geolocation | 19,015 distinct zips over 1,000,163 rows; 261,831 fully duplicated rows | Build a one-row-per-zip table using the median latitude and longitude of all samples | Assumption |
| R9 | customers, sellers | 278 customer rows and 7 seller rows have zips absent from geolocation | Keep rows, leave coordinates NULL, add a flag. Do not guess a location | Decided |
| R10 | orders | 1,359 carrier-before-approval; 23 delivery-before-carrier | Keep timestamps unchanged; add flag columns. Delivery duration uses purchase to customer delivery, which has 0 inversions | Decided |
| R11 | orders | 8 delivered orders have no customer delivery date; 6 canceled orders have one | Exclude the 8 from delivery metrics; flag the 6 | Decided |
| R12 | orders | 775 orders have no items (603 unavailable, 164 canceled, 5 created, 2 invoiced, 1 shipped) | Keep in orders; add has_items flag; flag the 3 invoiced/shipped as unexplained | Decided |
| R13 | payments | 4,446 extra rows beyond one per order; 1 delivered order has no payment | Aggregate to one row per order before joining; flag the order without payment | Decided |
| R14 | payments | 3 rows have payment_type not_defined | Keep and flag | Pending (see Q6) |
| R15 | payments | payment_value min is 0 and installments min is 0 | Decide after Q6 | Pending |
| R16 | geolocation | Coordinate range not yet checked | Flag rows outside Brazil | Pending (see Q8) |
| R17 | customers, sellers | State codes not yet inspected | Validate against the 2-letter list | Pending (see Q8) |
| R18 | order_items, payments | Revenue definition not yet chosen | Choose after Q7 reconciliation | Pending |

## Decisions recorded (Step 4)
- R5, R7, R8 confirmed by the project author. R7 translations are MANUAL (author's own) and are labelled category_source = manual.
- R14 to R17 are implemented as flags only (flag_payment_type_not_defined, flag_zero_payment_value, flag_zero_installments, flag_outside_brazil_box, flag_invalid_state). No values are changed or removed. Final treatment awaits review of investigation_pending_rules.txt.
- R18 (revenue definition) remains open. Cleaned tables keep price, freight_value and payment_value untouched.

## Final decisions (Step 4b)
- R14: not_defined payments (3 rows, all value 0, all on canceled orders) kept and flagged; excluded from payment-type analysis.
- R15: 6 zero-value vouchers kept. 2 zero-installment credit card rows kept and flagged.
- R16: geolocation coordinates flagged against an approximate Brazil box (an assumption). 42 raw rows were outside it; zip-level count measured separately.
- R17: 0 invalid state codes. No action.
- R18: Revenue = sum of price (order_items) for non-canceled, non-unavailable orders. Freight reported separately. payment_value used for payment-method analysis and reconciliation only. 378 of 98,665 orders differ by more than 0.01 between payments and items (about 0.38%); unexplained and flagged.
- R19: product_weight_g = 0 (4 products) treated as missing for weight analysis (author's assumption).

## Step 5 implementation notes
- R16 implemented: zips with median coordinates outside the approximate Brazil box (an assumption) get lat/lng set to missing; raw medians kept in lat_median_raw / lng_median_raw.
- R18 implemented: order_financials table (one row per order). revenue = sum of price for orders with items that are not canceled or unavailable. Payment totals used for reconciliation only.
- R19 implemented: flag_zero_weight and product_weight_g_clean (zero weight treated as missing; author's assumption).
