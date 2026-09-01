# Ejercicio de refuerzo - Semana 2

Este paquete contiene los datos y la estructura inicial del proyecto. Lea primero `Ejercicio_Semana_2_Enunciado.pdf`.

## Preparación

Desde la raíz del proyecto:

```bash
uv sync --group dev
git init
git add .
git commit -m "Inicializa ejercicio de semana 2"
```

Complete las funciones de `src/week2_exercise/analysis.py` y las respuestas de `informe.md`.

Ejecute las pruebas públicas con:

```bash
uv run pytest -q
```

Cuando complete la implementación, ejecute:

```bash
uv run week2-exercise
```

El programa debe crear:

- `output/store_differences.csv`
- `output/store_differences.png`

Antes de entregar, genere el registro de commits:

```bash
git log --oneline > git_history.txt
```

No entregue `.venv/`, cachés ni archivos temporales.

