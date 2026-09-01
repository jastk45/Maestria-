from pathlib import Path

from .core import (
    NUMERIC_FEATURES,
    TelemetryBatch,
    add_alert_columns,
    compute_risk_score,
    load_telemetry,
    save_and_validate_parquet,
    summarize_by_model,
)


def main():
    data_path = Path("data/telemetry.csv")
    output_path = Path("output/telemetry_alerts.parquet")

    df = load_telemetry(data_path)
    batch = TelemetryBatch(df.loc[:, NUMERIC_FEATURES].to_numpy(), NUMERIC_FEATURES)
    z_values = batch.standardize()
    risk_score = compute_risk_score(z_values)
    enriched = add_alert_columns(df, risk_score)
    summary = summarize_by_model(enriched)

    save_and_validate_parquet(enriched, output_path)

    print(batch)
    print("\nResumen por modelo:")
    print(summary.to_string(index=False))
    print(f"\nParquet: {output_path}")


if __name__ == "__main__":
    main()
