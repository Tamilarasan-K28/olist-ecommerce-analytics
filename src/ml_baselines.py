"""
ml_baselines.py: baselines and logistic regression, evaluated on VALIDATION only.
Run: python -m src.ml_baselines
The test split is not used here (see docs/ml_problem_definition.md).
Writes reports/ml_validation_results.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score,
                             roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "ml_dataset.csv"
OUT = ROOT / "reports" / "ml_validation_results.csv"

NUM = ["purchase_month", "purchase_dow", "purchase_hour", "estimated_days", "same_state",
       "n_items", "n_sellers", "n_products", "price_total", "freight_total",
       "total_weight_g", "max_installments", "payment_rows"]
CAT = ["customer_state", "seller_state", "category", "first_payment_type"]
LOG_COLS = ["price_total", "freight_total", "total_weight_g"]   # skewed money/weight


def metrics(name, y, score, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"model": name,
            "roc_auc": round(roc_auc_score(y, score), 4),
            "pr_auc": round(average_precision_score(y, score), 4),
            "precision": round(precision_score(y, pred, zero_division=0), 4),
            "recall": round(recall_score(y, pred, zero_division=0), 4),
            "f1": round(f1_score(y, pred, zero_division=0), 4),
            "flagged": int(pred.sum()), "tp": int(tp), "fp": int(fp),
            "fn": int(fn), "tn": int(tn)}


def best_f1_threshold(y, score):
    p, r, t = precision_recall_curve(y, score)
    f1 = 2 * p[:-1] * r[:-1] / np.maximum(p[:-1] + r[:-1], 1e-12)
    return float(t[f1.argmax()])


def main():
    df = pd.read_csv(DATA, parse_dates=["purchase_ts"])
    counts = df["split"].value_counts()
    assert counts["train"] == 57050 and counts["validation"] == 20550, "split sizes changed"
    for c in LOG_COLS:
        df[c] = np.log1p(df[c])          # NaN stays NaN

    tr = df[df["split"] == "train"]
    va = df[df["split"] == "validation"]
    ytr, yva = tr["is_late"].to_numpy(), va["is_late"].to_numpy()
    print(f"late rate: train {ytr.mean():.4f} | validation {yva.mean():.4f}")

    rows = []
    zeros = np.zeros(len(va), dtype=int)
    rows.append(metrics("never_late", yva, zeros, zeros))

    cross = (1 - va["same_state"]).to_numpy()
    rows.append(metrics("rule_cross_state", yva, cross, cross))

    q = tr["estimated_days"].quantile(0.25)
    short = (va["estimated_days"] <= q).astype(int).to_numpy()
    rows.append(metrics(f"rule_short_estimate(<={q:.1f}d)", yva,
                        -va["estimated_days"].to_numpy(), short))

    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                          ("sc", StandardScaler())]), NUM),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="missing")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", min_frequency=100))]), CAT),
    ])
    model = Pipeline([("prep", pre),
                      ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])
    model.fit(tr[NUM + CAT], ytr)
    s_tr = model.predict_proba(tr[NUM + CAT])[:, 1]
    s_va = model.predict_proba(va[NUM + CAT])[:, 1]
    print(f"logistic regression ROC-AUC: train {roc_auc_score(ytr, s_tr):.4f} | "
          f"validation {roc_auc_score(yva, s_va):.4f}")

    thr = best_f1_threshold(yva, s_va)
    rows.append(metrics("logreg_threshold_0.5", yva, s_va, (s_va >= 0.5).astype(int)))
    rows.append(metrics(f"logreg_val_best_f1_thr_{thr:.2f}", yva, s_va, (s_va >= thr).astype(int)))

    res = pd.DataFrame(rows)
    print("\nValidation results (late rate = %.4f):" % yva.mean())
    print(res.to_string(index=False))
    res.to_csv(OUT, index=False)

    names = model.named_steps["prep"].get_feature_names_out()
    coef = pd.Series(model.named_steps["clf"].coef_[0], index=names).sort_values()
    print("\nLargest negative coefficients (lower late risk):\n", coef.head(6).round(3).to_string())
    print("\nLargest positive coefficients (higher late risk):\n", coef.tail(6).round(3).to_string())
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()