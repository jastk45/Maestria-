"""Taller 04 — Busca datos personales y claves en los spans ANTES de subirlos.

    python buscar_pii.py --sesion jaime-astudillo-base jaime-astudillo-v2 \
        --archivos spans_base.jsonl spans_v2.jsonl resultados_base.csv resultados_v2.csv

Dos búsquedas sobre cada observation de Langfuse (input, output, metadata, nombre y mensaje de
estado: lo que guardó el servidor, no lo que el código cree haber enviado) y sobre cada archivo:

1. Los valores literales de los campos `pii` del golden set (correo, cédula, RUC, teléfonos y
   la clave de CL1), también sin espacios ni guiones.
2. Los detectores de mis_guardrails.py (correo, celular, fijo, cédula/RUC con su estructura y
   claves por su forma), por si se filtró un dato que no está en el golden set.

Sale con código 1 si encuentra algo: así se puede poner antes de un commit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
load_dotenv(AQUI / ".env")

import mis_guardrails as G  # noqa: E402


def valores_pii(golden: Path) -> list[str]:
    casos = json.loads(golden.read_text(encoding="utf-8"))["preguntas"]
    vals = {v for c in casos for v in c.get("pii", [])}
    vals |= {re.sub(r"[\s().-]", "", v) for v in vals}           # 099 123 4567 → 0991234567
    return sorted(v for v in vals if len(v) >= 6)


IDS_HEX = re.compile(r"\b[0-9a-f]{32}\b|\b[0-9a-f]{16}\b")      # ids de traza/observation: azar hex
CLAVE_PUBLICA = re.compile(r'"scope\.attributes\.public_key":\s*"pk-lf-[^"]*"')  # la pone el servidor


def detectores(texto: str) -> list[str]:
    """Los ids hexadecimales se quitan antes (diez dígitos seguidos dentro de un id parecen una
    cédula), y también la clave PÚBLICA del proyecto que el servidor guarda en la metadata de cada
    observation (`scope.attributes.public_key`): no es secreta. La secreta (sk-lf-) sí se busca."""
    texto = CLAVE_PUBLICA.sub('"scope.attributes.public_key": "<pública>"', IDS_HEX.sub("<id>", texto))
    hallado = []
    _, tipos = G.redactar_pii(texto)
    hallado += [f"pii:{t}" for t in sorted(set(tipos))]
    hallado += [f"clave:{t}" for t in G.buscar_claves(texto)]
    return hallado


def observaciones(sesion: str | None = None, desde=None, hasta=None) -> list[dict]:
    from langfuse import get_client
    lf, obs, cursor = get_client(), [], None
    while True:
        r = lf.api.observations.get_many(session_id=sesion, fields="core,basic,io,metadata",
                                         limit=500, cursor=cursor, expand_metadata="motivo,hallazgos",
                                         from_start_time=desde, to_start_time=hasta)
        obs += [o.dict(by_alias=True) for o in r.data]
        cursor = (r.meta.dict(by_alias=True) if r.meta else {}).get("cursor")
        if not cursor or not r.data:
            return obs


def revisar(nombre: str, textos: list[str], vals: list[str]) -> int:
    literal = {v: sum(v in t for t in textos) for v in vals}
    generico: dict[str, int] = {}
    for t in textos:
        for h in detectores(t):
            generico[h] = generico.get(h, 0) + 1
    encontrados = {k: n for k, n in literal.items() if n}
    print(f"{nombre}: {len(textos)} registros · valores pii del golden set encontrados: "
          f"{encontrados or 'ninguno'} · detectores: {generico or 'ninguno'}")
    return sum(encontrados.values()) + sum(generico.values())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--golden", default=str(AQUI / "golden_set.json"))
    ap.add_argument("--sesion", nargs="*", default=[])
    ap.add_argument("--archivos", nargs="*", default=[])
    ap.add_argument("--desde", help="ISO 8601: además, TODAS las observations de la ventana (también las del juez, sin sesión)")
    ap.add_argument("--hasta")
    a = ap.parse_args()
    vals = valores_pii(Path(a.golden))
    print(f"{len(vals)} valores pii a buscar (de los campos `pii` del golden set)")
    total = 0
    for s in a.sesion:
        obs = observaciones(s)
        textos = [json.dumps({k: o.get(k) for k in ("name", "input", "output", "metadata", "statusMessage")},
                             ensure_ascii=False, default=str) for o in obs]
        total += revisar(f"Langfuse, sesión {s}", textos, vals)
    if a.desde:
        from datetime import datetime
        f = lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")) if v else None
        obs = observaciones(None, f(a.desde), f(a.hasta))
        textos = [json.dumps({k: o.get(k) for k in ("name", "input", "output", "metadata", "statusMessage")},
                             ensure_ascii=False, default=str) for o in obs]
        total += revisar(f"Langfuse, todo de {a.desde} a {a.hasta or 'ahora'}", textos, vals)
    for ruta in a.archivos:
        p = Path(ruta)
        archivos = sorted(p.rglob("*.json*")) if p.is_dir() else [p]
        if p.suffix == ".csv":      # la columna `pregunta` trae los datos ficticios del golden set a propósito
            import csv as _csv
            with open(p, encoding="utf-8") as fh:
                textos = [r.get("respuesta", "") for r in _csv.DictReader(fh)]
        else:
            textos = [l for f in archivos for l in f.read_text(encoding="utf-8").splitlines()]
        total += revisar(str(ruta), textos, vals)
    print("✓ nada que se parezca a un dato personal o a una clave" if total == 0 else
          f"✗ {total} apariciones: revisa antes de subir")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
