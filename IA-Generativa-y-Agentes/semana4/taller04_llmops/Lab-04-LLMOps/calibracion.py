"""Taller 04 · 2.b — Las dos calibraciones del juez, con la herramienta del laboratorio.

    python calibracion.py etiquetas-verificador resultados_base.csv     # → etiquetas_verificador.csv
    python evaluar_llmops.py --calibrar resultados_base.csv --etiquetas etiquetas_verificador.csv
    python evaluar_llmops.py --calibrar resultados_base.csv --etiquetas etiquetas.csv
    python calibracion.py desacuerdos resultados_base.csv               # la tabla para revisarlos

1. Contra el verificador automático: sus aciertos (True → aprueba, False → falla) en respondibles,
   negativas y adversariales se escriben como etiquetas y se comparan con el MISMO `--calibrar`
   que usa la persona (acuerdo, kappa de Cohen, discrepancias y sin_parsear).
2. Contra la persona: etiquetas.csv, escrito antes de mirar al juez.

`desacuerdos` lista, por caso: tipo, verificador, juez, persona (si la hay) y el motivo del juez,
para decidir en cada desacuerdo quién se equivocó.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

NO_AMBIGUAS = {"simple", "multi", "negativa", "adversarial"}


def leer(ruta: str) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def etiquetas_verificador(resultados: str, salida: str = "etiquetas_verificador.csv") -> None:
    filas = [r for r in leer(resultados) if r["tipo"] in NO_AMBIGUAS and r["acierto"] in ("True", "False")]
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "etiqueta"])
        for r in filas:
            w.writerow([r["id"], "aprueba" if r["acierto"] == "True" else "falla"])
    print(f"✓ {salida}: {len(filas)} etiquetas del verificador automático "
          f"({sum(r['acierto'] == 'True' for r in filas)} aprueba, {sum(r['acierto'] == 'False' for r in filas)} falla)")


def desacuerdos(resultados: str, humanas: str = "etiquetas.csv") -> list[dict]:
    persona = {}
    if Path(humanas).exists():
        persona = {r["id"]: r["etiqueta"].strip().lower() for r in leer(humanas)}
    salida = []
    for r in leer(resultados):
        ver = ("aprueba" if r["acierto"] == "True" else "falla") if r["acierto"] in ("True", "False") else ""
        juez = r["juez_veredicto"]
        hum = persona.get(r["id"], "")
        choca_ver = ver and juez in ("aprueba", "falla") and ver != juez
        choca_hum = hum and juez in ("aprueba", "falla") and hum != juez
        if choca_ver or choca_hum or juez == "sin_parsear":
            salida.append({"id": r["id"], "tipo": r["tipo"], "verificador": ver or "—", "juez": juez,
                           "persona": hum or "—", "motivo_juez": r["juez_motivo"],
                           "respuesta": r["respuesta"][:240].replace("\n", " ")})
    return salida


if __name__ == "__main__":
    orden, ruta = sys.argv[1], sys.argv[2]
    if orden == "etiquetas-verificador":
        etiquetas_verificador(ruta)
    elif orden == "desacuerdos":
        for d in desacuerdos(ruta, *(sys.argv[3:4] or [])):
            print(json.dumps(d, ensure_ascii=False))
