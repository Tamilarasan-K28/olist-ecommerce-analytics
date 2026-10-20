# KPI Definitions

One definition per KPI. SQL, Python and Power BI must all follow these. Currency is not stated in the dataset.

| KPI | Definition | Grain | Filter / denominator |
|---|---|---|---|
| Revenue | Sum of item price | item line | Orders not canceled or unavailable (rule R18). Freight excluded |
| Freight | Sum of freight_value | item line | Same order filter as revenue |
| Orders (revenue-eligible) | Count of orders with at least one item | order | Not canceled or unavailable |
| Average order value (AOV) | Revenue / revenue-eligible orders | order | Same filter |
| Delivered orders (metric) | Orders with status delivered and a customer delivery date | order | delivery_metric_eligible |
| Average delivery days | Mean of days from purchase to customer delivery | order | Delivered orders (metric) |
| Late rate | Late delivered orders / delivered orders (metric) | order | Late = delivered after the estimated date |
| Average review score | Mean of order-level review score (latest review) | order | Orders with a review (rule R5) |
| Low-score share | Orders scoring 1 or 2 / orders with a review | order | Same filter |
| Repeat customer rate | People with 2 or more orders / people with 1 or more orders | person (customer_unique_id) | All orders; NOT a retention rate (see note) |
| Seller concentration | Share of revenue held by the top 10% of sellers | seller | Revenue-eligible sales |

## Notes
- Repeat rate is not retention: customers acquired late in the data have had little time to return. Cohorts (Module 4 step 3) handle that properly.
- Trend charts use the window 2017-01 to 2018-08 (assumption A1).
- Payment value is used for payment-method analysis only, never for revenue.