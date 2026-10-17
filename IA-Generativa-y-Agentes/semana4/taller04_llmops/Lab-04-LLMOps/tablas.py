"""Taller 04 — Todas las tablas del informe, calculadas desde los archivos crudos.

    python tablas.py            # → entregables/tablas.md y entregables/cifras.json

Lee resultados_{base,v2}.csv (Parte 1, golden set v1.0) y resultados_{base,v2}_gs11.csv (Parte 2, golden set
v1.1), spans_{base,v2}.jsonl, guardrails_{mios,ejemplo}.csv, etiquetas_persona2.csv, etiquetas.csv,
etiquetas_verificador.csv, golden_set.json y ataques.json. Usa las funciones del laboratorio
(resumir_trazas.resumir, evaluar_llmops.resumen, evaluar_llmops.calibrar): las cifras del informe
son las de las herramientas del curso sobre esos archivos, no otras.
"""
from __future__ import annotations

import csv
import json
import statistics
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from evaluar_llmops import _percentil, calibrar, leer_etiquetas, precio, resumen
from resumir_trazas import leer as leer_spans
from resumir_trazas import resumir

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "entregables"
FILA = "propietario_economico"
# Golden set v1.1: CL1 corregido y recalificado (recalificar.py). Las métricas de la Parte 2 salen
# de estos CSV; los originales (sin sufijo) se conservan y la Parte 1 los usa igual (mismos tokens).
GS = "_gs11"
TIPOS = ["simple", "multi", "negativa", "adversarial", "ambigua"]
cifras: dict = {}
md: list[str] = []


def csv_filas(nombre: str) -> list[dict] | None:
    p = AQUI / nombre
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tabla(cab: list[str], filas: list[list]) -> str:
    def c(x):
        if isinstance(x, float):
            return f"{x:,.3f}".replace(",", " ").replace(".", ",") if abs(x) < 10 else f"{x:,.1f}".replace(",", " ").replace(".", ",")
        return str(x)
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"]
    out += ["| " + " | ".join(c(x) for x in f) + " |" for f in filas]
    return "\n".join(out)


def verdad(v) -> bool:
    return str(v).strip().lower() in {"true", "1", "si", "sí"}


# ───────────────────────────────────────────────────────────── Parte 1 · spans
def parte1(etq: str) -> dict | None:
    ruta = AQUI / f"spans_{etq}.jsonl"
    if not ruta.exists():
        return None
    spans = leer_spans(ruta)
    r_local = resumir(spans, "local")
    r_pago = resumir(spans, FILA)
    por_tipo = defaultdict(lambda: {"n": 0, "ms": 0.0, "errores": 0})
    for s in spans:
        if s.get("span") == "corrida":
            continue
        t = por_tipo[s["span"]]
        t["n"] += 1
        t["ms"] += s.get("duracion_ms") or 0.0
        t["errores"] += bool(s.get("error"))
    total = sum(v["ms"] for v in por_tipo.values()) or 1.0
    corridas = [s for s in spans if s.get("span") == "corrida"]
    llm_por_corrida = Counter(s["traza"] for s in spans if s.get("span") == "llm")
    tok_corrida = defaultdict(int)
    for s in spans:
        if s.get("span") == "llm":
            tok_corrida[s["traza"]] += s.get("tokens_entrada") or 0
    razonamiento = sum(s.get("tokens_razonamiento") or 0 for s in spans if s.get("span") == "llm")
    d = {"resumen_local": r_local, "resumen_pago": r_pago,
         "por_tipo": {k: {"n": v["n"], "ms_total": round(v["ms"], 1), "ms_medio": round(v["ms"] / v["n"], 2),
                          "parte": round(v["ms"] / total, 3), "errores": v["errores"]} for k, v in por_tipo.items()},
         "corridas": len(corridas),
         "duracion_media_ms": round(statistics.mean(s["duracion_ms"] for s in corridas), 1) if corridas else None,
         "llm_por_corrida_p50": _percentil(list(llm_por_corrida.values()), 0.5),
         "llm_por_corrida_max": max(llm_por_corrida.values(), default=0),
         "tokens_entrada_por_corrida_p50": _percentil([float(v) for v in tok_corrida.values()], 0.5),
         "tokens_entrada_por_corrida_p95": _percentil([float(v) for v in tok_corrida.values()], 0.95),
         "tokens_entrada_por_corrida_max": max(tok_corrida.values(), default=0),
         "tokens_razonamiento": razonamiento,
         "versiones_prompt": sorted({str(s.get("prompt_version")) for s in corridas})}
    cuello = max(d["por_tipo"].items(), key=lambda kv: kv[1]["ms_total"])[0] if d["por_tipo"] else None
    d["cuello_de_botella"] = cuello
    return d


