from __future__ import annotations

from itertools import product
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

REQUIRED_COLUMNS = ("store_id", "error_a", "error_b")
SEED = 20260829
BOOTSTRAP_RESAMPLES = 10_000

ERROR_COLUMNS = ("error_a", "error_b")


def load_model_errors(path: str | Path) -> pd.DataFrame:
    """Carga y valida la tabla con un par de errores por tienda."""
    df = pd.read_csv(path)

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            f"Faltan columnas obligatorias en el archivo: {', '.join(missing)}."
        )

    df = df.loc[:, list(REQUIRED_COLUMNS)].copy()

    identifiers = df["store_id"]
    if identifiers.isna().any():
        raise ValueError("El identificador store_id no puede ser nulo.")
    df["store_id"] = identifiers.astype(str).str.strip()
    if (df["store_id"] == "").any():
        raise ValueError("El identificador store_id no puede ser una cadena vacía.")
    if not df["store_id"].is_unique:
        duplicated = sorted(df.loc[df["store_id"].duplicated(), "store_id"].unique())
        raise ValueError(
            "Cada identificador store_id debe ser único; "
            f"se repiten: {', '.join(duplicated)}."
        )

    for column in ERROR_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")
        if values.isna().any():
            raise ValueError(
                f"La columna {column} debe contener errores numéricos y finitos."
            )
        values = values.astype(float)
        if not np.isfinite(values.to_numpy()).all():
            raise ValueError(f"La columna {column} contiene un error no finito.")
        if (values < 0).any():
            raise ValueError(
                f"La columna {column} contiene un error negativo; "
                "un error absoluto no puede ser negativo."
            )
        df[column] = values

    if df.empty:
        raise ValueError("El archivo no contiene tiendas para comparar.")

    return df.reset_index(drop=True)


def build_paired_table(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la tabla por tienda con diferencia error_a - error_b."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            f"Faltan columnas obligatorias para construir los pares: {', '.join(missing)}."
        )

    table = df.loc[:, list(REQUIRED_COLUMNS)].copy()

    if not table["store_id"].is_unique:
        raise ValueError(
            "Los pares se verifican mediante store_id: los identificadores deben ser únicos."
        )

    # El par se forma dentro de la fila, de modo que ambos errores pertenecen
    # siempre a la misma tienda; la longitud de dos vectores no lo garantiza.
    table["difference"] = table["error_a"] - table["error_b"]
    table["favors"] = np.select(
        [table["difference"] > 0, table["difference"] < 0],
        ["B", "A"],
        default="empate",
    )

    return table.reset_index(drop=True)


def summarize_differences(differences: np.ndarray) -> dict[str, float | int]:
    """Resume tamaño, media, desviación muestral y error estándar."""
    values = np.asarray(differences, dtype=float)
    if values.ndim != 1:
        raise ValueError("Las diferencias deben formar un vector unidimensional.")
    n = int(values.size)
    if n < 2:
        raise ValueError("Se requieren al menos dos tiendas para estimar la dispersión.")

    sample_sd = float(np.std(values, ddof=1))

    return {
        "n": n,
        "mean": float(np.mean(values)),
        "sample_sd": sample_sd,
        "standard_error": sample_sd / np.sqrt(n),
    }


def paired_t_analysis(
    differences: np.ndarray,
    *,
    confidence: float = 0.95,
) -> dict[str, float | int | tuple[float, float]]:
    """Prueba t bilateral de una muestra e intervalo para la media pareada."""
    values = np.asarray(differences, dtype=float)
    summary = summarize_differences(values)
    n = int(summary["n"])
    degrees_of_freedom = n - 1

    # Una muestra sobre el vector de diferencias, no dos muestras independientes.
    result = stats.ttest_1samp(values, popmean=0.0, alternative="two-sided")

    critical = float(stats.t.ppf(0.5 + confidence / 2, degrees_of_freedom))
    margin = critical * summary["standard_error"]
    mean = summary["mean"]

    return {
        "t_statistic": float(result.statistic),
        "degrees_of_freedom": degrees_of_freedom,
        "p_value": float(result.pvalue),
        "confidence_interval": (float(mean - margin), float(mean + margin)),
    }


def exact_sign_flip_test(differences: np.ndarray) -> dict[str, float | int]:
    """Enumera todas las configuraciones de signos y calcula un p-value bilateral."""
    values = np.asarray(differences, dtype=float)
    if values.ndim != 1:
        raise ValueError("Las diferencias deben formar un vector unidimensional.")
    n = int(values.size)
    if n == 0:
        raise ValueError("Se requiere al menos una tienda para enumerar los signos.")

    observed = float(np.abs(np.mean(values)))
    total_configurations = 2**n

    # Bajo la nula de simetría, cada tienda puede cambiar de signo de forma
    # independiente: para n=16 se enumeran las 2**16 = 65536 configuraciones.
    signs = np.array(list(product((1.0, -1.0), repeat=n)), dtype=float)
    null_means = np.abs(signs @ values) / n

    tolerance = 1e-12
    extreme_count = int(np.count_nonzero(null_means >= observed - tolerance))

    return {
        "n": n,
        "observed_mean": float(np.mean(values)),
        "total_configurations": total_configurations,
        "extreme_count": extreme_count,
        "p_value": extreme_count / total_configurations,
    }


def paired_bootstrap_ci(
    differences: np.ndarray,
    *,
    seed: int = SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Intervalo percentil para la media, remuestreando unidades pareadas completas."""
    values = np.asarray(differences, dtype=float)
    if values.ndim != 1:
        raise ValueError("Las diferencias deben formar un vector unidimensional.")
    n = int(values.size)
    if n == 0:
        raise ValueError("Se requiere al menos una tienda para remuestrear.")
    if resamples < 1:
        raise ValueError("El número de remuestras debe ser positivo.")

    rng = np.random.default_rng(seed)
    # Se remuestrean tiendas completas: los índices seleccionan el par entero,
    # nunca los errores de A y de B por separado.
    indices = rng.integers(0, n, size=(resamples, n))
    boot_means = values[indices].mean(axis=1)

    alpha = 1.0 - confidence
    low, high = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])

    return (float(low), float(high))


def plot_differences(table: pd.DataFrame, output_path: str | Path) -> Path:
    """Guarda una visualización por tienda con una referencia visible en cero."""
    required = ("store_id", "difference")
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise ValueError(
            f"La tabla no contiene las columnas necesarias para la figura: {', '.join(missing)}."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stores = table["store_id"].astype(str).tolist()
    values = table["difference"].to_numpy(dtype=float)
    colors = ["#2166ac" if value > 0 else "#b2182b" for value in values]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    ax.bar(stores, values, color=colors, edgecolor="black", linewidth=0.6)
    ax.axhline(0.0, color="black", linewidth=1.4)
    ax.axhline(
        float(values.mean()),
        color="#4d4d4d",
        linestyle="--",
        linewidth=1.2,
        label=f"Diferencia media = {values.mean():.4f}",
    )

    for index, value in enumerate(values):
        offset = 0.05 if value >= 0 else -0.05
        ax.text(
            index,
            value + offset,
            f"{value:+.1f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8,
        )

    ax.set_title(
        "Diferencia de error absoluto por tienda (error_a - error_b)\n"
        "Positivo favorece a B; negativo favorece a A"
    )
    ax.set_xlabel("Tienda (store_id)")
    ax.set_ylabel("Diferencia en unidades vendidas")
    ax.margins(y=0.18)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False)

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)

    return output_path
