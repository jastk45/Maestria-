"""Taller 04 — Las versiones del prompt de sistema del agente, con su changelog.

    python prompts_agente.py registrar v1      # v1 → Langfuse, etiqueta production
    python prompts_agente.py registrar v2      # v2 → Langfuse, etiqueta candidata
    python prompts_agente.py promover 2        # production pasa a la v2 (promover 1 = rollback)
    python prompts_agente.py ver               # las versiones que hay en Langfuse

El agente no lee el prompt de este archivo: lo pide a Langfuse por etiqueta o por versión
(agente_llmops.py) y liga cada generation a esa versión (langfuse_prompt=prompt). Este archivo
es la fuente desde la que se registran, y el changelog.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
sys.path.append(str(AQUI.parent / "Lab-03-Agentes"))
load_dotenv(AQUI / ".env")

from mi_agente import SISTEMA  # noqa: E402  — el prompt del Taller 3, tal cual

NOMBRE = "agente-sql-sistema"

# v1 — el del Taller 3, sin un carácter de diferencia.
PROMPT_V1 = SISTEMA

# v2 — la mejora de la Parte 2.c, a partir de los peores casos de la v1 (N13 en la base; N7, N12 y
# N13 en la repetición): el modelo completa con un supuesto un dato que la base no registra. Un
# solo cambio: una regla nueva, insertada antes de la de abstención; el resto es la v1, carácter
# por carácter.
_REGLA_V2 = (
    "- No resuelvas con un supuesto lo que la base no registra. Si la respuesta depende de un\n"
    "  dato que ninguna columna registra (otra moneda, un impuesto, un costo, una unidad distinta\n"
    "  de las unidades vendidas, un precio o un estado en una fecha pasada), no lo supongas ni\n"
    "  rotules la cifra con él: abstente con la frase de abajo y di qué dato falta.\n")
_ANCLA = "- Si los datos no alcanzan para responder"
assert PROMPT_V1.count(_ANCLA) == 1
PROMPT_V2 = PROMPT_V1.replace(_ANCLA, _REGLA_V2 + _ANCLA)

CHANGELOG = {
    "v1": "v1: prompt del Taller 3 sin cambios (seis reglas, frase de abstención).",
    "v2": ("v2: regla nueva contra los supuestos silenciosos: abstenerse si la respuesta depende de un "
           "dato que la base no registra (moneda, impuesto, costo, unidad, precio pasado). Sale de los "
           "peores casos de la v1: N13 (base) y N7, N12, N13 (repetición)."),
}


def _lf():
    from langfuse import get_client
    lf = get_client()
    if not lf.auth_check():
        raise SystemExit("Langfuse no responde o las claves no valen: revisa LANGFUSE_* en .env.")
    return lf


def versiones() -> list[int]:
    try:
        metas = _lf().api.prompts.list(name=NOMBRE).data
    except Exception:
        return []
    return sorted(v for m in metas if m.name == NOMBRE for v in (m.versions or []))


def registrar(cual: str) -> None:
    texto = {"v1": PROMPT_V1, "v2": PROMPT_V2}[cual]
    if texto is None:
        raise SystemExit(f"{cual} todavía no está escrita.")
    existentes = versiones()
    esperada = {"v1": 1, "v2": 2}[cual]
    if esperada in existentes:
        print(f"«{NOMBRE}» ya tiene la versión {esperada}: no se crea otra.")
        return
    if esperada != len(existentes) + 1:
        raise SystemExit(f"Se esperaba registrar la versión {esperada} y Langfuse tiene {existentes}.")
    p = _lf().create_prompt(name=NOMBRE, type="text", prompt=texto,
                            labels=["production"] if cual == "v1" else ["candidata"],
                            commit_message=CHANGELOG[cual])
    print(f"«{NOMBRE}» v{p.version} registrada · etiquetas {p.labels} · «{CHANGELOG[cual]}»")


def promover(version: int) -> None:
    _lf().update_prompt(name=NOMBRE, version=version, new_labels=["production"])
    print(f"production → v{version}")


if __name__ == "__main__":
    orden = sys.argv[1:] or ["ver"]
    if orden[0] == "registrar":
        registrar(orden[1])
    elif orden[0] == "promover":
        promover(int(orden[1]))
    else:
        for v in versiones():
            p = _lf().get_prompt(NOMBRE, version=v, cache_ttl_seconds=0)
            print(f"v{p.version} · etiquetas {p.labels} · {len(p.prompt)} caracteres · "
                  f"commit «{getattr(p, 'commit_message', '') or ''}»")
