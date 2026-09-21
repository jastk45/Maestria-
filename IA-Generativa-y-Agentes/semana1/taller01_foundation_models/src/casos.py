"""Los 10 casos verificables y el verificador.

Define "acierto" en todo el taller: si el verificador esta mal, las llamadas
miden el verificador y no el modelo.
"""

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CASOS = RAIZ / "datos" / "casos.json"

with open(RUTA_CASOS, encoding="utf-8") as f:
    CASOS = json.load(f)

LIMPIOS = [c for c in CASOS if c["tipo"] == "limpio"]
CONTAMINADOS = [c for c in CASOS if c["tipo"] == "contaminado"]

# separador de miles: 2,870 o 2.870 son UN numero, no dos
_MILES = re.compile(r"(?<=\d)[.,](?=\d{3}\b)")
_ENTERO = re.compile(r"-?\d+")


def extraer_respuesta(texto):
    """Entero que el modelo dio como respuesta final, o None si no hay ninguno.

    Estrategia, en este orden:
      1. Si la salida es JSON con clave 'respuesta', usar ese valor
         (variante structured de la Parte 3).
      2. Si no, quitar el tramo <think>...</think> que devuelve qwen3:
         el razonamiento interno no es la respuesta.
      3. Quitar separadores de miles y tomar el ULTIMO entero del texto.

    El ULTIMO y no el primero porque en Chain-of-Thought el modelo escribe
    los pasos intermedios antes del resultado: tomar el primero contaria
    como fallo una respuesta correcta.
    """
    if texto is None:
        return None
    texto = str(texto)

    # 1. structured output
    try:
        dato = json.loads(texto.strip())
        if isinstance(dato, dict) and "respuesta" in dato:
            return int(dato["respuesta"])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # 2. el razonamiento de qwen3 no es la respuesta
    texto = re.sub(r"<think>.*?</think>", " ", texto, flags=re.DOTALL)

    # 3. ultimo entero, sin separadores de miles
    numeros = _ENTERO.findall(_MILES.sub("", texto))
    return int(numeros[-1]) if numeros else None


def es_correcta(texto, caso):
    """True si la respuesta extraida coincide con la esperada."""
    return extraer_respuesta(texto) == caso["respuesta"]


if __name__ == "__main__":
    print(f"{len(LIMPIOS)} limpios + {len(CONTAMINADOS)} contaminados")
    pruebas = [
        ("311", 311),
        ("La respuesta es 311.", 311),
        ("311 tornillos", 311),
        ('{"respuesta": 311}', 311),
        ("Primero 17*36 = 612. Luego 7*43 = 301. 612 - 301 = 311.", 311),
        ("2,870", 2870),
        ("La respuesta es 2870 pesos.", 2870),
        ("<think>a ver, 12-5</think>7", 7),
        ("no puedo resolverlo", None),
    ]
    for texto, esperado in pruebas:
        obtenido = extraer_respuesta(texto)
        marca = "OK " if obtenido == esperado else "<<<"
        print(f"  {marca} {texto[:48]!r:<52} -> {obtenido} (esperado {esperado})")
