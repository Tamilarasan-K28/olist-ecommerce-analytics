-- 05_analytics_checks.sql: analytics schema vs Module 1 reconciliation figures.
SELECT 'revenue' AS check_name, SUM(revenue) AS sql_value, 13494400.74 AS module1_value
FROM analytics.fact_orders
UNION ALL
SELECT 'revenue via items join', SUM(i.price), 13494400.74
FROM analytics.fact_order_items i
JOIN analytics.fact_orders o USING (order_id)
WHERE o.order_status NOT IN ('canceled','unavailable')
UNION ALL
SELECT 'total freight', SUM(freight_value), 2251909.54 FROM analytics.fact_order_items
UNION ALL
SELECT 'total payments', SUM(payment_value), 16008872.12 FROM analytics.fact_payments
UNION ALL
SELECT 'late delivered orders', COUNT(*), 7826 FROM analytics.fact_orders WHERE is_late
UNION ALL
SELECT 'delivery-eligible orders', COUNT(*), 96470
FROM analytics.fact_orders WHERE delivery_metric_eligible
UNION ALL
SELECT 'distinct customer_unique_id', COUNT(DISTINCT customer_unique_id), 96096
FROM analytics.dim_customers
UNION ALL
SELECT 'orders with a review', COUNT(*), 98673
FROM analytics.fact_orders WHERE review_count IS NOT NULL;