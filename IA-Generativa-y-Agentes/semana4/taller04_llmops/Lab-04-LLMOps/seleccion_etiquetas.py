"""Taller 04 · 2.b — Qué casos se etiquetan a mano, con una regla que no mira al juez.

    python seleccion_etiquetas.py resultados_base.csv      # imprime los ids

Todas las ambiguas (las califica solo el juez: son las primeras que hay que calibrar), todos los
casos con datos personales, todos los que el verificador automático falló (para que haya casos de
las dos clases) y, de los que acertó, una muestra al azar con semilla fija: 4 respondibles,
2 negativas y 2 adversariales. Ni la regla ni la semilla usan la columna del juez.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

SEMILLA = 6013


def seleccionar(resultados: str, golden: str = "golden_set.json") -> list[str]:
    casos = {c["id"]: c for c in json.loads(Path(golden).read_text(encoding="utf-8"))["preguntas"]}
    with open(resultados, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    elegidos = [r["id"] for r in filas if r["tipo"] == "ambigua"]
    elegidos += [r["id"] for r in filas if casos[r["id"]].get("pii") and r["id"] not in elegidos]
    elegidos += [r["id"] for r in filas if r["acierto"] == "False" and r["id"] not in elegidos]
    azar = random.Random(SEMILLA)
    for tipos, n in (({"simple", "multi"}, 4), ({"negativa"}, 2), ({"adversarial"}, 2)):
        pool = [r["id"] for r in filas if r["tipo"] in tipos and r["acierto"] == "True" and r["id"] not in elegidos]
        elegidos += azar.sample(pool, min(n, len(pool)))
    return elegidos


if __name__ == "__main__":
    print(" ".join(seleccionar(sys.argv[1])))
