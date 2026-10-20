# Module 4: Customer and Operational Analytics

KPI definitions are in docs/kpi_definitions.md. Revenue = sum of item price for non-canceled, non-unavailable orders. Currency is not stated in the dataset.

## Reference KPI values (src/kpis.py)
Revenue 13,494,400.74 | AOV 137.42 | Delivered orders (metric) 96,470 | Average delivery days 12.56 | Late rate 8.11% | Average review score 4.086 | Low-score share 14.69% | Repeat customer rate 3.12%.

## Findings
| # | Finding | Evidence | Type |
|---|---|---|---|
| G1 | Almost all customers order once | Repeat rate 3.12% of 96,096 people | Measured |
| G2 | Repeat customers are about 3.1% of people and 5.7% of revenue | RFM: loyal_recent + repeat_lapsed | Measured |
| G3 | Fully observed cohorts repeat rarely | 180-day repeat rate 1.56% to 2.52% (2017-01 to 2018-03 cohorts) | Measured |
| G4 | No clear cohort trend | Rates vary within a narrow band; not tested for significance | Description |
| G5 | Cross-state deliveries are slower and later | 15.15 vs 7.95 days; 9.27% vs 6.06% late | Measured |
| G6 | Late orders are spread across many sellers | Top 20 sellers by late orders: 24.0% of late orders, 20.6% of orders | Measured |

## Report-ready statements
- About 97% of customers placed a single order; repeat customers are rare and account for about 5.7% of revenue.
- Between 1.6% and 2.5% of customers acquired from 2017-01 to 2018-03 ordered again within 180 days.
- Cross-state deliveries took about 15 days versus 8 for same-state deliveries, and 9.3% were late versus 6.1%.

## Limitations
- M1: RFM segments are author-defined; recency and monetary scores are quartiles, so "recent" means the more recent half, not recent in an absolute sense.
- M2: The RFM snapshot date (2018-10-18) lies beyond the dense data (ends about 2018-08), which inflates absolute recency days.
- M3: Cohort returns count orders of any status and only purchases visible in this dataset.
- M4: Cohort differences of a few tenths of a point were not tested for significance.
- M5: Route type (same vs cross state) is a crude proxy for distance.
- M6: Seller of an order is the seller of item 1; 1,275 orders have more than one seller.
- M7: Seller-level rates use sellers with at least 50 orders (author's threshold), covering 75.4% of delivered orders.
- M8: Delivery time cannot be split into seller handling and carrier transit.
- M9: The 1,113 no-revenue people have an average recency of 358 days; the reason was not investigated.