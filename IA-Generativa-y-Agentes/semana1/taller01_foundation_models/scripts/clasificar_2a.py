"""Matriz 2.a desde el CSV: declarado (tabla semestral) vs observado.

Observado se decide con la DISPERSION entre corridas, no con la respuesta
final: en una tarea de respuesta unica el numero puede coincidir aunque el
muestreo actue. Se compara la tupla (salida, tokens_salida) de cada corrida:
si con el valor "frio" del parametro las corridas de un caso coinciden y con
el valor "caliente" difieren, el parametro actua.
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
FECHA = "2026-09-20"

DECLARADO = {
    "gpt-4o-mini":  {"temperature": "si", "top_p": "si", "top_k": "no"},
    "gpt-5.6-luna": {"temperature": "no_en_esta_fila", "top_p": "no_en_esta_fila",
                     "top_k": "no"},
    "qwen3:1.7b":   {"temperature": "si", "top_p": "si", "top_k": "si"},
}

df = pd.read_csv(RAIZ / "datos" / "resultados.csv")
df["parte"] = df["parte"].astype(str)
p2a = df[df.parte == "2a"]


def dispersion(g):
    """Fraccion de casos cuyas corridas NO fueron identicas."""
    por_caso = g.groupby("caso_id").apply(
        lambda c: c[["salida", "tokens_salida"]].astype(str).agg("|".join, axis=1).nunique() > 1,
        include_groups=False)
    return por_caso.mean() if len(por_caso) else float("nan")


filas = []
for modelo, params in DECLARADO.items():
    for param, decl in params.items():
        g = p2a[(p2a.modelo == modelo) & (p2a[param].notna())]
        if g.empty:
            filas.append(dict(modelo=modelo, parametro=param, declarado=decl,
                              observado="sin correr", evidencia="", fecha=FECHA,
                              error_literal=""))
            continue
        err = g[g.error_codigo.notna()]
        if len(err):
            filas.append(dict(modelo=modelo, parametro=param, declarado=decl,
                              observado="rechazado",
                              evidencia=f"{len(err)}/{len(g)} llamadas con error",
                              fecha=FECHA,
                              error_literal=f"{err.error_codigo.iloc[0]}: {err.error_mensaje.iloc[0]}"))
            continue
        valores = sorted(g[param].unique())
        disp = {v: dispersion(g[g[param] == v]) for v in valores}
        frio, caliente = valores[0], valores[-1]
        ev = "; ".join(f"{param}={v:g}: {d:.0%} de casos con corridas distintas"
                       for v, d in disp.items())
        # actua si el valor caliente dispersa mas que el frio, o si las
        # distribuciones de salida entre valores difieren
        actua = disp[caliente] > disp[frio] or (
            set(g[g[param] == frio].salida.astype(str)) !=
            set(g[g[param] == caliente].salida.astype(str)))
        filas.append(dict(modelo=modelo, parametro=param, declarado=decl,
                          observado="aceptado y actua" if actua else "aceptado y no actua",
                          evidencia=ev, fecha=FECHA, error_literal=""))

t = pd.DataFrame(filas)
t.to_csv(RAIZ / "datos" / "tabla_parte2a.csv", index=False)
print(t[["modelo", "parametro", "declarado", "observado", "evidencia"]].to_markdown(index=False))
print()
for _, r in t[t.error_literal != ""].iterrows():
    print(f"[{r.modelo}] {r.parametro}: {r.error_literal}")
