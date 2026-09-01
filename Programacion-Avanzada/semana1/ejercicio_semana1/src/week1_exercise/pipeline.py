from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

FEATURES = ("gpu_utilization", "cpu_utilization", "memory_gb")
WEIGHTS = np.array([0.50, 0.30, 0.20], dtype=float)
MAX_LOAD, MAX_TEMPERATURE = 1.5, 80.0


class ServerMeasurements:
    """Matriz numérica de mediciones junto a los nombres de sus características."""

    def __init__(self, values: np.ndarray, feature_names: tuple[str, ...]):
        values, feature_names = np.asarray(values), tuple(feature_names)

        if values.ndim != 2:
            raise ValueError(f"values debe ser bidimensional, se recibió ndim={values.ndim}")
        if not np.issubdtype(values.dtype, np.number):
            raise ValueError(f"values debe ser numérico, se recibió dtype={values.dtype}")
        if values.shape[1] != len(feature_names):
            raise ValueError(
                f"{values.shape[1]} columnas no coinciden con {len(feature_names)} nombres"
            )

        self.values = values.astype(float)
        self.feature_names = feature_names

    def __repr__(self) -> str:
        return f"ServerMeasurements(shape={self.values.shape}, features={self.feature_names})"


def build_measurements(df: pd.DataFrame) -> ServerMeasurements:
    """Construye ServerMeasurements usando las columnas definidas en FEATURES."""
    return ServerMeasurements(df.loc[:, list(FEATURES)].to_numpy(dtype=float), FEATURES)


def compute_load_score(batch: ServerMeasurements) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Retorna zscores, load_score y medias por característica."""
    values = batch.values
    means, stds = values.mean(axis=0), values.std(axis=0)

    # Una columna constante queda en z-score 0 en lugar de dividir por cero.
    zscores = (values - means) / np.where(stds == 0, 1.0, stds)

    return zscores, zscores @ WEIGHTS, means


def enrich_dataframe(df: pd.DataFrame, load_score: np.ndarray) -> pd.DataFrame:
    """Añade load_score y requires_review sin modificar el DataFrame original."""
    out = df.copy()
    out["load_score"] = np.asarray(load_score, dtype=float)
    out["requires_review"] = (
        (out["load_score"] > MAX_LOAD) | (out["temperature_c"] > MAX_TEMPERATURE)
    ).to_numpy(dtype=bool)
    return out


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Construye el resumen por servidor solicitado en el enunciado."""
    return df.groupby("server", as_index=False).agg(
        observations=("server", "size"),
        mean_power_w=("power_w", "mean"),
        max_temperature_c=("temperature_c", "max"),
        mean_load=("load_score", "mean"),
        review_count=("requires_review", "sum"),
    )


def save_and_validate_parquet(df: pd.DataFrame, output_path: str | Path) -> pd.DataFrame:
    """Guarda, lee y valida el round trip del DataFrame analizado."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    expected = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(expected, output_path)
    restored = pq.read_table(output_path)

    checks = {
        "Filas": restored.num_rows == expected.num_rows,
        "Columnas": restored.column_names == expected.column_names,
        "Esquema": restored.schema == expected.schema,
        "Valores": restored.equals(expected),
    }

    print(f"Round trip verificado: {output_path}")
    for nombre, ok in checks.items():
        print(f"{nombre}: {ok}")

    if not all(checks.values()):
        raise ValueError(f"El round trip de Parquet falló para {output_path}: {checks}")

    return restored.to_pandas()
