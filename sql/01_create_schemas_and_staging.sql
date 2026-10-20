-- 01_create_schemas_and_staging.sql
-- Staging tables mirror the cleaned CSV files (data/processed/*_clean.csv).
-- Run: psql -U postgres -h localhost -d olist -f sql/01_create_schemas_and_staging.sql

DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

CREATE TABLE staging.customers (
    customer_id                 TEXT,
    customer_unique_id          TEXT,
    customer_zip_code_prefix    TEXT,
    customer_city               TEXT,
    customer_state              TEXT,
    flag_zip_not_in_geolocation BOOLEAN,
    flag_invalid_state          BOOLEAN
);

CREATE TABLE staging.orders (
    order_id                              TEXT,
    customer_id                           TEXT,
    order_status                          TEXT,
    order_purchase_timestamp              TIMESTAMP,
    order_approved_at                     TIMESTAMP,
    order_delivered_carrier_date          TIMESTAMP,
    order_delivered_customer_date         TIMESTAMP,
    order_estimated_delivery_date         TIMESTAMP,
    has_items                             BOOLEAN,
    has_payment                           BOOLEAN,
    flag_carrier_before_approval          BOOLEAN,
    flag_delivery_before_carrier          BOOLEAN,
    flag_delivered_missing_delivery_date  BOOLEAN,
    flag_canceled_with_delivery_date      BOOLEAN,
    flag_no_items_unexplained             BOOLEAN,
    delivery_metric_eligible              BOOLEAN,
    delivery_days                         NUMERIC,
    is_late                               BOOLEAN
);

CREATE TABLE staging.order_items (
    order_id            TEXT,
    order_item_id       INTEGER,
    product_id          TEXT,
    seller_id           TEXT,
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(12,2),
    freight_value       NUMERIC(12,2)
);

CREATE TABLE staging.products (
    product_id                  TEXT,
    product_category_name       TEXT,
    product_name_lenght         NUMERIC,
    product_description_lenght  NUMERIC,
    product_photos_qty          NUMERIC,
    product_weight_g            NUMERIC,
    product_length_cm           NUMERIC,
    product_height_cm           NUMERIC,
    product_width_cm            NUMERIC,
    category_source             TEXT,
    product_category_english    TEXT,
    flag_zero_weight            BOOLEAN,
    product_weight_g_clean      NUMERIC
);

CREATE TABLE staging.sellers (
    seller_id                   TEXT,
    seller_zip_code_prefix      TEXT,
    seller_city                 TEXT,
    seller_state                TEXT,
    flag_zip_not_in_geolocation BOOLEAN,
    flag_invalid_state          BOOLEAN
);

CREATE TABLE staging.geolocation_zip (
    zip_code_prefix         TEXT,
    lat                     DOUBLE PRECISION,
    lng                     DOUBLE PRECISION,
    sample_count            INTEGER,
    flag_outside_brazil_box BOOLEAN,
    lat_median_raw          DOUBLE PRECISION,
    lng_median_raw          DOUBLE PRECISION
);

CREATE TABLE staging.order_financials (
    order_id                   TEXT,
    order_status               TEXT,
    item_count                 NUMERIC,
    items_price_total          NUMERIC(14,2),
    items_freight_total        NUMERIC(14,2),
    payment_total              NUMERIC(14,2),
    payment_minus_items        NUMERIC(14,2),
    flag_payment_item_mismatch BOOLEAN,
    is_revenue_eligible        BOOLEAN,
    revenue                    NUMERIC(14,2)
);

CREATE TABLE staging.payments (
    order_id                      TEXT,
    payment_sequential            INTEGER,
    payment_type                  TEXT,
    payment_installments          INTEGER,
    payment_value                 NUMERIC(12,2),
    flag_payment_type_not_defined BOOLEAN,
    flag_zero_payment_value       BOOLEAN,
    flag_zero_installments        BOOLEAN
);

CREATE TABLE staging.order_reviews (
    order_id               TEXT,
    review_count           INTEGER,
    distinct_scores        INTEGER,
    has_conflicting_scores BOOLEAN,
    selected_review_id     TEXT,
    order_review_score     INTEGER
);