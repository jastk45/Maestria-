"""Taller 04 · 2.c — Los spans de una corrida, leídos de Langfuse: qué pidió el modelo, qué recibió
de cada herramienta, qué decidió cada guardrail y qué respondió.

    python ver_traza.py <traza_id> [<traza_id> ...]
    python ver_traza.py --resultados resultados_base.csv --ids N7 N12 IN3 -o casos/base

Con --resultados, el id del golden set se traduce a su traza_id por la columna del CSV: de una
fila del CSV a sus spans, sin abrir la interfaz. Lo que se imprime sale de las observations de
Langfuse (ya enmascaradas: la máscara corrió antes de enviarlas).
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from langfuse import get_client  # noqa: E402

CAMPOS = "core,basic,io,metadata,model,usage,prompt"


def _fecha(v):
    if v is None or isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def _ms(o) -> float:
    ini, fin = _fecha(o.get("startTime")), _fecha(o.get("endTime"))
    return round((fin - ini).total_seconds() * 1000, 1) if ini and fin else float("nan")


def _corto(x, n=420) -> str:
    t = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    t = " ".join(t.split())
    return t if len(t) <= n else t[:n] + f" …[{len(t) - n} caracteres más]"


def _parsear(o: dict) -> dict:
    """El servidor 4.x devuelve input/output como texto JSON (parseIoAsJson ya no existe)."""
    for k in ("input", "output", "metadata"):
        if isinstance(o.get(k), str):
            try:
                o[k] = json.loads(o[k])
            except json.JSONDecodeError:
                pass
    return o


def observaciones(traza_id: str) -> list[dict]:
    r = get_client().api.observations.get_many(trace_id=traza_id, fields=CAMPOS, limit=200,
                                                expand_metadata="motivo,hallazgos,status,prompt_version")
    obs = [_parsear(o.dict(by_alias=True)) for o in r.data]
    return sorted(obs, key=lambda o: (_fecha(o.get("startTime")) or datetime.min, o.get("parentObservationId") is not None))


def _llm(o) -> str:
    u = o.get("usageDetails") or {}
    ent, sal = u.get("input"), (u.get("output") or 0) + (u.get("output_reasoning_tokens") or 0)
    salida = o.get("output")
    if isinstance(salida, str):
        try:
            salida = json.loads(salida)
        except json.JSONDecodeError:
            pass
    pedidos, texto = [], ""
    if isinstance(salida, dict):
        texto = salida.get("content") or ""
        for tc in salida.get("tool_calls") or []:
            f = tc.get("function", tc)
            pedidos.append(f"{f.get('name')}({_corto(f.get('arguments'), 300)})")
    else:
        texto = salida or ""
    cab = (f"[llm] {o.get('name')} · {_ms(o):.0f} ms · {ent}→{sal} tokens"
           f" · prompt {o.get('promptName') or '—'} v{o.get('promptVersion') or '—'}")
    lineas = [cab]
    if texto:
        lineas.append(f"      dijo: {_corto(texto)}")
    if pedidos:
        lineas.append("      pidió: " + " · ".join(pedidos))
    return "\n".join(lineas)


def describir(traza_id: str, etiqueta: str = "") -> str:
    obs = observaciones(traza_id)
    if not obs:
        return f"traza {traza_id}: Langfuse no devolvió observations (¿flush? ¿rango de fechas?)\n"
    raiz = next((o for o in obs if not o.get("parentObservationId")), obs[0])
    meta = raiz.get("metadata") if isinstance(raiz.get("metadata"), dict) else {}
    lineas = [f"{'=' * 100}", f"{etiqueta}traza {traza_id} · corrida {_ms(raiz):.0f} ms · "
              f"status {meta.get('status', '?')} · prompt_version {meta.get('prompt_version', '?')}"
              + (f" · nivel {raiz.get('level')}: {raiz.get('statusMessage')}" if raiz.get("level") in ("ERROR", "WARNING") else ""),
              f"  pregunta (enmascarada): {_corto((raiz.get('input') or {}).get('pregunta') if isinstance(raiz.get('input'), dict) else raiz.get('input'), 600)}"]
    for o in obs:
        if o is raiz:
            continue
        tipo = o.get("type")
        if tipo == "GUARDRAIL":
            m = o.get("metadata") if isinstance(o.get("metadata"), dict) else {}
            motivo = m.get("motivo") or ""
            lineas.append(f"  [guardrail] {o.get('name')} → {_corto(o.get('output'), 40)} · {_ms(o):.0f} ms"
                          + (f" · {motivo}" if motivo else ""))
        elif tipo == "GENERATION":
            lineas.append("  " + _llm(o))
        elif tipo == "TOOL":
            m = o.get("metadata") if isinstance(o.get("metadata"), dict) else {}
            err = f" · ERROR: {o.get('statusMessage')}" if o.get("level") == "ERROR" else ""
            lineas.append(f"  [herramienta] {o.get('name')}({_corto(o.get('input'), 300)}) · {_ms(o):.0f} ms · "
                          f"{m.get('tamano_resultado_caracteres', '?')} caracteres{err}")
            lineas.append(f"      recibió: {_corto(o.get('output'), 500)}")
        else:
            lineas.append(f"  [{str(tipo).lower()}] {o.get('name')} · {_ms(o):.0f} ms")
    salida = raiz.get("output") if isinstance(raiz.get("output"), dict) else {}
    lineas.append(f"  respuesta final: {_corto(salida.get('answer', raiz.get('output')), 900)}")
    return "\n".join(lineas) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trazas", nargs="*")
    ap.add_argument("--resultados", help="resultados*.csv con la columna traza_id")
    ap.add_argument("--ids", nargs="*", help="ids del golden set (con --resultados)")
    ap.add_argument("-o", "--salida", help="carpeta: un .txt por caso")
    a = ap.parse_args()
    pares = [("", t) for t in a.trazas]
    if a.resultados:
        with open(a.resultados, encoding="utf-8") as f:
            filas = {r["id"]: r for r in csv.DictReader(f)}
        pares += [(f"{i} · ", filas[i]["traza_id"]) for i in (a.ids or [])]
    for etiqueta, traza in pares:
        texto = describir(traza, etiqueta)
        print(texto)
        if a.salida:
            Path(a.salida).mkdir(parents=True, exist_ok=True)
            nombre = (etiqueta.split(" ")[0] or traza[:12]) + ".txt"
            (Path(a.salida) / nombre).write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
