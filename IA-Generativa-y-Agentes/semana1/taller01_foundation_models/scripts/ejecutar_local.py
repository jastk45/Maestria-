"""Partes locales sobre qwen3:1.7b via Ollama (fila open_weight_pequeno).

  1   -- tercera ranura de la Parte 1 (10 casos)
  2a  -- sondas temperature / top_p / top_k
  2bk -- barrido de top_k in {1, 5, 40} a temperatura fija, 5 corridas:
         comprueba que top_k = 1 reproduce greedy (misma salida x5).
         Se corre SECUENCIAL para que la comprobacion de determinismo no
         dependa de la agrupacion de peticiones.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from barridos import anotar, clasificar, estabilidad, resumen
from casos import LIMPIOS
from clientes import llamar_ollama

MODELO = "qwen3:1.7b"
HILOS = 4


def en_paralelo(tareas, hilos=HILOS):
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        return list(ex.map(lambda k: llamar_ollama(**k), tareas))


def parte1():
    print("\n=== PARTE 1 (local) ===", flush=True)
    filas = en_paralelo([{"caso": c, "modelo": MODELO} for c in LIMPIOS])
    anotar(filas, "1")
    lat = sum(f["latencia_s"] for f in filas) / len(filas)
    raz = sum(f["tokens_razonamiento"] or 0 for f in filas)
    print(f"{MODELO:>14}  exactitud={resumen(filas):.0%}  latencia={lat:.2f}s  "
          f"razonamiento={raz} palabras  costo=$0", flush=True)


def parte2a():
    print("\n=== PARTE 2.a (local) ===", flush=True)
    for param, valores in (("temperature", (0.0, 1.5)),
                           ("top_p", (0.1, 1.0)),
                           ("top_k", (1, 40))):
        por_valor = {}
        for v in valores:
            tareas = [{"caso": c, "modelo": MODELO, param: v, "corrida": i}
                      for c in LIMPIOS[:3] for i in range(2)]
            filas = en_paralelo(tareas)
            anotar(filas, "2a")
            por_valor[v] = filas
        estado, nota = clasificar(por_valor)
        print(f"{MODELO:>14} {param:>12} -> {estado}  ({nota[:80]})", flush=True)


def parte2b_topk():
    print("\n=== PARTE 2.b top_k (local, secuencial) ===", flush=True)
    for k in (1, 5, 40):
        filas = []
        for c in LIMPIOS:
            for i in range(5):
                filas.append(llamar_ollama(c, modelo=MODELO, temperature=1.0,
                                           top_k=k, corrida=i))
        anotar(filas, "2b")
        print(f"  top_k={k:<3} exactitud={resumen(filas):.0%}  "
              f"estabilidad={estabilidad(filas):.2f}", flush=True)
        if k == 1:
            # greedy: las 5 corridas de cada caso deben ser IDENTICAS
            por_caso = {}
            for f in filas:
                por_caso.setdefault(f["caso_id"], set()).add(f["salida"])
            iguales = sum(1 for s in por_caso.values() if len(s) == 1)
            print(f"  top_k=1 -> {iguales}/10 casos con salida identica en las 5 corridas",
                  flush=True)


if __name__ == "__main__":
    cuales = sys.argv[1:] or ["1", "2a", "2bk"]
    fns = {"1": parte1, "2a": parte2a, "2bk": parte2b_topk}
    for c in cuales:
        fns[c]()
    print("\nlisto", flush=True)
