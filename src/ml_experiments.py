"""
ml_experiments.py: time-aware features and gradient boosting, VALIDATION only.
Run: python -m src.ml_experiments
The test split is not used. Writes reports/ml_validation_experiments.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.db import get_engine
from src.ml_baselines import CAT, LOG_COLS, NUM

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "ml_dataset.csv"
OUT = ROOT / "reports" / "ml_validation_experiments.csv"

SQL_EXTRA = """
SELECT o.order_id, i.seller_id, o.order_delivered_customer_date AS delivered_ts
FROM analytics.fact_orders o
JOIN analytics.fact_order_items i ON i.order_id = o.order_id AND i.order_item_id = 1
WHERE o.delivery_metric_eligible
"""
SQL_ALL = "SELECT order_purchase_timestamp AS ts FROM analytics.fact_orders"
TIME = ["platform_late_14d", "platform_n_14d", "state_late_30d", "state_n_30d",
        "seller_late_prior", "seller_n_prior", "orders_last_7d"]


def prior_rate(df, key, window_days, alpha, prior):
    """Smoothed late rate among the group's orders DELIVERED BEFORE each purchase."""
    rate = np.full(len(df), np.nan)
    count = np.zeros(len(df))
    for _, idx in df.groupby(key).indices.items():
        g = df.iloc[idx]
        order = np.argsort(g["delivered_ts"].values)
        d = g["delivered_ts"].values[order]
        late_cum = np.concatenate([[0], np.cumsum(g["is_late"].values[order])])
        p = g["purchase_ts"].values
        hi = np.searchsorted(d, p, side="left")            # delivered strictly before purchase
        lo = (np.searchsorted(d, p - np.timedelta64(window_days, "D"), side="left")
              if window_days else 0)
        n = hi - lo
        rate[idx] = (late_cum[hi] - late_cum[lo] + alpha * prior) / (n + alpha)
        count[idx] = n
    return rate, count


def brute(df, i, key, window, alpha, prior):
    r = df.iloc[i]
    m = (df[key] == r[key]) & (df["delivered_ts"] < r["purchase_ts"])
    if window:
        m &= df["delivered_ts"] >= r["purchase_ts"] - pd.Timedelta(days=window)
    return (df.loc[m, "is_late"].sum() + alpha * prior) / (m.sum() + alpha)


def logreg(num_cols):
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                          ("sc", StandardScaler())]), num_cols),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="missing")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", min_frequency=100))]), CAT)])
    return Pipeline([("prep", pre), ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])


def hgb():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                          min_samples_leaf=100, l2_regularization=1.0,
                                          categorical_features="from_dtype", random_state=42)


def summarise(name, y, s):
    p, r, t = precision_recall_curve(y, s)
    f1 = 2 * p[:-1] * r[:-1] / np.maximum(p[:-1] + r[:-1], 1e-12)
    j = f1.argmax()
    k = int(0.10 * len(y))
    top = np.argsort(-s)[:k]
    prec10 = y[top].mean()
    return {"model": name, "roc_auc": round(roc_auc_score(y, s), 4),
            "pr_auc": round(average_precision_score(y, s), 4),
            "top10_precision": round(prec10, 4), "top10_recall": round(y[top].sum() / y.sum(), 4),
            "top10_lift": round(prec10 / y.mean(), 2),
            "best_f1(optimistic)": round(f1[j], 4), "its_precision": round(p[j], 4),
            "its_recall": round(r[j], 4)}


def main():
    eng = get_engine()
    df = pd.read_csv(DATA, parse_dates=["purchase_ts"])
    df = df.merge(pd.read_sql_query(SQL_EXTRA, eng, parse_dates=["delivered_ts"]),
                  on="order_id", how="left")
    assert len(df) == 96470 and df["delivered_ts"].notna().all() and df["seller_id"].notna().all()
    assert (df["delivered_ts"] >= df["purchase_ts"]).all(), "a delivery precedes its purchase"
    df = df.sort_values("purchase_ts").reset_index(drop=True)
    df["all"] = 1
    train_rate = df.loc[df["split"] == "train", "is_late"].mean()
    print(f"smoothing prior (train late rate): {train_rate:.4f}")

    df["platform_late_14d"], df["platform_n_14d"] = prior_rate(df, "all", 14, 50, train_rate)
    df["state_late_30d"], df["state_n_30d"] = prior_rate(df, "customer_state", 30, 30, train_rate)
    df["seller_late_prior"], df["seller_n_prior"] = prior_rate(df, "seller_id", None, 20, train_rate)
    ts_all = np.sort(pd.to_datetime(pd.read_sql_query(SQL_ALL, eng)["ts"]).values)
    p = df["purchase_ts"].values
    df["orders_last_7d"] = (np.searchsorted(ts_all, p, side="left")
                            - np.searchsorted(ts_all, p - np.timedelta64(7, "D"), side="left"))

    # leakage self-check against a slow brute-force version
    for i in np.random.default_rng(0).choice(len(df), 200, replace=False):
        assert np.isclose(df.loc[i, "seller_late_prior"], brute(df, i, "seller_id", None, 20, train_rate))
        assert np.isclose(df.loc[i, "state_late_30d"], brute(df, i, "customer_state", 30, 30, train_rate))
        assert np.isclose(df.loc[i, "platform_late_14d"], brute(df, i, "all", 14, 50, train_rate))
    print("leakage self-check passed (200 random orders)")
    print(df[TIME].describe().round(3).T.to_string())

    for c in LOG_COLS:
        df[c] = np.log1p(df[c])
    dh = df.copy()
    for c in CAT:
        dh[c] = dh[c].astype("category")

    base = NUM + CAT
    time_all = base + TIME
    no_month = [c for c in time_all if c != "purchase_month"]
    specs = [("logreg_base", logreg(NUM), df, base),
             ("logreg_time", logreg(NUM + TIME), df, time_all),
             ("hgb_base", hgb(), dh, base),
             ("hgb_time", hgb(), dh, time_all),
             ("hgb_time_no_month", hgb(), dh, no_month)]

    rows, fitted = [], {}
    for name, model, frame, feats in specs:
        tr, va = frame[frame["split"] == "train"], frame[frame["split"] == "validation"]
        model.fit(tr[feats], tr["is_late"])
        s = model.predict_proba(va[feats])[:, 1]
        rows.append(summarise(name, va["is_late"].to_numpy(), s))
        fitted[name] = (model, va, feats, s)
    res = pd.DataFrame(rows)
    print("\nValidation (late rate %.4f):" % fitted["hgb_base"][1]["is_late"].mean())
    print(res.to_string(index=False))
    res.to_csv(OUT, index=False)

    best = res.sort_values("pr_auc", ascending=False).iloc[0]["model"]
    model, va, feats, s = fitted[best]
    print("\nbest by validation PR-AUC:", best)
    month = va["purchase_ts"].dt.to_period("M").astype(str)
    by = pd.DataFrame({"m": month, "y": va["is_late"].to_numpy(), "s": s}).groupby("m")
    print(by.apply(lambda g: pd.Series({"orders": len(g), "late_rate": g["y"].mean().round(4),
                                        "mean_score": g["s"].mean().round(4),
                                        "roc_auc": round(roc_auc_score(g["y"], g["s"]), 4)})).to_string())
    imp = permutation_importance(model, va[feats], va["is_late"], scoring="average_precision",
                                 n_repeats=3, random_state=0)
    print("\npermutation importance on validation (drop in PR-AUC):")
    print(pd.Series(imp.importances_mean, index=feats).sort_values(ascending=False).head(10).round(4).to_string())
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()