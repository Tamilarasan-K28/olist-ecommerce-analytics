-- 02_staging_remaining.sql
DROP TABLE IF EXISTS staging.reviews;
DROP TABLE IF EXISTS staging.payments_by_order;
DROP TABLE IF EXISTS staging.category_translation;

CREATE TABLE staging.reviews (
    review_id               TEXT,
    order_id                TEXT,
    review_score            INTEGER,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

CREATE TABLE staging.payments_by_order (
    order_id                TEXT,
    payment_rows            INTEGER,
    payment_total           NUMERIC(14,2),
    max_installments        INTEGER,
    distinct_payment_types  INTEGER,
    has_not_defined_payment BOOLEAN
);

CREATE TABLE staging.category_translation (
    product_category_name         TEXT,
    product_category_name_english TEXT
);
