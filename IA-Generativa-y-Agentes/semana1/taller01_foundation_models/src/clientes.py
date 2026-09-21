"""Una sola funcion que llama al modelo. Todo el taller son barridos sobre ella.

Dos proveedores detras de la MISMA firma:
  - OpenAI  (gpt-4o-mini, gpt-5.6-luna)  -- necesita clave
  - Ollama  (qwen3:1.7b)                 -- local, costo cero
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

cliente_openai = OpenAI()
URL_OLLAMA = "http://localhost:11434"

# De la tabla semestral del enunciado, con la fecha de CADA fila.
PRECIOS = {
    "gpt-4o-mini":  {"entrada": 0.15, "salida": 0.60, "verificado": "2026-08-26",
                     "fila": "propietario_economico"},
    "gpt-5.6-luna": {"entrada": 0.20, "salida": 1.20, "verificado": "2026-09-18",
                     "fila": "openai_razonamiento"},
    "qwen3:1.7b":   {"entrada": 0.0,  "salida": 0.0,  "verificado": None,
                     "fila": "open_weight_pequeno"},
    "openai-community/gpt2": {"entrada": 0.0, "salida": 0.0, "verificado": None,
                              "fila": "base_local"},
}

# Modelos de razonamiento: el SDK los expone por reasoning_effort y rechaza
# temperature / top_p (fila openai_razonamiento, valor no_en_esta_fila).
RAZONAMIENTO = {"gpt-5.6-luna"}


def costo_usd(modelo, tokens_entrada, tokens_salida):
    """USD de una llamada. Los tokens de razonamiento van dentro de salida."""
    p = PRECIOS.get(modelo)
    if not p:
        return None
    return ((tokens_entrada or 0) * p["entrada"]
            + (tokens_salida or 0) * p["salida"]) / 1_000_000


def construir_prompt(caso, plantilla="zero_shot"):
    """Las cuatro variantes de la Parte 3."""
    from prompts import (prompt_zero_shot, prompt_few_shot, prompt_cot,
                         prompt_structured)
    return {
        "zero_shot": prompt_zero_shot,
        "few_shot": prompt_few_shot,
        "cot": prompt_cot,
        "structured": prompt_structured,
    }[plantilla](caso)


def llamar(caso, modelo="gpt-4o-mini", plantilla="zero_shot",
           temperature=None, top_p=None, top_k=None, esfuerzo=None,
           corrida=0):
    """Una llamada = una fila de resultados.csv

    None en temperature / top_p significa NO MANDAR el parametro. Mandar el
    valor por defecto y no mandar nada son cosas distintas, y la matriz de
    la Parte 2.a mide justamente esa diferencia.
    """
    kwargs = {
        "model": modelo,
        "messages": [{"role": "user", "content": construir_prompt(caso, plantilla)}],
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if top_p is not None:
        kwargs["top_p"] = top_p
    if top_k is not None:                      # OpenAI no lo expone: 400 esperado
        kwargs["top_k"] = top_k
    if esfuerzo is not None:
        kwargs["reasoning_effort"] = esfuerzo
    if plantilla == "structured":
        kwargs["response_format"] = {"type": "json_object"}

    t0 = time.perf_counter()
    try:
        r = cliente_openai.chat.completions.create(**kwargs)
        latencia = time.perf_counter() - t0
    except Exception as e:
        # Un error NO es un bug: es el resultado "rechazado" de la matriz 2.a.
        return fila(caso, modelo, plantilla, temperature, top_p, top_k,
                    esfuerzo, corrida,
                    latencia_s=time.perf_counter() - t0,
                    error_codigo=getattr(e, "status_code", type(e).__name__),
                    error_mensaje=str(e)[:500])

    u = r.usage
    razonamiento = None
    det = getattr(u, "completion_tokens_details", None)
    if det is not None:
        razonamiento = getattr(det, "reasoning_tokens", None)

    return fila(caso, modelo, plantilla, temperature, top_p, top_k,
                esfuerzo, corrida,
                salida=r.choices[0].message.content,
                tokens_entrada=u.prompt_tokens,
                tokens_salida=u.completion_tokens,
                tokens_razonamiento=razonamiento,
                latencia_s=latencia)


def llamar_ollama(caso, modelo="qwen3:1.7b", plantilla="zero_shot",
                  temperature=None, top_p=None, top_k=None, esfuerzo=None,
                  corrida=0):
    """Misma firma, proveedor local. Los parametros de muestreo van DENTRO
    de 'options'. qwen3 razona en un tramo <think>...</think>."""
    opciones = {}
    if temperature is not None:
        opciones["temperature"] = temperature
    if top_p is not None:
        opciones["top_p"] = top_p
    if top_k is not None:
        opciones["top_k"] = top_k

    cuerpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": construir_prompt(caso, plantilla)}],
        "stream": False,
    }
    if opciones:
        cuerpo["options"] = opciones
    if esfuerzo is not None:
        cuerpo["think"] = esfuerzo

    req = urllib.request.Request(
        f"{URL_OLLAMA}/api/chat", data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json"})

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            d = json.loads(resp.read())
        latencia = time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return fila(caso, modelo, plantilla, temperature, top_p, top_k,
                    esfuerzo, corrida, latencia_s=time.perf_counter() - t0,
                    error_codigo=e.code, error_mensaje=e.read().decode()[:500])
    except Exception as e:
        return fila(caso, modelo, plantilla, temperature, top_p, top_k,
                    esfuerzo, corrida, latencia_s=time.perf_counter() - t0,
                    error_codigo=type(e).__name__, error_mensaje=str(e)[:500])

    msg = d.get("message", {})
    texto = msg.get("content", "")
    pensado = msg.get("thinking") or ""
    # Ollama devuelve eval_count = TODOS los tokens generados (thinking + respuesta)
    # pero no separa los del thinking. Se miden en la misma unidad restando los
    # tokens de la respuesta visible, contados con el tokenizador del modelo.
    eval_count = d.get("eval_count")
    razonamiento = None
    if pensado and eval_count is not None:
        visibles = _tokens_qwen(texto)
        # sin tokenizador no hay medida en la misma unidad: se deja ausente,
        # nunca se restan palabras de un contador de tokens
        razonamiento = max(eval_count - visibles, 0) if visibles is not None else None
    return fila(caso, modelo, plantilla, temperature, top_p, top_k,
                esfuerzo, corrida,
                salida=texto,
                tokens_entrada=d.get("prompt_eval_count"),
                tokens_salida=eval_count,
                tokens_razonamiento=razonamiento,
                latencia_s=latencia)


_TOK_QWEN = None


def _tokens_qwen(texto):
    """Tokens de un texto con el tokenizador de Qwen3 (Apache 2.0, sin gate).
    Si no se puede cargar devuelve None: no hay medida valida en tokens."""
    global _TOK_QWEN
    if _TOK_QWEN is None:
        try:
            from transformers import AutoTokenizer
            _TOK_QWEN = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")
        except Exception as e:  # sin red o sin transformers
            print(f"(tokenizador Qwen no disponible; tokens_razonamiento quedara vacio: {e})")
            _TOK_QWEN = False
    if _TOK_QWEN is False:
        return None
    return len(_TOK_QWEN(str(texto))["input_ids"])


def fila(caso, modelo, plantilla, temperature, top_p, top_k, esfuerzo, corrida,
         salida=None, tokens_entrada=None, tokens_salida=None,
         tokens_razonamiento=None, latencia_s=None,
         error_codigo=None, error_mensaje=None):
    """Una fila de resultados.csv. Todas las llamadas pasan por aqui para que
    el CSV tenga siempre las mismas columnas."""
    from casos import extraer_respuesta

    extraida = extraer_respuesta(salida) if salida else None
    return {
        "caso_id": caso["id"],
        "tipo": caso["tipo"],
        "modelo": modelo,
        "plantilla": plantilla,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "esfuerzo": esfuerzo,
        "corrida": corrida,
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
        "tokens_razonamiento": tokens_razonamiento,
        "latencia_s": latencia_s,
        "costo_usd": costo_usd(modelo, tokens_entrada, tokens_salida),
        "salida": salida,
        "respuesta_extraida": extraida,
        "esperada": caso["respuesta"],
        "acierto": extraida == caso["respuesta"] if extraida is not None else False,
        "error_codigo": error_codigo,
        "error_mensaje": error_mensaje,
    }
