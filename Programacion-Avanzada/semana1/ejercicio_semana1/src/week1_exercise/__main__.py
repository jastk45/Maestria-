from pathlib import Path
import pandas as pd

from .pipeline import (
    build_measurements,
    compute_load_score,
    enrich_dataframe,
    build_summary,
    save_and_validate_parquet,
)


def main() -> None:
    data_path = Path("data/server_measurements.csv")
    output_path = Path("output/server_analysis.parquet")

    df = pd.read_csv(data_path, parse_dates=["timestamp"])
    batch = build_measurements(df)
    print(batch)

    _, load_score, _ = compute_load_score(batch)
    analysis = enrich_dataframe(df, load_score)
    summary = build_summary(analysis)
    print()
    print("Resumen por servidor:")
    print(summary.to_string(index=False))

    restored = save_and_validate_parquet(analysis, output_path)
    print()
    print(f"Parquet verificado: {output_path} ({len(restored)} filas)")


if __name__ == "__main__":
    main()
