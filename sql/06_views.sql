-- 06_views.sql: reusable analytical views. Each states its grain.
CREATE OR REPLACE VIEW analytics.v_monthly_sales AS   -- grain: one row per purchase month
SELECT date_trunc('month', order_purchase_timestamp)::date AS month,
       COUNT(*)                         AS orders_eligible,
       SUM(revenue)                     AS revenue,
       SUM(items_freight_total)         AS freight,
       ROUND(AVG(revenue), 2)           AS avg_order_revenue
FROM analytics.fact_orders
WHERE is_revenue_eligible
GROUP BY 1;

CREATE OR REPLACE VIEW analytics.v_category_sales AS  -- grain: one row per English category
SELECT p.product_category_english AS category,
       COUNT(*)                   AS items_sold,
       COUNT(DISTINCT i.order_id) AS orders,
       SUM(i.price)               AS revenue
FROM analytics.fact_order_items i
JOIN analytics.fact_orders o   USING (order_id)
JOIN analytics.dim_products p  USING (product_id)
WHERE o.order_status NOT IN ('canceled','unavailable')
GROUP BY 1;

CREATE OR REPLACE VIEW analytics.v_seller_performance AS  -- grain: one row per seller
SELECT s.seller_id, s.seller_state,
       COUNT(*)                   AS items_sold,
       COUNT(DISTINCT i.order_id) AS orders,
       SUM(i.price)               AS revenue
FROM analytics.fact_order_items i
JOIN analytics.fact_orders o  USING (order_id)
JOIN analytics.dim_sellers s  USING (seller_id)
WHERE o.order_status NOT IN ('canceled','unavailable')
GROUP BY s.seller_id, s.seller_state;

CREATE OR REPLACE VIEW analytics.v_delivery_by_state AS  -- grain: one row per customer state
SELECT c.customer_state,
       COUNT(*)                                   AS delivered_orders,
       ROUND(AVG(o.delivery_days)::numeric, 2)    AS avg_delivery_days,
       ROUND(100.0 * AVG(o.is_late::int), 2)      AS late_pct
FROM analytics.fact_orders o
JOIN analytics.dim_customers c USING (customer_id)
WHERE o.delivery_metric_eligible
GROUP BY c.customer_state;

CREATE OR REPLACE VIEW analytics.v_customer_orders AS  -- grain: one row per PERSON (customer_unique_id)
SELECT c.customer_unique_id,
       COUNT(*)                          AS orders,
       MIN(o.order_purchase_timestamp)   AS first_order,
       MAX(o.order_purchase_timestamp)   AS last_order,
       COALESCE(SUM(o.revenue), 0)       AS revenue
FROM analytics.fact_orders o
JOIN analytics.dim_customers c USING (customer_id)
GROUP BY c.customer_unique_id;