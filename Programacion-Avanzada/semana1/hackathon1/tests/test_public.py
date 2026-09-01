from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_model_monitor.core import (
    NUMERIC_FEATURES,
    TelemetryBatch,
    add_alert_columns,
    compute_risk_score,
    load_telemetry,
    save_and_validate_parquet,
    summarize_by_model,
)

DATA_PATH = Path("data/telemetry.csv")


def test_load_telemetry_contract():
    df = load_telemetry(DATA_PATH)
    assert len(df) == 240
    assert set(NUMERIC_FEATURES).issubset(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert int(df["confidence"].isna().sum()) == 4


def test_telemetry_batch_and_addition_do_not_mutate():
    a_values = np.array([[1, 2, 3, 4], [5, 6, 7, 8]], dtype=float)
    b_values = np.array([[9, 10, 11, 12]], dtype=float)
    a = TelemetryBatch(a_values, NUMERIC_FEATURES)
    b = TelemetryBatch(b_values, NUMERIC_FEATURES)

    a_before = a.values.copy()
    b_before = b.values.copy()
    c = a + b

    assert a.feature_names == NUMERIC_FEATURES
    assert isinstance(a.feature_names, tuple)
    assert c.values.shape == (3, 4)
    assert np.array_equal(a.values, a_before)
    assert np.array_equal(b.values, b_before)
    assert c is not a and c is not b


def test_standardize_is_columnwise():
    df = load_telemetry(DATA_PATH)
    batch = TelemetryBatch(df.loc[:, NUMERIC_FEATURES].to_numpy(), NUMERIC_FEATURES)
    z = batch.standardize()

    assert z.shape == batch.values.shape
    assert np.allclose(z.mean(axis=0), np.zeros(4), atol=1e-10)
    assert np.allclose(z.std(axis=0), np.ones(4), atol=1e-10)


def test_risk_score_formula():
    z = np.array([[1.2, -0.5, 0.1, 2.0]], dtype=float)
    score = compute_risk_score(z)
    assert score.shape == (1,)
    assert score[0] == pytest.approx(0.925)


def test_alert_rule_includes_missing_confidence():
    small = pd.DataFrame({
        "model": ["A", "A", "B"],
        "latency_ms": [10.0, 20.0, 30.0],
        "confidence": [0.90, 0.55, np.nan],
    })
    out = add_alert_columns(small, np.array([0.50, 0.40, 0.30]))
    assert out["alert"].tolist() == [False, True, True]
    assert "risk_score" in out.columns
    assert "alert" in out.columns


def test_summary_contract():
    sample = pd.DataFrame({
        "model": ["A", "A", "B"],
        "latency_ms": [10.0, 20.0, 30.0],
        "risk_score": [0.2, 1.4, 0.5],
        "alert": [False, True, True],
    })
    summary = summarize_by_model(sample)
    assert list(summary.columns) == [
        "model", "executions", "alerts", "alert_rate",
        "mean_latency_ms", "mean_risk_score",
    ]
    row_a = summary.loc[summary["model"] == "A"].iloc[0]
    assert row_a["executions"] == 2
    assert row_a["alerts"] == 1
    assert row_a["alert_rate"] == pytest.approx(0.5)
    assert row_a["mean_latency_ms"] == pytest.approx(15.0)


def test_parquet_round_trip(tmp_path):
    pytest.importorskip("pyarrow")
    df = pd.DataFrame({
        "model": ["A", "B"],
        "timestamp": pd.to_datetime(["2026-08-20 10:00", "2026-08-20 10:02"]),
        "risk_score": [0.3, 1.2],
        "alert": [False, True],
    })
    restored = save_and_validate_parquet(df, tmp_path / "test.parquet")
    assert restored.num_rows == 2
