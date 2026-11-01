# Module 6: Late-Delivery Prediction (Problem Definition)

## Question
Given what is known at the moment an order is placed, will it be delivered after its estimated delivery date?

## Target
`is_late` = 1 if order_delivered_customer_date > order_estimated_delivery_date, else 0. Same definition as the Late Rate KPI (docs/kpi_definitions.md).

## Population
Delivery-eligible orders (status delivered with a customer delivery date): 96,470 in the full data. Modelling window: purchases 2017-01 to 2018-08.

## Prediction point
Purchase time. Only information available when the order is placed may be used.

## Split (by purchase date, never random)
- Train: 2017-01 to 2018-02
- Validation: 2018-03 to 2018-05 (model choice and threshold)
- Test: 2018-06 to 2018-08 (final report, used once)

## Allowed features
Purchase month, weekday and hour; estimated days (estimate minus purchase); same-state flag; customer state; seller state; item-1 category; item count; distinct sellers; distinct products; price total; freight total; total weight; first payment type; maximum installments; payment lines.

## Forbidden (leakage)
Approval, carrier and customer delivery timestamps; delivery_days; review score and dates; any flag built from those; historical seller or state late rates computed without a strict time cutoff.

## Assumptions
- Payment details are known at purchase (the data has no payment timestamps).
- Seller and category are those of item 1; n_sellers is a feature because 1,275 orders have several sellers.
- Orders not delivered by the end of the data are absent, which may understate lateness in the latest months.

## Evaluation (planned)
Baseline (never late), a simple rule, logistic regression, and a tree ensemble. Metrics: precision, recall, F1, ROC-AUC, PR-AUC and the confusion matrix, with the decision threshold chosen on validation. Accuracy alone is not reported as a success measure, because late orders are a small minority.