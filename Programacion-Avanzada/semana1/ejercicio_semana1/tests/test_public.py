from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from week1_exercise import (
    FEATURES,
    ServerMeasurements,
    build_measurements,
    compute_load_score,
    enrich_dataframe,
    build_summary,
    save_and_validate_parquet,
)

DATA = Path("data/server_measurements.csv")


def load_df():
    return pd.read_csv(DATA, parse_dates=["timestamp"])


# ============================================================
# TAREA 1 - ServerMeasurements
# ============================================================

def test_batch_contract():
    df = load_df()
    batch = build_measurements(df)

    assert isinstance(batch, ServerMeasurements)
    assert batch.values.shape == (len(df), len(FEATURES))
    assert batch.feature_names == FEATURES
    assert isinstance(batch.feature_names, tuple)
    assert np.issubdtype(batch.values.dtype, np.floating)


def test_invalid_batch_rejected():
    """values debe ser una matriz NumPy bidimensional."""
    with pytest.raises(ValueError):
        ServerMeasurements(
            np.array([1.0, 2.0]),
            ("a",),
        )


def test_feature_count_must_match_columns():
    """Cada columna debe tener exactamente un nombre de característica."""
    values = np.array([
        [10.0, 20.0, 30.0],
        [40.0, 50.0, 60.0],
    ])

    with pytest.raises(ValueError):
        ServerMeasurements(
            values,
            ("gpu", "cpu"),
        )


def test_non_numeric_values_rejected():
    """La matriz debe contener datos numéricos."""
    values = np.array([
        ["high", "50", "20"],
        ["low", "40", "18"],
    ])

    with pytest.raises(ValueError):
        ServerMeasurements(
            values,
            ("gpu", "cpu", "memory"),
        )


def test_batch_repr():
    """__repr__ debe mostrar shape y nombres de características."""
    values = np.array([
        [10.0, 20.0, 30.0],
        [40.0, 50.0, 60.0],
    ])

    batch = ServerMeasurements(
        values,
        ("gpu", "cpu", "memory"),
    )

    text = repr(batch)

    assert "ServerMeasurements" in text
    assert "shape=(2, 3)" in text
    assert "gpu" in text
    assert "cpu" in text
    assert "memory" in text


# ============================================================
# TAREA 2 - Normalización y load_score
# ============================================================

def test_load_score_shapes_and_finiteness():
    batch = build_measurements(load_df())

    zscores, load_score, means = compute_load_score(batch)

    assert zscores.shape == batch.values.shape
    assert load_score.shape == (batch.values.shape[0],)
    assert means.shape == (batch.values.shape[1],)

    assert np.isfinite(zscores).all()
    assert np.isfinite(load_score).all()

    assert np.allclose(
        zscores.mean(axis=0),
        0.0,
        atol=1e-10,
    )

    assert np.allclose(
        zscores.std(axis=0),
        1.0,
        atol=1e-10,
    )

    weights = np.array([0.50, 0.30, 0.20])

    assert np.allclose(
        load_score,
        zscores @ weights,
    )


# ============================================================
# TAREA 3 - DataFrame enriquecido
# ============================================================

def test_enriched_dataframe_contract():
    df = load_df()

    batch = build_measurements(df)
    _, score, _ = compute_load_score(batch)

    out = enrich_dataframe(df, score)

    assert len(out) == len(df)

    assert {
        "load_score",
        "requires_review",
    }.issubset(out.columns)

    assert out["requires_review"].dtype == bool
    assert out["requires_review"].any()


# ============================================================
# TAREA 4 - Resumen por servidor
# ============================================================

def test_summary_contract():
    df = load_df()

    batch = build_measurements(df)
    _, score, _ = compute_load_score(batch)

    out = enrich_dataframe(df, score)
    summary = build_summary(out)

    assert list(summary.columns) == [
        "server",
        "observations",
        "mean_power_w",
        "max_temperature_c",
        "mean_load",
        "review_count",
    ]

    assert set(summary["server"]) == set(df["server"])

# ============================================================
# TAREA 5 - Guardar y verificar el resultado en Parquet
# ============================================================

def test_parquet_roundtrip(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    df = load_df()

    batch = build_measurements(df)
    _, score, _ = compute_load_score(batch)
    out = enrich_dataframe(df, score)

    path = tmp_path / "server_analysis.parquet"

    save_and_validate_parquet(out, path)

    assert path.exists()

    expected = pa.Table.from_pandas(
        out,
        preserve_index=False,
    )

    restored = pq.read_table(path)

    assert restored.num_rows == expected.num_rows
    assert restored.column_names == expected.column_names
    assert restored.schema == expected.schema
    assert restored.equals(expected)