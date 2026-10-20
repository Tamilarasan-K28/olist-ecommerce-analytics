"""
cohorts.py: repeat-purchase rate by first-order cohort, with fixed horizons.
Run: python -m src.cohorts
Writes reports/cohort_repeat_rates.csv.
"""
import pandas as pd

from src.db import get_engine, TREND_START, TREND_END

HORIZONS = (30, 90, 180)

SQL = """
SELECT c.customer_unique_id, o.order_purchase_timestamp AS ts
FROM analytics.fact_orders o
JOIN analytics.dim_customers c USING (customer_id)
"""


def main():
    df = pd.read_sql_query(SQL, get_engine())
    df["ts"] = pd.to_datetime(df["ts"])
    last_data = df["ts"].max()
    print("people:", df["customer_unique_id"].nunique(), "| orders:", len(df),
          "| last order:", last_data)
    assert len(df) == 99441 and df["customer_unique_id"].nunique() == 96096

    first = df.groupby("customer_unique_id")["ts"].min().rename("first_ts")
    d = df.join(first, on="customer_unique_id")
    d["days_after_first"] = (d["ts"] - d["first_ts"]).dt.total_seconds() / 86400

    people = first.reset_index()
    people["cohort"] = people["first_ts"].dt.to_period("M").dt.to_timestamp()
    people = people[people["cohort"].between(TREND_START, TREND_END)]

    rows = []
    for cohort, grp in people.groupby("cohort"):
        row = {"cohort": cohort.date(), "people": len(grp)}
        cohort_end = cohort + pd.offsets.MonthEnd(0) + pd.Timedelta(days=1)
        ids = set(grp["customer_unique_id"])
        sub = d[d["customer_unique_id"].isin(ids)]
        for h in HORIZONS:
            if cohort_end + pd.Timedelta(days=h) > last_data:
                row[f"repeat_{h}d_pct"] = None   # not fully observed
                continue
            back = sub[(sub["days_after_first"] >= 1) & (sub["days_after_first"] <= h)]
            row[f"repeat_{h}d_pct"] = round(100 * back["customer_unique_id"].nunique() / len(grp), 2)
        rows.append(row)

    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv("reports/cohort_repeat_rates.csv", index=False)


if __name__ == "__main__":
    main()