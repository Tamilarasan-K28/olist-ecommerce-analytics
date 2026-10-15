# Table Relationships, Keys and Granularity

Status: based on Step 2 profiling of the raw Olist files. Figures marked "derived" are arithmetic on measured values.

| Table | Grain (one row =) | Key | Notes |
|---|---|---|---|
| customers | a customer_id (one order's customer record) | customer_id | customer_unique_id identifies the person: 96,096 distinct over 99,441 rows |
| orders | an order | order_id | 99,441 rows |
| order_items | an item line in an order | order_id + order_item_id | 112,650 rows over 98,666 orders |
| payments | a payment line in an order | order_id + payment_sequential | 103,886 rows over 99,440 orders |
| reviews | a review row | review_id + order_id | review_id alone is NOT unique (814 extra rows) |
| products | a product | product_id | 610 blank categories (derived) |
| sellers | a seller | seller_id | 3,095 rows |
| translation | a category | product_category_name | 71 rows; 2 product categories absent from it |
| geolocation | a coordinate sample | none | 19,015 distinct zips over 1,000,163 rows; 261,831 fully duplicated rows |

## Relationships (all core foreign keys have zero orphans)
- orders.customer_id -> customers.customer_id (1:1 in this data)
- order_items.order_id -> orders.order_id (many:1)
- order_items.product_id -> products.product_id (many:1)
- order_items.seller_id -> sellers.seller_id (many:1)
- payments.order_id -> orders.order_id (many:1)
- reviews.order_id -> orders.order_id (many:1)
- products.product_category_name -> translation (13 rows / 2 categories unmatched)
- customers/sellers zip -> geolocation zip (278 customer rows and 7 seller rows unmatched; geolocation is many rows per zip)

## Join rules
1. Aggregate items, payments and reviews to one row per order BEFORE joining to orders.
2. Never join geolocation on zip without first reducing it to one row per zip.
3. Use customer_unique_id, not customer_id, for repeat-customer analysis.
4. Never sum order-level or payment-level money after joining to item rows.

## Open items
- Decide the review de-duplication rule after Step 3 investigation.
- Decide how to treat timestamp inversions (1,359 carrier-before-approval; 23 delivery-before-carrier).
- Confirm zip-code string lengths (leading zeros).
