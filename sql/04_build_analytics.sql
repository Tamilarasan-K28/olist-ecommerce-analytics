-- 04_build_analytics.sql
-- Builds the analytics schema from staging. Runs in one transaction:
-- any failure (e.g. a key that cannot be created) rolls everything back.
BEGIN;

DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;

-- ---------- dimensions ----------
CREATE TABLE analytics.dim_customers AS
SELECT customer_id, customer_unique_id, customer_zip_code_prefix AS zip_code_prefix,
       customer_city, customer_state, flag_zip_not_in_geolocation
FROM staging.customers;
ALTER TABLE analytics.dim_customers ADD PRIMARY KEY (customer_id);
CREATE INDEX ix_dim_customers_unique ON analytics.dim_customers (customer_unique_id);
CREATE INDEX ix_dim_customers_state  ON analytics.dim_customers (customer_state);

CREATE TABLE analytics.dim_products AS
SELECT product_id, product_category_name, product_category_english, category_source,
       product_photos_qty, product_weight_g, product_weight_g_clean, flag_zero_weight,
       product_length_cm, product_height_cm, product_width_cm
FROM staging.products;
ALTER TABLE analytics.dim_products ADD PRIMARY KEY (product_id);
CREATE INDEX ix_dim_products_category ON analytics.dim_products (product_category_english);

CREATE TABLE analytics.dim_sellers AS
SELECT seller_id, seller_zip_code_prefix AS zip_code_prefix, seller_city, seller_state,
       flag_zip_not_in_geolocation
FROM staging.sellers;
ALTER TABLE analytics.dim_sellers ADD PRIMARY KEY (seller_id);
CREATE INDEX ix_dim_sellers_state ON analytics.dim_sellers (seller_state);

CREATE TABLE analytics.dim_geography AS
SELECT zip_code_prefix, lat, lng, sample_count, flag_outside_brazil_box
FROM staging.geolocation_zip;
ALTER TABLE analytics.dim_geography ADD PRIMARY KEY (zip_code_prefix);

-- ---------- facts ----------
CREATE TABLE analytics.fact_orders AS
SELECT o.order_id, o.customer_id, o.order_status,
       o.order_purchase_timestamp, o.order_approved_at,
       o.order_delivered_carrier_date, o.order_delivered_customer_date,
       o.order_estimated_delivery_date,
       o.delivery_metric_eligible, o.delivery_days, o.is_late,
       o.flag_carrier_before_approval, o.flag_delivery_before_carrier,
       f.item_count, f.items_price_total, f.items_freight_total,
       f.payment_total, f.payment_minus_items, f.flag_payment_item_mismatch,
       f.is_revenue_eligible, f.revenue,
       pb.payment_rows, pb.max_installments,
       r.review_count, r.has_conflicting_scores, r.order_review_score
FROM staging.orders o
LEFT JOIN staging.order_financials f  USING (order_id)
LEFT JOIN staging.payments_by_order pb USING (order_id)
LEFT JOIN staging.order_reviews r      USING (order_id);
ALTER TABLE analytics.fact_orders ADD PRIMARY KEY (order_id);
ALTER TABLE analytics.fact_orders
  ADD FOREIGN KEY (customer_id) REFERENCES analytics.dim_customers (customer_id);
CREATE INDEX ix_fact_orders_purchase ON analytics.fact_orders (order_purchase_timestamp);
CREATE INDEX ix_fact_orders_status   ON analytics.fact_orders (order_status);
CREATE INDEX ix_fact_orders_customer ON analytics.fact_orders (customer_id);

CREATE TABLE analytics.fact_order_items AS
SELECT order_id, order_item_id, product_id, seller_id, shipping_limit_date,
       price, freight_value
FROM staging.order_items;
ALTER TABLE analytics.fact_order_items ADD PRIMARY KEY (order_id, order_item_id);
ALTER TABLE analytics.fact_order_items
  ADD FOREIGN KEY (order_id)   REFERENCES analytics.fact_orders (order_id),
  ADD FOREIGN KEY (product_id) REFERENCES analytics.dim_products (product_id),
  ADD FOREIGN KEY (seller_id)  REFERENCES analytics.dim_sellers (seller_id);
CREATE INDEX ix_items_product ON analytics.fact_order_items (product_id);
CREATE INDEX ix_items_seller  ON analytics.fact_order_items (seller_id);

CREATE TABLE analytics.fact_payments AS
SELECT order_id, payment_sequential, payment_type, payment_installments, payment_value,
       flag_payment_type_not_defined, flag_zero_payment_value, flag_zero_installments
FROM staging.payments;
ALTER TABLE analytics.fact_payments ADD PRIMARY KEY (order_id, payment_sequential);
ALTER TABLE analytics.fact_payments
  ADD FOREIGN KEY (order_id) REFERENCES analytics.fact_orders (order_id);
CREATE INDEX ix_payments_type ON analytics.fact_payments (payment_type);

CREATE TABLE analytics.fact_reviews AS
SELECT review_id, order_id, review_score, review_creation_date, review_answer_timestamp
FROM staging.reviews;
ALTER TABLE analytics.fact_reviews ADD PRIMARY KEY (review_id, order_id);
ALTER TABLE analytics.fact_reviews
  ADD FOREIGN KEY (order_id) REFERENCES analytics.fact_orders (order_id);
ALTER TABLE analytics.fact_reviews
  ADD CONSTRAINT ck_review_score CHECK (review_score BETWEEN 1 AND 5);

-- ---------- sanity checks (the transaction rolls back if one fails) ----------
DO $$
DECLARE n_orders BIGINT; n_stage BIGINT;
BEGIN
  SELECT COUNT(*) INTO n_orders FROM analytics.fact_orders;
  SELECT COUNT(*) INTO n_stage  FROM staging.orders;
  IF n_orders <> n_stage THEN
    RAISE EXCEPTION 'fact_orders has % rows but staging.orders has % (join multiplied or lost rows)', n_orders, n_stage;
  END IF;
END $$;

COMMIT;