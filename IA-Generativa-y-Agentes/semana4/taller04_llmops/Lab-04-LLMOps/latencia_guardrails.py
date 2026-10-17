"""Taller 04 · Parte 3 — Cuánto cuesta cada guardrail en tiempo.

    python latencia_guardrails.py      # → entregables/latencia_guardrails.json

Langfuse guarda los tiempos con resolución de milisegundo, y un guardrail de expresiones regulares
tarda microsegundos: en los spans aparece como 0 o 1 ms. Aquí se mide cada uno sobre los textos
reales (las 81 preguntas del golden set y los 34 casos del banco), 200 pasadas, con
time.perf_counter_ns, y se reporta la mediana y el p95 por llamada en microsegundos.
"""
from __future__ import annotations

import json
import platform
import statistics
import time
from pathlib import Path

import guardrails as EJ
import mis_guardrails as G

AQUI = Path(__file__).resolve().parent
PASADAS = 200


def medir(funcion, textos: list[str]) -> dict:
    tiempos = []
    for _ in range(PASADAS):
        for t in textos:
            t0 = time.perf_counter_ns()
            funcion(t)
            tiempos.append((time.perf_counter_ns() - t0) / 1000)
    tiempos.sort()
    return {"mediana_us": round(statistics.median(tiempos), 2),
            "p95_us": round(tiempos[int(0.95 * (len(tiempos) - 1))], 2),
            "llamadas": len(tiempos)}


def main() -> None:
    golden = [c["pregunta"] for c in json.loads((AQUI / "golden_set.json").read_text(encoding="utf-8"))["preguntas"]]
    banco = json.loads((AQUI / "ataques.json").read_text(encoding="utf-8"))["casos"]
    entrada = golden + [c["texto"] for c in banco if c["canal"] == "entrada"]
    salida = [c["texto"] for c in banco if c["canal"] == "salida"]
    r = {"python": platform.python_version(), "pasadas": PASADAS,
         "textos_entrada": len(entrada), "textos_salida": len(salida), "mios": {}, "ejemplo": {}}
    for nombre, f in G.ENTRADA:
        r["mios"][nombre] = medir(f, entrada)
    for nombre, f in G.SALIDA:
        r["mios"][nombre] = medir(f, salida)
    r["mios"]["validar_entrada (cadena)"] = medir(G.validar_entrada, entrada)
    r["mios"]["validar_salida (cadena)"] = medir(G.validar_salida, salida)
    r["mios"]["enmascarar (máscara de la traza)"] = medir(lambda t: G.enmascarar(data={"x": (t,)}), entrada)
    r["ejemplo"]["validate_input"] = medir(EJ.validate_input, entrada)
    r["ejemplo"]["validate_output"] = medir(EJ.validate_output, salida)
    destino = AQUI / "entregables" / "latencia_guardrails.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
