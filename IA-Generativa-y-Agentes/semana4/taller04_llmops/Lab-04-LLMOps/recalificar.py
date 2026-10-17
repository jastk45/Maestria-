"""Taller 04 · 2.b — Aplica una corrección del golden set a corridas ya hechas, sin volver a correrlas.

    python recalificar.py --golden golden_set.json --ids CL1 \
        --entrada resultados_base.csv resultados_v2.csv --sufijo _gs11

La revisión de desacuerdos (2.b) encontró un error del golden set en CL1: pedía abstención, pero lo
que importa en ese caso —que la clave no llegue al usuario— ya lo mide `pii`. La versión v1.1 del
golden set lo corrige (CL1 pasa a respondible `simple` con su `sql_verificacion` y su `pii`).

Volver a correr el agente cambiaría las respuestas (el modelo muestrea), así que se recalifican las
respuestas YA GUARDADAS en cada CSV con las mismas piezas de evaluar_llmops.py: el verificador del
Taller 3 (cifra contra la consulta y abstención) y el mismo juez (gemma3, prompt j1, temperature=0)
con el criterio del nuevo tipo y la referencia de la consulta. Solo cambian las filas de --ids; los
CSV originales no se tocan: se escribe uno nuevo con el sufijo.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
load_dotenv(AQUI / ".env")

import evaluar_llmops as E  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--golden", default="golden_set.json")
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--entrada", nargs="+", required=True)
    ap.add_argument("--sufijo", default="_gs11")
    ap.add_argument("--sin-juez", action="store_true", help="para corridas que se hicieron sin juez")
    ap.add_argument("--db", default=os.getenv("AGENT_DB_PATH", str(E.LAB03 / "data/database.sqlite")))
    a = ap.parse_args()
    casos = {c["id"]: c for c in json.loads(Path(a.golden).read_text(encoding="utf-8"))["preguntas"]}
    juez = None if a.sin_juez else E.Juez(os.getenv("JUEZ_MODEL", "gemma3"), os.getenv("JUEZ_BASE_URL"),
                                          os.getenv("JUEZ_API_KEY"))
    for ruta in a.entrada:
        with open(ruta, encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        for fila in filas:
            if fila["id"] not in a.ids:
                continue
            caso = casos[fila["id"]]
            objetivo = E.T3.esperado(Path(a.db), caso)
            antes = (fila["tipo"], fila["acierto"], fila["juez_veredicto"])
            fila["tipo"] = caso["tipo"]
            fila["esperado"] = "" if objetivo is None else objetivo
            abst = E.T3.se_abstiene(fila["respuesta"])
            fila["abstencion"] = abst
            if caso["tipo"] in E.RESPONDIBLES:
                fila["acierto"] = (not abst and objetivo is not None
                                   and E.T3.contiene_numero(fila["respuesta"], objetivo)
                                   and E.T3.contiene_textos(fila["respuesta"], caso.get("debe_contener", [])))
            elif caso["tipo"] in E.NO_RESPONDIBLES:
                fila["acierto"] = abst and E._es_verdad(fila["base_intacta"])
            if juez:
                criterio = caso.get("criterio_juez") or E.CRITERIO_POR_TIPO.get(caso["tipo"], "")
                fila.update(juez.evaluar(caso["pregunta"], fila["respuesta"], criterio, E._referencia(caso, objetivo)),
                            juez_modelo=juez.modelo, juez_version=E.JUEZ_VERSION + "·recalificado")
            print(f"{ruta} · {fila['id']}: {antes} → ({fila['tipo']}, {fila['acierto']}, {fila['juez_veredicto']}) "
                  f"· {fila['juez_motivo'][:120]}")
        salida = Path(ruta).with_name(Path(ruta).stem + a.sufijo + ".csv")
        with open(salida, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=E.COLUMNAS)
            w.writeheader()
            w.writerows(filas)
        print(f"✓ {salida}")


if __name__ == "__main__":
    main()
