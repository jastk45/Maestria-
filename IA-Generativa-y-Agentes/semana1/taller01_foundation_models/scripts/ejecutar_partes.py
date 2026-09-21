"""Corre las Partes 1, 2.a, 2.b (reducida), 3, 4.a y 4.b.

Las llamadas van en paralelo con hilos: son peticiones de red, no computo.
El barrido de 2.b se corre reducido -- 3 corridas por celda en vez de 5 --
y esa desviacion del enunciado se declara en el informe.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import barridos
from barridos import anotar, clasificar, estabilidad, resumen
from casos import CONTAMINADOS, LIMPIOS
from clientes import llamar

ECONOMICO = "gpt-4o-mini"
RAZONADOR = "gpt-5.6-luna"
HILOS = 12


def en_paralelo(tareas):
    """tareas: lista de dicts de kwargs para llamar()."""
    with ThreadPoolExecutor(max_workers=HILOS) as ex:
        return list(ex.map(lambda k: llamar(**k), tareas))


def parte1():
    print("\n=== PARTE 1 ===")
    for modelo in (ECONOMICO, RAZONADOR):
        filas = en_paralelo([{"caso": c, "modelo": modelo} for c in LIMPIOS])
        anotar(filas, "1")
        lat = sum(f["latencia_s"] for f in filas) / len(filas)
        cost = sum(f["costo_usd"] or 0 for f in filas)
        err = sum(1 for f in filas if f["error_codigo"])
        print(f"{modelo:>14}  exactitud={resumen(filas):.0%}  "
              f"latencia={lat:.2f}s  costo=${cost:.5f}  errores={err}")


def parte2a():
    print("\n=== PARTE 2.a ===")
    matriz = {}
    for modelo in (ECONOMICO, RAZONADOR):
        for param, valores in (("temperature", (0.0, 1.5)),
                               ("top_p", (0.1, 1.0)),
                               ("top_k", (1, 40))):
            por_valor = {}
            for v in valores:
                tareas = [{"caso": c, "modelo": modelo, param: v, "corrida": i}
                          for c in LIMPIOS[:3] for i in range(2)]
                filas = en_paralelo(tareas)
                anotar(filas, "2a")
                por_valor[v] = filas
            estado, nota = clasificar(por_valor)
            matriz[(modelo, param)] = (estado, nota)
            print(f"{modelo:>14} {param:>12} -> {estado}")
            if estado == "rechazado":
                print(f"                            {nota[:150]}")
    return matriz


def parte2b(corridas=range(5)):
    """Rejilla completa: 15 celdas x 5 corridas x 10 casos = 750 llamadas.
    'corridas' permite completar solo las que falten (p. ej. range(3, 5))."""
    print(f"\n=== PARTE 2.b (corridas {list(corridas)}) ===")
    for T in (0.0, 0.3, 0.7, 1.0, 1.5):
        for tp in (0.5, 0.9, 1.0):
            tareas = [{"caso": c, "modelo": ECONOMICO, "temperature": T,
                       "top_p": tp, "corrida": i}
                      for c in LIMPIOS for i in corridas]
            filas = en_paralelo(tareas)
            anotar(filas, "2b")
            print(f"  T={T:<4} top_p={tp:<4} exactitud={resumen(filas):.0%} "
                  f"estabilidad={estabilidad(filas):.2f}")


def parte3():
    print("\n=== PARTE 3 ===")
    for p in ("zero_shot", "few_shot", "cot", "structured"):
        filas = en_paralelo([{"caso": c, "modelo": ECONOMICO, "plantilla": p}
                             for c in LIMPIOS])
        anotar(filas, "3")
        tin = sum(f["tokens_entrada"] or 0 for f in filas)
        tout = sum(f["tokens_salida"] or 0 for f in filas)
        print(f"  {p:>11}  exactitud={resumen(filas):.0%}  "
              f"tokens_in={tin:<6} tokens_out={tout:<6} "
              f"costo=${sum(f['costo_usd'] or 0 for f in filas):.5f}")


def parte4a():
    print("\n=== PARTE 4.a ===")
    for nivel in ("low", "medium", "high"):
        filas = en_paralelo([{"caso": c, "modelo": RAZONADOR, "esfuerzo": nivel}
                             for c in LIMPIOS])
        anotar(filas, "4a")
        raz = sum(f["tokens_razonamiento"] or 0 for f in filas)
        vis = sum((f["tokens_salida"] or 0) - (f["tokens_razonamiento"] or 0)
                  for f in filas)
        print(f"  {nivel:>7}  exactitud={resumen(filas):.0%}  "
              f"razonamiento={raz:<6} visibles={vis:<5} "
              f"costo=${sum(f['costo_usd'] or 0 for f in filas):.5f}  "
              f"lat={sum(f['latencia_s'] for f in filas)/len(filas):.1f}s")


def parte4b():
    print("\n=== PARTE 4.b (contaminados) ===")
    for nivel in ("low", "high"):
        filas = en_paralelo([{"caso": c, "modelo": RAZONADOR, "esfuerzo": nivel}
                             for c in CONTAMINADOS])
        anotar(filas, "4b")
        det = " ".join(f"{f['caso_id']}={'OK' if f['acierto'] else 'X'}"
                       for f in filas)
        raz = sum(f["tokens_razonamiento"] or 0 for f in filas)
        print(f"  {nivel:>5}  exactitud={resumen(filas):.0%}  {det}  razonamiento={raz}")


if __name__ == "__main__":
    cuales = sys.argv[1:] or ["1", "2a", "3", "4a", "4b", "2b"]
    fns = {"1": parte1, "2a": parte2a, "2b": parte2b,
           "2b-completar": lambda: parte2b(range(3, 5)),   # corridas 3 y 4 que faltaban
           "3": parte3, "4a": parte4a, "4b": parte4b}
    for c in cuales:
        fns[c]()
    print("\nlisto")
