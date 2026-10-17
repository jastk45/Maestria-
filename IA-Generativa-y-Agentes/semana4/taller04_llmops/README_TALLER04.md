# Taller 04 — Evaluar, observar y proteger el agente (opción A) · Jaime Astudillo

El sistema del Taller 3 —`MiAgente`, el agente analista SQL (`Lab-03-Agentes/mi_agente.py`,
`herramientas.py`)— instrumentado con Langfuse, evaluado con un golden set de 81 casos y un juez
calibrado, y protegido con cuatro guardrails. Informe: `Lab-04-LLMOps/informe/informe.pdf`.

## Qué es de quién

| archivo | qué es |
|---|---|
| `Lab-03-Agentes/mi_agente.py`, `herramientas.py` | el agente del Taller 3; en el Taller 4 solo cambian tres cosas: el prompt es un atributo (`self.sistema`), la llamada al modelo acepta argumentos extra (`self.kw_llm`) y la traza local se escribe en un método (`_guardar_traza`) |
| `Lab-04-LLMOps/agente_llmops.py` | `AgenteLLMOps`: spans `corrida`, `guardrail`, `llm` y `herramienta` en Langfuse, las tres correcciones de la 0.c, `traza_id`, `prompt_version` y `guardrail` en el resultado |
| `Lab-04-LLMOps/mis_guardrails.py` | G1 inyección · G2 datos personales (entrada, salida y traza: la máscara) · G3 claves en la salida · G4 longitud |
| `Lab-04-LLMOps/prompts_agente.py` | las versiones del prompt (v1 = Taller 3; v2 = la mejora de la 2.c), su changelog y su registro en Langfuse |
| `Lab-04-LLMOps/golden_set.json`, `ataques.json`, `etiquetas.csv` | golden set (81), banco de guardrails (34) y etiquetas a mano |
| `Lab-04-LLMOps/resultados_{base,v2}.csv`, `spans_{base,v2}.jsonl`, `guardrails_{mios,ejemplo}.csv` | archivos crudos: las tablas del informe salen de aquí (`tablas.py`) |
| `Lab-04-LLMOps/{ver_traza,buscar_pii,verificar_correcciones,calibracion,latencia_guardrails,hoja_etiquetas,tablas}.py` | evidencia: spans de un caso, búsqueda de datos personales, las tres correcciones, calibración, latencia de guardrails, hoja de etiquetado, tablas |
| `fuentes/modelos/modelos-2026-1.json` | la tabla de precios del Anexo del enunciado, transcrita (sin ella `--precio` no corre) |
| el resto | el laboratorio tal como se repartió (sin cambios: `evaluar_llmops.py`, `exportar_trazas.py`, `resumir_trazas.py`, `probar_guardrails.py`, `guion.py`, y el andamiaje de la Parte 0) |

## Reproducir (bash, desde la carpeta del taller)

```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/Scripts/python.exe -r Lab-04-LLMOps/requirements.txt
(cd Lab-03-Agentes && ../.venv/Scripts/python crear_base.py)          # data/database.sqlite, semilla 6013
(cd langfuse && ./levantar_langfuse.sh)                                 # Docker · Langfuse 4.50.0 · http://localhost:3000
cp Lab-04-LLMOps/.env.example Lab-04-LLMOps/.env                        # + LANGFUSE_* de langfuse/.env (VPN: H200)
cd Lab-04-LLMOps
```

| parte | orden | salida |
|---|---|---|
| 0 | `python guion.py ceros` · `guardrails` · `traza` | `parte0/salida_*.txt` |
| 1 | `python verificar_correcciones.py` | `parte1/verificacion_correcciones.txt` |
| 2.c | `python prompts_agente.py registrar v1` (y `v2`) | versiones en Langfuse |
| 2.b | `SESION_LANGFUSE=jaime-astudillo-t4-base PROMPT_LABEL=production python evaluar_llmops.py --golden golden_set.json --agente agente_llmops:AgenteLLMOps --juez gemma3 --salida resultados_base.csv` | `resultados_base.csv` |
| 2.c | `SESION_LANGFUSE=jaime-astudillo-t4-v2 PROMPT_VERSION=2 python evaluar_llmops.py … --salida resultados_v2.csv` | `resultados_v2.csv` |
| 1 | `python exportar_trazas.py --sesion jaime-astudillo-t4-base -o spans_base.jsonl` (y `-v2`) · `python resumir_trazas.py spans_base.jsonl --precio propietario_economico` | `spans_*.jsonl` |
| 2.b | `python calibracion.py etiquetas-verificador resultados_base.csv` · `python evaluar_llmops.py --calibrar resultados_base.csv --etiquetas etiquetas_verificador.csv` · `… --etiquetas etiquetas.csv` | acuerdo y kappa |
| 2.c | `python ver_traza.py --resultados resultados_base.csv --ids <ids> -o casos/base` | `casos/` |
| 3 | `python probar_guardrails.py --entrada mis_guardrails:validar_entrada --salida mis_guardrails:validar_salida --casos ataques.json --csv guardrails_mios.csv` · `python probar_guardrails.py --casos ataques.json --csv guardrails_ejemplo.csv` · `python latencia_guardrails.py` | `guardrails_*.csv` |
| repo | `python buscar_pii.py --sesion jaime-astudillo-t4-base jaime-astudillo-t4-v2 --archivos spans_base.jsonl spans_v2.jsonl` | sin datos personales ni claves |
| informe | `python tablas.py` · `python informe/construir_pdf.py` | `entregables/tablas.md`, `informe/informe.pdf` |

Modelos leídos de los endpoints el 2026-10-16: agente `zai-org/GLM-5.3-Flash` (vLLM de la H200),
juez `gemma3:27b` (Ollama de la H200, otra familia). Credenciales: solo en `.env` (fuera de git).
