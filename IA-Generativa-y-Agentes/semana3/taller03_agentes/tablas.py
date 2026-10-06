"""Taller 03 — Las tablas del informe, derivadas de resultados/*.csv (y, para la métrica
estricta de abstención, del campo `abstencion_por_codigo` de las trazas).

    python tablas.py        # escribe entregables/tablas.md
"""
import csv
import json
from pathlib import Path

from evaluar import ABSTENCION, resumen

AGENTES = {"andamiaje (agent:AnalystAgent)": "resultados/resultados_andamiaje.csv",
           "MiAgente (Parte 1)": "resultados/resultados_mi_agente.csv",
           "MiAgenteMCP (Parte 4.B)": "resultados/resultados_mcp.csv"}


def leer(ruta):
    filas = list(csv.DictReader(open(ruta, encoding="utf-8")))
    for f in filas:   # el CSV guarda texto: se restauran los tipos que usa evaluar.resumen
        for k in ("pasos", "errores_herramienta", "tokens_entrada", "tokens_salida", "llamadas_herramienta"):
            f[k] = int(f[k]) if f[k].isdigit() else f[k]
        for k in ("acierto", "abstencion", "base_intacta"):
            f[k] = f[k] == "True"
    return filas


TRAZAS = {"MiAgente (Parte 1)": "trazas/mi_agente", "MiAgenteMCP (Parte 4.B)": "trazas/mcp"}

datos = {n: leer(r) for n, r in AGENTES.items()}
res = {n: resumen(f) for n, f in datos.items()}
# Más estricta que evaluar.py: si la frase la antepuso el CÓDIGO, no es una abstención del modelo.
# Fuente principal: el campo `abstencion_por_codigo` que MiAgente escribe en cada traza (registro
# directo). Verificación cruzada: el prefijo que deja el código en la respuesta del CSV.
FORZADA = ABSTENCION + " La base es de solo lectura."
for n, filas in datos.items():
    neg = [f for f in filas if f["tipo"] in ("negativa", "adversarial")]
    if n in TRAZAS:
        pregunta_a_id = {p["pregunta"]: p["id"] for p in json.loads(
            Path("golden_set.json").read_text(encoding="utf-8"))["preguntas"]}
        por_codigo = {pregunta_a_id[t["question"]] for t in map(
            lambda f: json.loads(f.read_text(encoding="utf-8")), Path(TRAZAS[n]).glob("*.json"))
            if t.get("abstencion_por_codigo")}
        assert por_codigo == {f["id"] for f in neg if f["respuesta"].startswith(FORZADA)}, "traza y CSV discrepan"
    else:
        por_codigo = set()
    propias = sum(f["abstencion"] and f["id"] not in por_codigo for f in neg)
    res[n]["abstencion_del_modelo_sin_ayuda_del_codigo"] = round(propias / len(neg), 3) if neg else None
    res[n]["abstenciones_forzadas_por_codigo"] = ", ".join(sorted(por_codigo)) or "ninguna"
claves = list(next(iter(res.values())))
out = ["## Métricas (2.b)", "", "| métrica | " + " | ".join(res) + " |", "|---" * (len(res) + 1) + "|"]
out += [f"| {k} | " + " | ".join(str(r[k]) for r in res.values()) + " |" for k in claves]
out += ["", "## Por pregunta: acierto · pasos · tokens de entrada", "",
        "| id | tipo | " + " | ".join(datos) + " |", "|---" * (len(datos) + 2) + "|"]
for i, f0 in enumerate(next(iter(datos.values()))):
    celdas = [f"{'✓' if d[i]['acierto'] else '✗'} · {d[i]['pasos']} · {d[i]['tokens_entrada'] or '—'}"
              for d in datos.values()]
    out.append(f"| {f0['id']} | {f0['tipo']} | " + " | ".join(celdas) + " |")
Path("entregables").mkdir(exist_ok=True)
Path("entregables/tablas.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
