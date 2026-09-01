from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from week2_exercise import (
    BOOTSTRAP_RESAMPLES,
    SEED,
    build_paired_table,
    exact_sign_flip_test,
    load_model_errors,
    paired_bootstrap_ci,
    paired_t_analysis,
    plot_differences,
    summarize_differences,
)

DATA = Path("data/model_errors.csv")


def load_table():
    return build_paired_table(load_model_errors(DATA))


def test_load_contract():
    df = load_model_errors(DATA)
    assert list(df.columns) == ["store_id", "error_a", "error_b"]
    assert df.shape == (16, 3)
    assert df["store_id"].is_unique
    assert np.isfinite(df[["error_a", "error_b"]].to_numpy()).all()


def test_invalid_identifiers_rejected(tmp_path):
    path = tmp_path / "duplicates.csv"
    pd.DataFrame({
        "store_id": ["S01", "S01"],
        "error_a": [1.0, 2.0],
        "error_b": [1.2, 1.8],
    }).to_csv(path, index=False)
    with pytest.raises(ValueError, match="identificador|store_id|único"):
        load_model_errors(path)


def test_invalid_errors_rejected(tmp_path):
    path = tmp_path / "invalid.csv"
    pd.DataFrame({
        "store_id": ["S01", "S02"],
        "error_a": [1.0, np.nan],
        "error_b": [1.2, -1.0],
    }).to_csv(path, index=False)
    with pytest.raises(ValueError, match="error|finito|negativo"):
        load_model_errors(path)


def test_paired_table_contract():
    table = load_table()
    assert list(table.columns) == [
        "store_id", "error_a", "error_b", "difference", "favors"
    ]
    assert np.allclose(table["difference"], table["error_a"] - table["error_b"])
    assert set(table["favors"]) == {"A", "B"}
    assert (table.loc[table["difference"] > 0, "favors"] == "B").all()
    assert (table.loc[table["difference"] < 0, "favors"] == "A").all()


def test_summary_values():
    differences = load_table()["difference"].to_numpy()
    result = summarize_differences(differences)
    assert set(result) == {"n", "mean", "sample_sd", "standard_error"}
    assert result["n"] == 16
    assert np.isclose(result["mean"], 0.41875)
    assert np.isclose(result["standard_error"], result["sample_sd"] / 4)


def test_t_analysis_contract():
    differences = load_table()["difference"].to_numpy()
    result = paired_t_analysis(differences)
    assert set(result) == {"t_statistic", "degrees_of_freedom", "p_value", "confidence_interval"}
    assert result["degrees_of_freedom"] == 15
    assert np.isclose(result["t_statistic"], 1.336388, atol=1e-6)
    assert np.isclose(result["p_value"], 0.201342, atol=1e-6)
    low, high = result["confidence_interval"]
    assert low < 0 < high
    assert low < 0.41875 < high


def test_sign_flip_is_exact_and_two_sided():
    differences = load_table()["difference"].to_numpy()
    result = exact_sign_flip_test(differences)
    assert result["total_configurations"] == 2**16
    assert result["extreme_count"] == 13372
    assert np.isclose(result["p_value"], 13372 / 2**16)


def test_bootstrap_is_reproducible_and_paired():
    differences = load_table()["difference"].to_numpy()
    first = paired_bootstrap_ci(
        differences,
        seed=SEED,
        resamples=BOOTSTRAP_RESAMPLES,
    )
    second = paired_bootstrap_ci(
        differences,
        seed=SEED,
        resamples=BOOTSTRAP_RESAMPLES,
    )
    assert first == second
    assert np.allclose(first, (-0.19375, 1.00625), atol=1e-12)


def test_plot_created(tmp_path):
    table = load_table()
    path = tmp_path / "differences.png"
    returned = plot_differences(table, path)
    assert returned == path
    assert path.exists()
    assert path.stat().st_size > 10_000
