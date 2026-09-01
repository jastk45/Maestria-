# Hackathon 1 - AI Model Operations Monitor

Lea primero `Hackathon_1_Enunciado.docx`.

## Inicio rapido

```bash
uv lock
uv sync --locked --group dev
git init
```

Cree un `.gitignore` apropiado antes del primer commit.

## Ejecucion

```bash
uv run pytest -q
uv run ai-model-monitor
```

El archivo principal que debe completar es:

```text
src/ai_model_monitor/core.py
```

No modifique `tests/test_public.py` ni `data/telemetry.csv`.
