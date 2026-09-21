"""Graficas y tablas derivadas de datos/resultados.csv."""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
FIG = RAIZ / "figuras"
FIG.mkdir(exist_ok=True)

df = pd.read_csv(RAIZ / "datos" / "resultados.csv")
df["parte"] = df["parte"].astype(str)
AZUL, NARANJA = "#1565C0", "#E65100"


def tabla(nombre, t):
    print(f"\n### {nombre}\n")
    print(t.to_markdown(index=False))
    t.to_csv(RAIZ / "datos" / f"tabla_{nombre}.csv", index=False)


# ------------------------------------------------------------------ Parte 1
p1 = df[df.parte == "1"]
if len(p1):
    t = (p1.groupby("modelo")
           .agg(exactitud=("acierto", "mean"),
                latencia_s=("latencia_s", "mean"),
                tokens_in=("tokens_entrada", "sum"),
                tokens_out=("tokens_salida", "sum"),
                costo_usd=("costo_usd", "sum"))
           .round(5).reset_index())
    fechas = {"gpt-4o-mini": "2026-08-26", "gpt-5.6-luna": "2026-09-18",
              "qwen3:1.7b": "local (cero real)"}
    t["precio_verificado"] = t["modelo"].map(fechas)
    tabla("parte1", t)

# ---------------------------------------------------------------- Parte 2.b
p2b_todo = df[df.parte == "2b"]
p2b = p2b_todo[p2b_todo.top_k.isna()]        # rejilla T x top_p (OpenAI)
p2bk = p2b_todo[p2b_todo.top_k.notna()]      # barrido top_k (local)

if len(p2bk):
    est_k = (p2bk.groupby(["top_k", "caso_id"])["salida"]
                 .agg(lambda s: s.value_counts(dropna=False).iloc[0] / len(s))
                 .groupby(level=0).mean().rename("estabilidad_salida"))
    tk = (p2bk.groupby("top_k")
              .agg(modelo=("modelo", "first"),
                   temperature=("temperature", "first"),
                   exactitud=("acierto", "mean"),
                   tokens_out=("tokens_salida", "mean"))
              .join(est_k).reset_index())
    # greedy: cuantos casos dieron salida IDENTICA en las 5 corridas
    ident = (p2bk.groupby(["top_k", "caso_id"])["salida"].nunique()
                 .eq(1).groupby(level=0).sum().rename("casos_identicos_x5"))
    tk = tk.merge(ident.reset_index(), on="top_k")
    tabla("parte2b_topk", tk.round(3))

if len(p2b):
    g = (p2b.groupby(["temperature", "top_p"])
            .agg(exactitud=("acierto", "mean"),
                 tokens_out=("tokens_salida", "mean"))
            .reset_index())
    # estabilidad: fraccion de corridas que dieron la respuesta modal
    est = (p2b.groupby(["temperature", "top_p", "caso_id"])["respuesta_extraida"]
              .agg(lambda s: s.value_counts(dropna=False).iloc[0] / len(s))
              .groupby(level=[0, 1]).mean().reset_index(name="estabilidad"))
    g = g.merge(est, on=["temperature", "top_p"])
    tabla("parte2b", g.round(3))

    piv = g.pivot(index="temperature", columns="top_p", values="exactitud").astype(float)
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    im = ax.imshow(piv.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(piv.columns)), [f"{c:g}" for c in piv.columns])
    ax.set_yticks(range(len(piv.index)), [f"{i:g}" for i in piv.index])
    ax.set_xlabel("top_p"); ax.set_ylabel("temperature")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax.text(j, i, f"{v:.0%}", ha="center", va="center",
                    color="white" if v > 0.5 else "black", fontsize=9)
    ax.set_title("Parte 2.b — exactitud por celda (gpt-4o-mini)")
    fig.colorbar(im, ax=ax, label="exactitud")
    fig.tight_layout(); fig.savefig(FIG / "parte2b_rejilla.png", dpi=140)
    plt.close(fig)

# ------------------------------------------------------------------ Parte 3
p3 = df[df.parte == "3"]
if len(p3):
    orden = ["zero_shot", "few_shot", "cot", "structured"]
    t = (p3.groupby("plantilla")
           .agg(exactitud=("acierto", "mean"),
                tokens_in=("tokens_entrada", "sum"),
                tokens_out=("tokens_salida", "sum"),
                costo_usd=("costo_usd", "sum"))
           .reindex(orden).round(5).reset_index())
    tabla("parte3", t)

# ---------------------------------------------------------------- Parte 4.a
p4 = df[df.parte == "4a"]
if len(p4):
    niveles = ["low", "medium", "high"]
    t = (p4.groupby("esfuerzo")
           .agg(exactitud=("acierto", "mean"),
                tokens_razonamiento=("tokens_razonamiento", "sum"),
                tokens_salida=("tokens_salida", "sum"),
                latencia_s=("latencia_s", "mean"),
                costo_usd=("costo_usd", "sum"))
           .reindex(niveles).reset_index())
    t["tokens_visibles"] = t.tokens_salida - t.tokens_razonamiento
    tabla("parte4a", t.round(5))

    # GRAFICA 1 -- exactitud frente a tokens de razonamiento
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.plot(t.tokens_razonamiento, t.exactitud, "o-", color=AZUL, lw=2, ms=9)
    for _, r in t.iterrows():
        ax.annotate(r.esfuerzo, (r.tokens_razonamiento, r.exactitud),
                    textcoords="offset points", xytext=(0, 11), ha="center")
    ax.set_xlabel("tokens de razonamiento (medidos, 10 casos)")
    ax.set_ylabel("exactitud")
    ax.set_ylim(-0.05, 1.15); ax.grid(alpha=.3)
    ax.set_title("Parte 4.a — exactitud vs tokens de razonamiento")
    fig.tight_layout(); fig.savefig(FIG / "parte4a_exactitud_vs_tokens.png", dpi=140)
    plt.close(fig)

    # GRAFICA 2 -- costo USD frente a exactitud
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.plot(t.exactitud, t.costo_usd, "s-", color=NARANJA, lw=2, ms=9)
    for _, r in t.iterrows():
        ax.annotate(r.esfuerzo, (r.exactitud, r.costo_usd),
                    textcoords="offset points", xytext=(0, 11), ha="center")
    ax.set_xlabel("exactitud"); ax.set_ylabel("costo USD (10 casos)")
    ax.set_xlim(-0.05, 1.15); ax.grid(alpha=.3)
    ax.set_title("Parte 4.a — costo vs exactitud")
    fig.tight_layout(); fig.savefig(FIG / "parte4a_costo_vs_exactitud.png", dpi=140)
    plt.close(fig)

# ---------------------------------------------------------------- Parte 4.b
p4b = df[df.parte == "4b"]
if len(p4b):
    t = (p4b.groupby(["esfuerzo", "caso_id"])
            .agg(acierto=("acierto", "mean"),
                 tokens_razonamiento=("tokens_razonamiento", "sum"))
            .reset_index())
    tabla("parte4b", t)

print("\nfiguras:", sorted(p.name for p in FIG.glob("*.png")))
