-- 07_query_library.sql
-- Each query is separated by a "-- Q<n>:" header so the runner can split the file.

-- Q1: Order counts by status (aggregation, beginner)
SELECT order_status, COUNT(*) AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 3) AS pct
FROM analytics.fact_orders
GROUP BY order_status
ORDER BY orders DESC;

-- Q2: Date range of purchases and months covered (check for partial months)
SELECT MIN(order_purchase_timestamp) AS first_purchase,
       MAX(order_purchase_timestamp) AS last_purchase,
       COUNT(DISTINCT date_trunc('month', order_purchase_timestamp)) AS months_covered
FROM analytics.fact_orders;

-- Q3: Month-over-month revenue change (window function: LAG)
SELECT month, orders_eligible, revenue,
       LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 2) AS pct_change
FROM analytics.v_monthly_sales
ORDER BY month;

-- Q4: Top 10 categories by revenue with share of total (window: SUM OVER)
SELECT category, items_sold, orders, revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 2) AS pct_of_revenue
FROM analytics.v_category_sales
ORDER BY revenue DESC
LIMIT 10;

-- Q5: Top 3 sellers per state by revenue (CTE + window: RANK)
WITH ranked AS (
    SELECT seller_state, seller_id, revenue, orders,
           RANK() OVER (PARTITION BY seller_state ORDER BY revenue DESC) AS rnk
    FROM analytics.v_seller_performance
)
SELECT * FROM ranked WHERE rnk <= 3 ORDER BY seller_state, rnk;

-- Q6: Delivery performance by state, worst late rate first (view + HAVING)
SELECT customer_state, delivered_orders, avg_delivery_days, late_pct
FROM analytics.v_delivery_by_state
WHERE delivered_orders >= 100
ORDER BY late_pct DESC;

-- Q7: Review score vs lateness (join + conditional aggregation)
SELECT CASE WHEN is_late THEN 'late' ELSE 'on_time' END AS delivery_outcome,
       COUNT(*) AS orders,
       ROUND(AVG(order_review_score), 3) AS avg_review_score,
       ROUND(100.0 * AVG((order_review_score <= 2)::int), 2) AS pct_low_scores
FROM analytics.fact_orders
WHERE delivery_metric_eligible AND order_review_score IS NOT NULL
GROUP BY 1;

-- Q8: People with more than one order (subquery on the person-level view)
SELECT COUNT(*) AS customers,
       COUNT(*) FILTER (WHERE orders > 1) AS repeat_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE orders > 1) / COUNT(*), 2) AS repeat_pct
FROM analytics.v_customer_orders;