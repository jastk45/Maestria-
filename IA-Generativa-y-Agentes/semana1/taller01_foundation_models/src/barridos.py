"""Los bucles de las Partes 1-4 y la escritura del CSV crudo.

Toda llamada se anota como una fila, incluidas las locales de la Parte 0 con
costo cero: una corrida gratis tambien es una corrida.
"""

import csv
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CSV = RAIZ / "datos" / "resultados.csv"

COLUMNAS = [
    "caso_id", "tipo", "modelo", "plantilla",
    "temperature", "top_p", "top_k", "esfuerzo", "corrida",
    "tokens_entrada", "tokens_salida", "tokens_razonamiento",
    "latencia_s", "costo_usd",
    "salida", "respuesta_extraida", "esperada", "acierto",
    "error_codigo", "error_mensaje",
    "parte",
]


def anotar(filas, parte):
    """Agrega filas al CSV crudo. Se llama despues de cada celda, no al final:
    si un barrido se cae en la llamada 600 no se pierden las 599 anteriores."""
    existe = RUTA_CSV.exists()
    RUTA_CSV.parent.mkdir(exist_ok=True)
    with open(RUTA_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        if not existe:
            w.writeheader()
        for fila in filas:
            w.writerow({**fila, "parte": parte})
    return len(filas)


# --------------------------------------------------------------- Parte 1
def barrido_comparacion(modelos, casos):
    """El mismo prompt en varios modelos. modelos: [(id, funcion_llamar)]"""
    filas = []
    for modelo, fn in modelos:
        for caso in casos:
            filas.append(fn(caso, modelo=modelo))
        anotar(filas[-len(casos):], "1")
    return filas


# ------------------------------------------------------------- Parte 2.a
def sonda_parametro(modelo, fn, parametro, valores, casos, n_corridas=3):
    """Manda UN parametro con dos valores extremos y devuelve las filas crudas.
    Si la llamada falla, la fila se guarda igual: esa fila ES el resultado
    'rechazado'."""
    por_valor = {}
    for v in valores:
        filas = []
        for caso in casos:
            for c in range(n_corridas):
                filas.append(fn(caso, modelo=modelo, corrida=c, **{parametro: v}))
        anotar(filas, "2a")
        por_valor[v] = filas
    return por_valor


def clasificar(por_valor):
    """Los tres estados de la matriz 2.a."""
    todas = [f for fs in por_valor.values() for f in fs]
    errores = [f for f in todas if f["error_codigo"] is not None]
    if errores:
        return "rechazado", f"{errores[0]['error_codigo']}: {errores[0]['error_mensaje']}"

    # comparar DISTRIBUCIONES de salida, no una muestra contra otra
    firmas = {}
    for v, filas in por_valor.items():
        firmas[v] = Counter((f["caso_id"], f["salida"]) for f in filas)
    valores = list(firmas)
    if len(valores) >= 2 and firmas[valores[0]] == firmas[valores[-1]]:
        return "aceptado y no actua", "salidas identicas entre valores extremos"
    return "aceptado y actua", "distribuciones distintas entre valores extremos"


# ------------------------------------------------------------- Parte 2.b
def barrido_decodificacion(modelo, fn, casos, temperaturas, top_ps, n_corridas=5):
    """La rejilla. len(T) x len(top_p) x n_corridas x len(casos) llamadas."""
    filas = []
    for T in temperaturas:
        for tp in top_ps:
            celda = []
            for caso in casos:
                for c in range(n_corridas):
                    celda.append(fn(caso, modelo=modelo, temperature=T,
                                    top_p=tp, corrida=c))
            anotar(celda, "2b")       # anota DESPUES DE CADA CELDA
            filas += celda
    return filas


def estabilidad(filas_celda):
    """De las n corridas de un mismo caso, fraccion que dio la respuesta modal.
    1.0 = las n corridas coincidieron."""
    por_caso = {}
    for f in filas_celda:
        por_caso.setdefault(f["caso_id"], []).append(f["respuesta_extraida"])
    fracciones = [Counter(rs).most_common(1)[0][1] / len(rs)
                  for rs in por_caso.values()]
    return sum(fracciones) / len(fracciones) if fracciones else None


# --------------------------------------------------------------- Parte 3
def barrido_plantillas(modelo, fn, casos,
                       plantillas=("zero_shot", "few_shot", "cot", "structured")):
    filas = []
    for p in plantillas:
        celda = [fn(caso, modelo=modelo, plantilla=p) for caso in casos]
        anotar(celda, "3")
        filas += celda
    return filas


# ------------------------------------------------------------- Parte 4.a
def barrido_esfuerzo(modelo, fn, casos, niveles=("low", "medium", "high")):
    """El dial de razonamiento. Un nivel completo por vez: si el contador de
    tokens del nivel alto se dispara, se rehace la cuenta antes de seguir."""
    filas = []
    for n in niveles:
        celda = [fn(caso, modelo=modelo, esfuerzo=n) for caso in casos]
        anotar(celda, "4a")
        filas += celda
    return filas


# ------------------------------------------------------------- Parte 4.b
def barrido_contaminados(modelo, fn, contaminados, nivel_bajo="low", nivel_alto="high"):
    filas = []
    for n in (nivel_bajo, nivel_alto):
        celda = [fn(caso, modelo=modelo, esfuerzo=n) for caso in contaminados]
        anotar(celda, "4b")
        filas += celda
    return filas


def resumen(filas):
    """Exactitud media de un conjunto de filas."""
    return sum(f["acierto"] for f in filas) / len(filas) if filas else None
