from pathlib import Path

from .analysis import (
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


def main() -> None:
    data_path = Path("data/model_errors.csv")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    data = load_model_errors(data_path)
    table = build_paired_table(data)
    differences = table["difference"].to_numpy(dtype=float)

    summary = summarize_differences(differences)
    t_result = paired_t_analysis(differences)
    sign_result = exact_sign_flip_test(differences)
    bootstrap_ci = paired_bootstrap_ci(
        differences,
        seed=SEED,
        resamples=BOOTSTRAP_RESAMPLES,
    )

    csv_path = output_dir / "store_differences.csv"
    figure_path = output_dir / "store_differences.png"
    table.to_csv(csv_path, index=False)
    plot_differences(table, figure_path)

    print(table.to_string(index=False))
    print("\nResumen:", summary)
    print("Prueba t e IC:", t_result)
    print("Cambios de signo:", sign_result)
    print("Bootstrap pareado:", bootstrap_ci)
    print(f"\nTabla guardada en: {csv_path}")
    print(f"Figura guardada en: {figure_path}")


if __name__ == "__main__":
    main()

