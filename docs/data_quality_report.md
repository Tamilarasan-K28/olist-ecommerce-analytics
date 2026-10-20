# Data Quality Report (Module 1)

All figures below were measured on the Olist files downloaded for this project (see docs/dataset_source_and_license.md). Rules are in docs/cleaning_rules.md.

## Scope
9 raw tables (99,441 orders; 112,650 order items; 1,000,163 geolocation rows). Raw files were never modified; SHA-256 hashes are in reports/data_quality/raw_data_manifest.csv.

## Findings and treatment
| Area | Finding | Treatment |
|---|---|---|
| Keys | Core primary keys unique; 0 orphan foreign keys on core relationships | None needed |
| Reviews | 789 review_ids repeat on different orders with identical content; 547 orders have 2-3 reviews, 202 with differing scores | Kept all rows; one order-level score from the latest review |
| Geolocation | 19,015 distinct zips over 1,000,163 rows; 261,831 duplicate rows | One row per zip, median coordinates; 8 zips outside the Brazil box set to missing (4 customers affected) |
| Timestamps | 1,359 carrier-before-approval; 23 delivery-before-carrier | Flagged, not changed |
| Order status | 8 delivered orders lack a delivery date; 6 canceled orders have one; 3 invoiced/shipped orders have no items | Flagged; excluded from delivery metrics where relevant |
| Payments | 3 not_defined rows (all 0 value, canceled orders); 6 zero vouchers; 2 zero-installment credit card rows | Kept and flagged |
| Payment vs items | 303 orders differ by more than 1 cent after rounding; 250 by more than 1 unit | Flagged; cause not determined |
| Products | 610 blank categories; 13 products in 2 categories missing from the translation table; 4 zero weights | unknown label; manual translation (author's own); zero weight treated as missing |

## Validation
- 11 unit tests pass.
- Pipeline validation passes (unique keys, no orphan foreign keys).
- Independent reconciliation: 10 of 10 checks pass (revenue 13,494,400.74; late delivered orders 7,826 of 96,470).

## Assumptions and limitations
- The Brazil bounding box, revenue definition (sum of price for non-canceled, non-unavailable orders), latest-review rule and zero-weight rule are the author's choices.
- The two manual category translations are the author's own.
- Currency is not stated in the dataset.
- The 303 payment/item mismatches are unexplained.
- Reconciliation shows the code follows the rules; it does not prove the rules are correct.