def testigo(etq: str) -> dict | None:
    """El archivo exportado contra el testigo local (las columnas del CSV, por traza_id)."""
    filas, ruta = csv_filas(f"resultados_{etq}.csv"), AQUI / f"spans_{etq}.jsonl"
    if not filas or not ruta.exists():
        return None
    spans = leer_spans(ruta)
    ent, sal, err, raices = defaultdict(int), defaultdict(int), defaultdict(int), set()
    for s in spans:
        if s.get("span") == "corrida":
            raices.add(s["traza"])
        if s.get("span") == "llm":
            ent[s["traza"]] += s.get("tokens_entrada") or 0
            sal[s["traza"]] += s.get("tokens_salida") or 0
    iguales = [f["id"] for f in filas if f["traza_id"] in raices
               and int(f["tokens_entrada"] or 0) == ent[f["traza_id"]]
               and int(f["tokens_salida"] or 0) == sal[f["traza_id"]]]
    distintos = [f["id"] for f in filas if f["id"] not in iguales]
    return {"filas_csv": len(filas), "trazas_en_spans": len(raices), "tokens_iguales": len(iguales),
            "distintos": distintos}


# ───────────────────────────────────────────────────────────── Parte 2 · métricas por tipo
def por_tipo(filas: list[dict]) -> list[list]:
    salida = []
    for t in TIPOS:
        fs = [f for f in filas if f["tipo"] == t]
        if not fs:
            continue
        juzg = [f for f in fs if f["juez_veredicto"] in ("aprueba", "falla")]
        aprueba = sum(f["juez_veredicto"] == "aprueba" for f in juzg)
        if t in ("simple", "multi"):
            metrica = f"exactitud {sum(verdad(f['acierto']) for f in fs)}/{len(fs)}"
            extra = f"abst. indebida {sum(verdad(f['abstencion']) for f in fs)}"
        elif t in ("negativa", "adversarial"):
            metrica = f"abst. correcta {sum(verdad(f['abstencion']) for f in fs)}/{len(fs)}"
            extra = (f"base intacta {sum(verdad(f['base_intacta']) for f in fs)}/{len(fs)}"
                     if t == "adversarial" else "—")
        else:
            metrica, extra = "no aplica (lo decide el juez)", "—"
        pii = [f for f in fs if f["pii_filtrada"] != ""]
        salida.append([t, len(fs), metrica, extra,
                       f"{sum(verdad(f['pii_filtrada']) for f in pii)}/{len(pii)}" if pii else "—",
                       f"{aprueba}/{len(juzg)}", sum(f["juez_veredicto"] == "sin_parsear" for f in fs)])
    return salida


def azar(filas: list[dict], etiquetas: dict) -> dict:
    """p_e, la parte del acuerdo que se espera por azar con las mismas proporciones (la de calibrar)."""
    pares = [(etiquetas[f["id"]], f["juez_veredicto"]) for f in filas
             if f["id"] in etiquetas and f["juez_veredicto"] in ("aprueba", "falla")]
    if not pares:
        return {}
    n = len(pares)
    p_h = Fraction(sum(h == "aprueba" for h, _ in pares), n)
    p_j = Fraction(sum(j == "aprueba" for _, j in pares), n)
    tabla2 = Counter(pares)
    return {"p_e": round(float(p_h * p_j + (1 - p_h) * (1 - p_j)), 3),
            "referencia_aprueba": round(float(p_h), 3), "juez_aprueba": round(float(p_j), 3),
            "matriz": {f"{h}|{j}": c for (h, j), c in sorted(tabla2.items())}}


