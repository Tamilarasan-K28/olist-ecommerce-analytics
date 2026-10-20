"""
rfm.py: RFM segmentation of people (customer_unique_id).
Run: python -m src.rfm
Writes reports/rfm_segments.csv (one row per person) and reports/rfm_summary.csv.
"""
import pandas as pd

from src.db import get_engine

SEGMENTS = {
    # (frequency score, recency score >= 3?) -> label (author's definitions)
}


def label(row):
    if row["revenue"] <= 0:
        return "no_revenue"
    recent = row["r_score"] >= 3
    repeat = row["f_score"] == 2
    if repeat and recent:
        return "loyal_recent"
    if repeat:
        return "repeat_lapsed"
    if recent:
        return "new_recent"
    return "one_time_lapsed"


def main():
    df = pd.read_sql_query("SELECT * FROM analytics.v_customer_orders", get_engine())
    df["revenue"] = df["revenue"].astype(float)
    df["last_order"] = pd.to_datetime(df["last_order"])
    snapshot = df["last_order"].max().normalize() + pd.Timedelta(days=1)
    df["recency_days"] = (snapshot - df["last_order"]).dt.days
    print("snapshot date:", snapshot.date(), "| people:", len(df))

    # Recency: lower days = better; rank first so ties cannot break qcut.
    df["r_score"] = pd.qcut(df["recency_days"].rank(method="first", ascending=False),
                            4, labels=[1, 2, 3, 4]).astype(int)
    df["f_score"] = (df["orders"] >= 2).astype(int) + 1
    pos = df["revenue"] > 0
    df["m_score"] = 0
    df.loc[pos, "m_score"] = pd.qcut(df.loc[pos, "revenue"].rank(method="first"),
                                     4, labels=[1, 2, 3, 4]).astype(int)
    df["segment"] = df.apply(label, axis=1)

    summary = (df.groupby("segment")
               .agg(people=("customer_unique_id", "size"),
                    avg_recency_days=("recency_days", "mean"),
                    avg_orders=("orders", "mean"),
                    total_revenue=("revenue", "sum"))
               .round(2).reset_index())
    summary["pct_people"] = (100 * summary["people"] / len(df)).round(2)
    summary["pct_revenue"] = (100 * summary["total_revenue"] / df["revenue"].sum()).round(2)
    print(summary.to_string(index=False))

    assert len(df) == 96096, "people count differs from Module 1"
    assert round(df["revenue"].sum(), 2) == 13494400.74, "revenue differs"
    df.to_csv("reports/rfm_segments.csv", index=False)
    summary.to_csv("reports/rfm_summary.csv", index=False)
    print("\nChecks passed.")


if __name__ == "__main__":
    main()