# Taller 01 — Foundation Models: Comparación, Decodificación y Razonamiento

**MMIA 6013 · IA Generativa y Agentes** — Universidad San Francisco de Quito
Semana 1, Sesión 05 · Entrega: 2026-09-19

## Qué mide este taller

Las cinco palancas que actúan en el momento de la inferencia, todas sobre
**un mismo problema con 10 casos de respuesta verificable automáticamente**:
cómo se elige el token, qué se pone en el prompt, qué forma tiene la salida,
qué cuesta, y cuánto piensa el modelo antes de responder.

**Tarea elegida:** aritmética de 2-3 pasos con respuesta entera única.
Elegida porque el nivel de esfuerzo de razonamiento (Parte 4, 25 % del taller)
necesita margen donde moverse: con una tarea trivial la curva sale plana.

## Estructura

```
├── taller-01-informe.ipynb   # el informe → se exporta a PDF
├── src/
│   ├── casos.py              # carga de casos + verificador
│   ├── clientes.py           # llamar() a OpenAI y a Ollama, precios, prompts
│   └── barridos.py           # bucles de las Partes 1-4 + escritura del CSV
├── datos/
│   ├── casos.json            # 10 casos limpios + 3 contaminados (Parte 4.b)
│   └── resultados.csv        # CSV crudo: una fila por llamada
└── figuras/                  # PNGs del informe (se regeneran desde el CSV)
```

`datos/resultados.csv` es un entregable y se versiona: las tablas del informe
se derivan de él. Las figuras no se versionan porque se regeneran; el CSV no
se regenera sin gastar dólares.

## Reproducir

```bash
pip install -r requirements.txt          # o: uv sync
cp .env.example .env                     # y pon tu clave dentro
jupyter lab taller-01-informe.ipynb
```

### Ejecutar solo la Parte 0

La Parte 0 está resuelta y ejecutada en `taller-01-informe.ipynb`, desde
**Setup** hasta **0.c**. Puedes abrirlo en VS Code y seleccionar el kernel
Python de `.venv`. No necesita clave de API ni Ollama.

Para repetir solo esta parte desde PowerShell, con las dependencias de
`requirements.txt` instaladas:

```powershell
.venv/Scripts/python.exe scripts/ejecutar_parte0.py
```

El ejecutor guarda las salidas y gráficas dentro del notebook y se detiene
antes de la Parte 1. Cada ejecución añade **9 generaciones** al CSV, sin
borrar corridas anteriores. GPT-2 usa la caché disponible; si falta, su
primera carga descarga aproximadamente 550 MB. Se fija la revisión del
modelo y se registran las versiones y las semillas.

Archivos de evidencia:

- `datos/resultados.csv`: nueve generaciones locales, costo cero; `acierto`
  vacío porque aquí no se puntúa exactitud.
- `datos/parte0_generaciones.jsonl`: prompts, IDs, configuración, semillas,
  fecha y revisión de cada generación.
- `datos/parte0_logits.csv`: los 50 257 logits de cada uno de los dos
  prefijos; permite reconstruir las distribuciones completas.
- `datos/parte0_distribuciones.csv`: entropía, núcleo del 90 % y probabilidad
  máxima para cada prefijo y temperatura.
- `figuras/parte0a_temperatura.png` y `figuras/parte0b_cortes.png`: figuras
  que también están incrustadas en el notebook.

La lógica está en `src/parte0.py`. La instrucción de 0.c se comparte con
la plantilla zero-shot de las siguientes partes mediante `src/prompts.py`.
La latencia registrada mide únicamente `generate()`, excluyendo la carga
del modelo y la tokenización. El aviso de parámetros ignorados al usar
greedy forma parte de la evidencia de 0.b.

Para Qwen/Ollama en las partes posteriores:

```bash
ollama serve
ollama pull qwen3:1.7b
```

## Modelos (tabla semestral del curso)

| Fila | Modelo | USD/M entrada | USD/M salida | Verificado |
|---|---|---|---|---|
| `base_local` | `openai-community/gpt2` | 0 | 0 | — |
| `propietario_economico` | `gpt-4o-mini` | 0,15 | 0,60 | 2026-08-26 |
| `openai_razonamiento` | `gpt-5.6-luna` | 0,20 | 1,20 | 2026-09-18 |
| `open_weight_pequeno` | `qwen3:1.7b` | 0 | 0 | — |

Cada precio trae la fecha de **su propia fila**, no una fecha única para toda
la tabla.

## Credenciales

Las claves se leen de un `.env` que `.gitignore` excluye. **Ninguna clave
aparece en el código, el notebook, el CSV ni el repositorio** — es un hallazgo
bloqueante según la política del curso, no una advertencia.