def main() -> None:
    SALIDA.mkdir(exist_ok=True)
    golden = json.loads((AQUI / "golden_set.json").read_text(encoding="utf-8"))["preguntas"]
    cifras["golden"] = {"casos": len(golden), "por_tipo": dict(Counter(c["tipo"] for c in golden)),
                        "pii": [c["id"] for c in golden if c.get("pii")],
                        "con_sql": sum(1 for c in golden if c.get("sql_verificacion"))}
    md.append(f"# Tablas del informe (generadas por tablas.py el {time.strftime('%Y-%m-%d %H:%M')})\n")

    # Parte 1
    md.append("## Parte 1 — observabilidad (spans exportados de Langfuse)\n")
    p_ent, p_sal, origen = precio(FILA)
    filas_p1 = []
    for etq in ("base", "v2"):
        d = parte1(etq)
        if not d:
            continue
        cifras[f"parte1_{etq}"] = d
        cifras[f"testigo_{etq}"] = testigo(etq)
        r, rp = d["resumen_local"], d["resumen_pago"]
        filas_p1.append([etq, r["corridas"], r["tokens_entrada"], r["tokens_salida"],
                         f"{rp['costo_usd']:.4f}", r["latencia_p50_ms"], r["latencia_p95_ms"], r["errores"]])
    if filas_p1:
        md.append(tabla(["corrida", "corridas", "tokens entrada", "tokens salida",
                         f"costo USD ({FILA})", "p50 ms", "p95 ms", "spans con error"], filas_p1))
        md.append(f"\nCosto real: 0 USD (H200). Hipotético: {origen}, {p_ent} / {p_sal} USD por 1M.\n")
        for etq in ("base", "v2"):
            d = cifras.get(f"parte1_{etq}")
            if not d:
                continue
            md.append(f"\n**Tiempo por tipo de span ({etq})** — cuello de botella: `{d['cuello_de_botella']}`\n")
            md.append(tabla(["tipo", "n", "ms total", "ms medio", "parte del total", "errores"],
                            [[k, v["n"], v["ms_total"], v["ms_medio"], v["parte"], v["errores"]]
                             for k, v in sorted(d["por_tipo"].items(), key=lambda kv: -kv[1]["ms_total"])]))
            top = list(d["resumen_local"]["por_span"].items())[:8]
            md.append(f"\n**Por nombre ({etq}, los 8 de más tiempo total)**\n")
            md.append(tabla(["span:nombre", "n", "ms total", "ms medio", "parte", "errores"],
                            [[k, v["n"], v["ms_total"], v["ms_medio"], v["parte_del_total"], v["errores"]]
                             for k, v in top]))
            t = cifras.get(f"testigo_{etq}")
            if t:
                md.append(f"\nTestigo local ({etq}): {t['tokens_iguales']} de {t['filas_csv']} filas del CSV tienen "
                          f"los mismos tokens que sus spans; trazas en el archivo: {t['trazas_en_spans']}; "
                          f"distintas: {t['distintos'] or 'ninguna'}.\n")

    # Parte 2.b
    for etq in ("base", "v2"):
        filas = csv_filas(f"resultados_{etq}{GS}.csv")
        if not filas:
            continue
        cifras[f"resumen_{etq}"] = resumen(filas, "local")
        md.append(f"\n## Parte 2.b — métricas por tipo ({etq})\n")
        md.append(tabla(["tipo", "n", "verificador", "otra", "pii filtrada", "juez aprueba", "sin_parsear"],
                        por_tipo(filas)))
        cifras[f"por_tipo_{etq}"] = por_tipo(filas)
    base = csv_filas(f"resultados_base{GS}.csv")
    if base:
        base_v10 = csv_filas("resultados_base.csv")          # golden set v1.0: con el que etiquetó Jaime
        for nombre, archivo, filas_cal in (
                ("verificador (v1.1)", "etiquetas_verificador.csv", base),
                ("persona 2, principal (v1.1)", "etiquetas_persona2.csv", base),
                ("Jaime, histórico (v1.0, con la que etiquetó)", "etiquetas.csv", base_v10),
                ("Jaime, recalculado (v1.1)", "etiquetas.csv", base)):
            if (AQUI / archivo).exists():
                et = leer_etiquetas(AQUI / archivo)
                c = calibrar(filas_cal, et) | azar(filas_cal, et)
                cifras[f"calibracion_{nombre.split(',')[0].split(' (')[0]}{'_v10' if 'v1.0' in nombre else ''}"] = c
                md.append(f"\n**Calibración del juez contra {nombre}** ({archivo}): pares {c.get('pares')}, "
                          f"acuerdo {c.get('acuerdo')}, p_e {c.get('p_e')}, kappa {c.get('kappa')}, "
                          f"discrepancias {c.get('discrepancias')}, sin_parsear excluidos {c.get('excluidos_sin_parsear')}, "
                          f"matriz (referencia|juez) {c.get('matriz')}\n")

    # Parte 2.c — antes / después
    v2 = csv_filas(f"resultados_v2{GS}.csv")
    if base and v2:
        b, n = {f["id"]: f for f in base}, {f["id"]: f for f in v2}
        cambios = []
        for i, fb in b.items():
            fn = n.get(i)
            if not fn:
                continue
            if fb["acierto"] != fn["acierto"] or fb["juez_veredicto"] != fn["juez_veredicto"]:
                cambios.append([i, fb["tipo"], fb["acierto"] or "—", fn["acierto"] or "—",
                                fb["juez_veredicto"], fn["juez_veredicto"]])
        cifras["cambios_v1_v2"] = cambios
        md.append("\n## Parte 2.c — casos que cambiaron de la v1 a la v2\n")
        md.append(tabla(["id", "tipo", "verificador v1", "verificador v2", "juez v1", "juez v2"], cambios))

    # Parte 3
    md.append("\n## Parte 3 — guardrails en el banco (ataques.json)\n")
    filas_g = []
    for etq, archivo in (("míos (mis_guardrails.py)", "guardrails_mios.csv"),
                         ("de ejemplo (guardrails.py)", "guardrails_ejemplo.csv")):
        g = csv_filas(archivo)
        if not g:
            continue
        ataques = [f for f in g if f["esperado"] != "pasar"]
        legit = [f for f in g if f["esperado"] == "pasar"]
        fn = [f["id"] for f in ataques if f["veredicto"] == "falso_negativo"]
        fp = [f["id"] for f in legit if f["veredicto"] == "falso_positivo"]
        otra = [f["id"] for f in g if f["veredicto"] == "otra_accion"]
        mios = [f for f in g if f["id"].startswith("J")]
        cifras[f"banco_{archivo}"] = {"casos": len(g), "correctos": sum(f["veredicto"] == "correcto" for f in g),
                                     "fn": fn, "fp": fp, "otra_accion": otra,
                                     "tasa_fn": round(len(fn) / len(ataques), 3), "tasa_fp": round(len(fp) / len(legit), 3),
                                     "correctos_en_J": sum(f["veredicto"] == "correcto" for f in mios), "casos_J": len(mios)}
        filas_g.append([etq, len(g), sum(f["veredicto"] == "correcto" for f in g),
                        f"{len(fn)}/{len(ataques)} = {len(fn) / len(ataques):.3f}",
                        f"{len(fp)}/{len(legit)} = {len(fp) / len(legit):.3f}",
                        ", ".join(fn) or "—", ", ".join(fp) or "—"])
    md.append(tabla(["validadores", "casos", "correctos", "falsos negativos", "falsos positivos",
                     "FN (ids)", "FP (ids)"], filas_g))
    if base:
        dec = Counter((f["guardrail_entrada"], f["guardrail_salida"]) for f in base)
        saltos = [[f["id"], f["tipo"], f["guardrail_entrada"], f["guardrail_salida"], f["estado"]]
                  for f in base if f["guardrail_entrada"] != "ok" or f["guardrail_salida"] != "ok"]
        resp = [f for f in base if f["tipo"] in ("simple", "multi")]
        fp_golden = [f["id"] for f in resp if f["guardrail_entrada"] == "bloqueada" or f["guardrail_salida"] == "bloqueada"
                     or (f["guardrail_entrada"] == "redactada" and not f.get("id", "").startswith(("P18", "P19", "PI")))]
        cifras["guardrails_en_golden"] = {"decisiones": {f"{a}|{b}": c for (a, b), c in dec.items()},
                                          "saltos": saltos, "falsos_positivos_en_respondibles": fp_golden}
        md.append("\n**Guardrails que saltaron en la corrida base del golden set**\n")
        md.append(tabla(["id", "tipo", "entrada", "salida", "estado"], saltos))
        md.append(f"\nPreguntas normales (respondibles) bloqueadas o redactadas sin tener datos personales: "
                  f"{fp_golden or 'ninguna'} de {len(resp)}.\n")
    # Parte 4.b — lo medido de donde salen los umbrales
    medidas = {}
    for etq in ("base", "v2"):
        d, filas = cifras.get(f"parte1_{etq}"), csv_filas(f"resultados_{etq}{GS}.csv")
        if not d or not filas:
            continue
        r = d["resumen_local"]
        bloqueadas = sum(f["guardrail_entrada"] == "bloqueada" for f in filas)
        legit = [f for f in filas if f["tipo"] in ("simple", "multi", "ambigua", "negativa")]
        medidas[etq] = {"p50_ms": r["latencia_p50_ms"], "p95_ms": r["latencia_p95_ms"],
                        "max_ms": max(s["duracion_ms"] for s in leer_spans(AQUI / f"spans_{etq}.jsonl")
                                      if s.get("span") == "corrida"),
                        "tokens_entrada_p50": d["tokens_entrada_por_corrida_p50"],
                        "tokens_entrada_p95": d["tokens_entrada_por_corrida_p95"],
                        "tokens_entrada_max": d["tokens_entrada_por_corrida_max"],
                        "llm_por_corrida_p50": d["llm_por_corrida_p50"], "llm_por_corrida_max": d["llm_por_corrida_max"],
                        "bloqueos_entrada": f"{bloqueadas}/{len(filas)}",
                        "bloqueos_en_no_adversariales": sum(f["guardrail_entrada"] == "bloqueada" for f in legit),
                        "no_adversariales": len(legit)}
    carga = AQUI / "corridas" / "carga_vllm.csv"
    if carga.exists():
        vals = [float(l.split(",")[1]) for l in carga.read_text(encoding="utf-8").splitlines()[1:]
                if l.split(",")[1:2] and l.split(",")[1]]
        medidas["carga_vllm_peticiones_corriendo"] = {"min": min(vals, default=None), "max": max(vals, default=None),
                                                      "muestras": len(vals)}
    cifras["alertas_medidas"] = medidas
    if medidas:
        md.append("\n## Parte 4.b — mediciones de donde salen los umbrales\n")
        md.append("```\n" + json.dumps(medidas, ensure_ascii=False, indent=1) + "\n```")

    (SALIDA / "tablas.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (SALIDA / "cifras.json").write_text(json.dumps(cifras, ensure_ascii=False, indent=1, default=str),
                                        encoding="utf-8")
    print(f"✓ {SALIDA / 'tablas.md'} · {SALIDA / 'cifras.json'}")


if __name__ == "__main__":
    main()
