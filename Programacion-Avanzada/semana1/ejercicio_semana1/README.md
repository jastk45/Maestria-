# Ejercicio de refuerzo - Semana 1

Este paquete contiene el dataset y la estructura inicial del proyecto. El enunciado completo se encuentra en `Ejercicio_Semana_1_Enunciado.pdf`.

## Preparación

El paquete inicial no incluye `uv.lock`. El primer `uv sync` lo generará a partir de `pyproject.toml`.

```bash
uv sync --group dev
git init
git add .
git commit -m "Inicializa ejercicio de semana 1"
```

Ejecute las pruebas públicas con:

```bash
uv run pytest -q
```

Cuando complete la implementación, ejecute:

```bash
uv run week1-exercise
```

El programa debe crear `output/server_analysis.parquet` y verificar su lectura.

Antes de entregar, genere el registro de commits:

```bash
git log --oneline > git_history.txt
```

No entregue `.venv/` ni archivos de caché.
