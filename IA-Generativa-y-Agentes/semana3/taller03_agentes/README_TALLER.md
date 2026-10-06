# Taller 03 — cómo reproducirlo

```bash
uv sync                          # versiones fijadas (pyproject.toml + uv.lock; también requirements.txt)
cp .env.example .env             # OPENAI_BASE_URL=http://172.28.230.10:12555/v1 · OPENAI_API_KEY=local
uv run python crear_base.py      # data/database.sqlite (semilla 6013)
```

`MiAgente` lee el id del modelo de `/v1/models` si `AGENT_MODEL` está vacío. `AnalystAgent`
(andamiaje) lo exige: se pasa en la línea de comandos. El 2026-10-03 la H200 servía `zai-org/GLM-5.3-Flash`.

| parte | comando (bash) | salida |
|---|---|---|
| 0.a | `AGENT_MODEL=zai-org/GLM-5.3-Flash uv run python evaluar.py --solo P1 P3 --salida entregables/parte0/parte0.csv` | `traces/` → `entregables/parte0/` |
| 0.b · 0.c | `uv run python guion.py ataque` · `uv run python guion.py limite` | `entregables/parte0/` |
| 1 | `AGENT_TRACE_DIR=trazas/parte1 uv run python mi_agente.py "pregunta"` | `trazas/parte1/` |
| 2.b | `AGENT_TRACE_DIR=trazas/mi_agente uv run python evaluar.py --golden golden_set.json --agente mi_agente:MiAgente --salida resultados/resultados_mi_agente.csv` | `resultados/`, `trazas/mi_agente/` |
| 2.b | `AGENT_TRACE_DIR=trazas/andamiaje AGENT_MODEL=zai-org/GLM-5.3-Flash uv run python evaluar.py --golden golden_set.json --agente agent:AnalystAgent --salida resultados/resultados_andamiaje.csv` | `resultados/`, `trazas/andamiaje/` |
| 3 | `uv run python frenos.py` | `trazas/frenos/` |
| 4 | `AGENT_TRACE_DIR=trazas/mcp_prueba uv run python parte4_mcp.py` | `entregables/parte4_mcp_prueba.txt` |
| 4 | `AGENT_TRACE_DIR=trazas/mcp uv run python evaluar.py --golden golden_set.json --agente servidor_mcp:MiAgenteMCP --salida resultados/resultados_mcp.csv` | `resultados/`, `trazas/mcp/` |
| tablas | `uv run python tablas.py` | `entregables/tablas.md` |
| informe | `uv run python informe/construir_pdf.py` | `informe/informe.pdf` |

Historial: `resultados/{v1,v2_13,v2_18,v3_21,v4_28,caida_vpn,sondeo}/` (v2_18 solo CSV: sus trazas no se conservaron) y `trazas/{v1,v2_13,v3_21,v4_28,caida_vpn}_*`, `trazas/sondeo/` (ver 2.b del informe). Los PNG que faltaban se regeneran con `uv run python regenerar_graficos.py` (lista en `entregables/graficos_regenerados.txt`).

Archivos del grupo: `mi_agente.py`, `herramientas.py`, `golden_set.json`, `frenos.py`, `servidor_mcp.py`,
`herramienta_nueva.py`, `parte4_mcp.py`, `tablas.py`, `informe/`. El andamiaje (`agent.py`, `tools.py`,
`evaluar.py`, `guion.py`, `crear_base.py`) no se modificó; de `.gitignore` solo se cambió `resultados*.csv`
por `/resultados.csv` para que los CSV de `resultados/` se versionen.
