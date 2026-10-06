"""Taller 03 · Parte 3 — Los tres frenos de MiAgente, forzados con un modelo de guion.

    python frenos.py        # sin red ni modelo: escribe trazas en trazas/frenos/

El guion sustituye SOLO `_llamar_modelo`; el bucle, las herramientas y los frenos son los de
mi_agente.py. El freno es código nuestro, no del modelo: por eso se prueba sin modelo.
"""
from __future__ import annotations

import itertools
import json
import os

os.environ["AGENT_TRACE_DIR"] = "trazas/frenos"
os.environ.setdefault("AGENT_MODEL", "guion")

from mi_agente import MiAgente  # noqa: E402


class AgenteDeGuion(MiAgente):
    def __init__(self, guion, tokens_por_llamada=900, **ajustes):
        super().__init__()
        self.model = "guion"
        self._guion, self._tok = guion, tokens_por_llamada
        for k, v in ajustes.items():
            setattr(self, k, v)

    def _llamar_modelo(self, messages, con_herramientas=True):
        if not con_herramientas:
            # Respuesta vacía a propósito: obliga al agente a usar su propio respaldo (_parcial).
            return {"content": "", "tool_calls": [],
                    "tokens_entrada": self._tok, "tokens_salida": 20}
        nombre, args = next(self._guion)
        # El costo de entrada crece con el historial: así lo cobra un modelo real.
        return {"content": "", "tool_calls": [{"id": f"c{len(messages)}", "name": nombre,
                                               "arguments": json.dumps(args)}],
                "tokens_entrada": self._tok + 4 * len(json.dumps(messages)) // 10,
                "tokens_salida": 30}


def sql(q):
    return ("consultar_sql", {"consulta": q})


CASOS = {
    # 1 · consultas siempre distintas: ni repetición ni presupuesto la cortan; el tope de pasos sí
    "max_pasos": AgenteDeGuion((sql(f"SELECT COUNT(*) FROM ventas WHERE cantidad > {i}")
                                for i in itertools.count())),
    # 2 · cada observación es grande: el historial crece y el presupuesto salta antes del tope
    "presupuesto": AgenteDeGuion((sql(f"SELECT * FROM ventas WHERE venta_id > {i}")
                                  for i in itertools.count()), presupuesto=12_000),
    # 3 · la misma llamada una y otra vez
    "repeticion": AgenteDeGuion(itertools.repeat(sql("SELECT COUNT(*) FROM ventas"))),
    # 4 · lo que el detector NO ve: la misma consulta escrita de otra forma
    #     (WHERE i = i siempre es verdadero): el texto cambia, la consulta es la misma
    "parafrasis": AgenteDeGuion((sql(f"SELECT COUNT(*) FROM ventas WHERE {i} = {i}")
                                 for i in itertools.count())),
}

if __name__ == "__main__":
    for nombre, agente in CASOS.items():
        r = agente.run(f"[{nombre}] pregunta de prueba")
        frenos = [p["freno"] for p in r["trace"] if p.get("freno")]
        print(f"{nombre:12s} status={r['status']:20s} pasos={len(r['trace']):2d} "
              f"tokens_entrada={r['usage']['tokens_entrada']:6d}  freno: {frenos[-1] if frenos else '-'}")
        print(f"{'':12s} respuesta: {r['answer'][:110]}")
        print(f"{'':12s} traza: trazas/frenos/trace-{agente.id_corrida}.json")
