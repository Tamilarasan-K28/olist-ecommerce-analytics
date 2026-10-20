-- 03_staging_checks.sql: staging values vs the Module 1 reconciliation report.
SELECT 'revenue (non-canceled/unavailable)' AS check_name,
       SUM(price) AS sql_value, 13494400.74 AS module1_value
FROM staging.order_items i
JOIN staging.orders o USING (order_id)
WHERE o.order_status NOT IN ('canceled', 'unavailable')
UNION ALL
SELECT 'total freight', SUM(freight_value), 2251909.54 FROM staging.order_items
UNION ALL
SELECT 'total payment value', SUM(payment_value), 16008872.12 FROM staging.payments
UNION ALL
SELECT 'revenue-eligible orders', COUNT(*), 98199 FROM staging.order_financials
WHERE is_revenue_eligible
UNION ALL
SELECT 'delivery-eligible orders', COUNT(*), 96470 FROM staging.orders
WHERE delivery_metric_eligible
UNION ALL
SELECT 'late delivered orders', COUNT(*), 7826 FROM staging.orders
WHERE is_late
UNION ALL
SELECT 'distinct customer_unique_id', COUNT(DISTINCT customer_unique_id), 96096
FROM staging.customers;
