from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

NUMERIC_FEATURES = ("latency_ms", "cpu_pct", "memory_mb", "requests_s")
WEIGHTS = np.array([0.40, 0.25, 0.20, 0.15], dtype=float)
RISK_THRESHOLD = 1.00
CONFIDENCE_THRESHOLD = 0.60


def load_telemetry(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["timestamp"])


class TelemetryBatch:
    """Lote de variables numericas con un esquema de caracteristicas estable."""

    def __init__(self, values, feature_names):
        values = np.asarray(values, dtype=float)
        if values.ndim != 2:
            raise ValueError(f"values debe ser 2D, se recibio ndim={values.ndim}")

        feature_names = tuple(feature_names)
        if values.shape[1] != len(feature_names):
            raise ValueError(
                f"columnas ({values.shape[1]}) != nombres ({len(feature_names)})"
            )

        self.values = values
        self.feature_names = feature_names

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(n_rows={self.values.shape[0]}, "
            f"features={self.feature_names})"
        )

    def __add__(self, other: TelemetryBatch) -> TelemetryBatch:
        if not isinstance(other, TelemetryBatch):
            return NotImplemented
        if self.feature_names != other.feature_names:
            raise ValueError(
                "esquemas incompatibles: "
                f"{self.feature_names} != {other.feature_names}"
            )
        return TelemetryBatch(
            np.vstack((self.values, other.values)), self.feature_names
        )

    def standardize(self) -> np.ndarray:
        mean = self.values.mean(axis=0)
        std = self.values.std(axis=0)
        safe_std = np.where(std == 0, 1.0, std)
        return (self.values - mean) / safe_std


def compute_risk_score(z_values: np.ndarray, weights: np.ndarray = WEIGHTS) -> np.ndarray:
    """Calcule sum(abs(z) * weights) para cada observacion."""
    z_values = np.asarray(z_values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if z_values.shape[1] != weights.shape[0]:
        raise ValueError(
            f"columnas ({z_values.shape[1]}) != pesos ({weights.shape[0]})"
        )
    return np.abs(z_values) @ weights


def add_alert_columns(
    df: pd.DataFrame,
    risk_score: np.ndarray,
    risk_threshold: float = RISK_THRESHOLD,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> pd.DataFrame:
    """Agregue risk_score y alert sin modificar el DataFrame recibido."""
    risk_score = np.asarray(risk_score, dtype=float)
    if risk_score.shape != (len(df),):
        raise ValueError(
            f"risk_score con {risk_score.shape} no coincide con {len(df)} filas"
        )

    out = df.copy()
    out["risk_score"] = risk_score

    confidence = out["confidence"]

    out["alert"] = (
        (out["risk_score"] >= risk_threshold)
        | (confidence < confidence_threshold)
        | confidence.isna()
    )
    return out


def summarize_by_model(df: pd.DataFrame) -> pd.DataFrame:
    """Genere una fila por modelo con las metricas pedidas en el enunciado.

    Cambia la granularidad: 1 fila = 1 modelo (no 1 ejecucion). as_index=False
    deja model como columna en vez de indice. alert_rate se calcula despues de
    agregar: la media de una columna booleana es la proporcion de True.
    """
    summary = (
        df.groupby("model", as_index=False)
        .agg(
            executions=("model", "size"),
            alerts=("alert", "sum"),
            mean_latency_ms=("latency_ms", "mean"),
            mean_risk_score=("risk_score", "mean"),
        )
    )
    summary["alerts"] = summary["alerts"].astype(int)
    summary["alert_rate"] = summary["alerts"] / summary["executions"]

    return summary.loc[
        :,
        [
            "model",
            "executions",
            "alerts",
            "alert_rate",
            "mean_latency_ms",
            "mean_risk_score",
        ],
    ]


def save_and_validate_parquet(df: pd.DataFrame, path: str | Path):
    """Convierta a Arrow, escriba Parquet y verifique el round trip."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    restored = pq.read_table(path)

    assert restored.num_rows == table.num_rows, (
        f"filas {restored.num_rows} != {table.num_rows}"
    )
    assert restored.column_names == table.column_names, (
        f"columnas {restored.column_names} != {table.column_names}"
    )
    assert restored.schema.equals(table.schema), (
        f"esquema {restored.schema} != {table.schema}"
    )
    assert restored.equals(table), "los valores cambiaron en el round trip"

    return restored
