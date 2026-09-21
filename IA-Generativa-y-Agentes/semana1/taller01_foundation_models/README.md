# Taller 01 — Foundation Models: Comparación, Decodificación y Razonamiento

MMIA 6013 · IA Generativa y Agentes · Universidad San Francisco de Quito
Jaime Astudillo y Roberth Chachalo

**Tarea:** aritmética de 2-3 pasos con respuesta entera única (10 casos limpios
+ 3 contaminados), verificada automáticamente.

## Estructura

```
├── taller-01-informe.pdf     # informe final (LaTeX, clase llncs)
├── taller-01-informe.ipynb   # notebook ejecutado: código, tablas y figuras
├── informe-latex/            # fuente del PDF: informe.tex, tablas/, figuras/
├── src/
│   ├── casos.py              # carga de casos y verificador
│   ├── clientes.py           # llamar() a OpenAI y a Ollama, precios
│   ├── prompts.py            # las cuatro plantillas de la Parte 3
│   ├── barridos.py           # bucles de las Partes 1-4 y escritura del CSV
│   └── parte0.py             # mediciones locales con GPT-2
├── scripts/
│   ├── ejecutar_parte0.py    # Parte 0 (local, sin API)
│   ├── ejecutar_partes.py    # Partes 1, 2.a, 2.b, 3, 4 con la API de OpenAI
│   ├── ejecutar_local.py     # Parte 1 (tercera ranura), 2.a y top_k con Ollama
│   ├── clasificar_2a.py      # matriz declarado/observado desde el CSV
│   ├── graficas.py           # tablas y figuras desde el CSV
│   └── generar_latex.py      # informe.tex desde CSV, figuras y notebook
├── datos/
│   ├── casos.json            # los 13 casos con respuesta esperada
│   ├── resultados.csv        # CSV crudo: una fila por llamada (850)
│   ├── tabla_*.csv           # tablas derivadas del CSV
│   └── parte0_*.{csv,jsonl}  # logits, distribuciones y generaciones de GPT-2
└── figuras/                  # PNG (se regeneran desde el CSV)
```

## Reproducir

```bash
pip install -r requirements.txt      # o: uv sync
cp .env.example .env                 # y pon la clave de OpenAI dentro
ollama pull qwen3:1.7b               # para las partes locales

python scripts/ejecutar_parte0.py    # Parte 0, GPT-2 en CPU (~550 MB la primera vez)
python scripts/ejecutar_partes.py    # Partes 1-4 con la API (~0.06 USD)
python scripts/ejecutar_local.py     # partes con Ollama
python scripts/clasificar_2a.py && python scripts/graficas.py
python scripts/generar_latex.py && cd informe-latex && pdflatex informe.tex && pdflatex informe.tex
```

Cada ejecución **añade** filas a `datos/resultados.csv`; no borra las anteriores.

## Modelos y precios (tabla semestral del curso)

| Fila | Modelo | USD/M entrada | USD/M salida | Verificado |
|---|---|---|---|---|
| `base_local` | `openai-community/gpt2` | 0 | 0 | — |
| `propietario_economico` | `gpt-4o-mini` | 0,15 | 0,60 | 2026-08-26 |
| `openai_razonamiento` | `gpt-5.6-luna` | 0,20 | 1,20 | 2026-09-18 |
| `open_weight_pequeno` | `qwen3:1.7b` (Ollama) | 0 | 0 | — |

## Notas de medición

- Las sondas de 2.a y la rejilla de 2.b (750 llamadas) se mandaron con 4
  peticiones en paralelo; el barrido de `top_k` en local, en secuencia.
- Los tokens de razonamiento de qwen3 se miden en tokens: `eval_count` de
  Ollama menos los tokens de la respuesta visible (tokenizador de Qwen3).
- `ollama pull qwen3:1.7b` y la descarga de GPT-2 (~550 MB) y del tokenizador
  de Qwen3 necesitan red la primera vez.

## Credenciales

Las claves se leen de `.env`, excluido por `.gitignore`. Ninguna aparece en el
código, el notebook, el CSV ni el PDF.
