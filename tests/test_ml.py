"""Tests for the ML pipeline: leakage-safe features, splits, inference robustness."""
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier

from src import ml_build_dataset as mb
from src.ml_experiments import TIME, brute, prior_rate


def make(n=80, seed=1):
    rng = np.random.default_rng(seed)
    p = pd.Timestamp("2018-01-01") + pd.to_timedelta(np.sort(rng.integers(0, 60 * 24, n)), unit="h")
    d = p + pd.to_timedelta(rng.integers(24, 24 * 15, n), unit="h")
    return pd.DataFrame({"purchase_ts": p, "delivered_ts": d, "is_late": rng.integers(0, 2, n),
                         "key": rng.choice(["a", "b", "c"], n), "all": 1})


@pytest.mark.parametrize("window", [None, 14])
def test_prior_rate_matches_brute_force(window):
    df = make()
    rate, _ = prior_rate(df, "key", window, 10, 0.08)
    expected = [brute(df, i, "key", window, 10, 0.08) for i in range(len(df))]
    assert np.allclose(rate, expected)


def test_order_never_sees_its_own_or_a_simultaneous_delivery():
    t0, t1 = pd.Timestamp("2018-01-01"), pd.Timestamp("2018-01-05")
    df = pd.DataFrame({"purchase_ts": [t0, t1], "delivered_ts": [t1, t1 + pd.Timedelta(days=3)],
                       "is_late": [1, 0], "key": ["a", "a"], "all": 1})
    rate, count = prior_rate(df, "key", None, 10, 0.08)
    assert count[0] == 0 and np.isclose(rate[0], 0.08)
    assert count[1] == 0


def test_splits_do_not_overlap():
    s = mb.SPLITS
    assert s[0][2] == s[1][1] and s[1][2] == s[2][1]
    assert all(a[1] < a[2] for a in s)


def test_no_forbidden_or_post_purchase_feature():
    assert not (set(mb.FEATURES) & mb.FORBIDDEN)
    assert not any("review" in c or "delivery_days" in c for c in mb.FEATURES + TIME)


def test_hgb_handles_unseen_category_and_missing_values():
    rng = np.random.default_rng(0)
    n = 600
    X = pd.DataFrame({"num": rng.normal(size=n),
                      "cat": pd.Categorical(rng.choice(["a", "b"], n), categories=["a", "b"])})
    m = HistGradientBoostingClassifier(max_iter=20, categorical_features="from_dtype",
                                       random_state=0).fit(X, rng.integers(0, 2, n))
    new = pd.DataFrame({"num": [0.0, np.nan], "cat": pd.Categorical(["c", None], categories=["a", "b"])})
    p = m.predict_proba(new)[:, 1]
    assert p.shape == (2,) and not np.isnan(p).any() and ((p >= 0) & (p <= 1)).all()