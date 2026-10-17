"""Demo de la sesión 17 — observabilidad con Langfuse, en seis pasos.

Un asistente mínimo responde preguntas sobre el calendario de la semana 4: busca en una tabla
de cuatro filas (un *retriever*) y redacta con un LLM (una *generation*). Es más pequeño que el
agente del laboratorio a propósito: aquí no se mira el agente, se mira su traza.

    python demo.py                    # el menú
    python demo.py 1   (sin-trazas)   # el problema: respuestas y ningún dato
    python demo.py 2   (prompts)      # registra el prompt: v1 (production) y v2 (candidata)
    python demo.py 3   (trazas)       # las preguntas, trazadas, con la versión en production
    python demo.py 4   (candidata)    # las mismas, con la v2 — también: trazas candidata | trazas v2
    python demo.py 5   (promover)     # production pasa a la v2; «promover 1» es el rollback
    python demo.py 6   (falla)        # una herramienta que falla y un correo enmascarado

Necesita un `.env` en esta carpeta con dos bloques (ver `.env.example`):
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL   ← ./levantar_langfuse.sh los escribe
    OPENAI_BASE_URL, OPENAI_API_KEY                               ← el modelo: la H200, Ollama o la clave del curso
El paso 1 solo necesita el modelo.

Probado el 2026-10-06 con langfuse 4.17.0 (SDK de Python), Langfuse 4.50.0 (servidor) y
openai 3.22.1, contra el vLLM de la H200 y desde una copia limpia del ZIP.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

try:
    from dotenv import load_dotenv
    from langfuse import Langfuse, get_client, observe, propagate_attributes
    from langfuse.openai import OpenAI          # el cliente de OpenAI de siempre, con trazas
    import openai
except ImportError as err:
    sys.exit(f"Falta un paquete ({err.name}). Instala las dependencias en un entorno virtual:\n"
             "    python -m venv .venv && source .venv/bin/activate\n"
             "    pip install -r requirements.txt")

AQUI = Path(__file__).resolve().parent
load_dotenv(AQUI / ".env")   # el .env de ESTA carpeta, se corra desde donde se corra

PROMPT = "asistente-calendario"
TAG = "demo-s17"

CALENDARIO = {
    "taller 4": "El Taller 4 se entrega el sábado 17 de octubre de 2026, la última sesión, y vale el 25 % de la nota.",
    "sesion 18": "La sesión 18, el miércoles 7 de octubre, trata guardrails, costo y latencia.",
    "sesion 19": "La sesión 19, el jueves 8 de octubre, trata ajuste fino ligero y cierra el curso.",
    "langfuse": "En el Taller 4 las trazas se instrumentan con Langfuse y se exportan a JSONL.",
}

# (pregunta, dato que la respuesta tiene que contener). La última no está en la tabla: el
# buscador manda la tabla ENTERA como contexto, y eso se va a ver en los tokens de la traza.
PREGUNTAS = [
    ("¿Cuándo se entrega el Taller 4?", "17 de octubre"),
    ("¿De qué trata la sesión 18?", "guardrails"),
    ("¿Qué día es la sesión 19?", "8 de octubre"),
    ("¿Con qué herramienta se trazan los agentes del taller?", "Langfuse"),
    ("¿Cuál es la capital de Mongolia?", "No lo sé"),
]

PROMPT_V1 = ("Eres el asistente del curso MMIA 6013. Responde en una frase usando este "
             "contexto:\n{{contexto}}")
PROMPT_V2 = ("Eres el asistente del curso MMIA 6013. Responde en una frase, en español, usando "
             "SOLO este contexto. Si el contexto no contiene la respuesta, responde exactamente "
             "«No lo sé».\nContexto:\n{{contexto}}")

CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def enmascarar(*, data, **_):
    """Corre en esta máquina ANTES de enviar nada. Recorre tuplas: @observe guarda los
    argumentos de la función como {"args": (…), "kwargs": {…}}, y una máscara que solo mira
    listas deja pasar el correo sin avisar."""
    if isinstance(data, str):
        return CORREO.sub("<CORREO>", data)
    if isinstance(data, dict):
        return {k: enmascarar(data=v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [enmascarar(data=v) for v in data]
    return data


# --------------------------------------------------------------------------- los dos clientes
def _falta(variables: list[str], para: str, ejemplo: str) -> None:
    sys.exit(f"Falta {', '.join(variables)} en {AQUI / '.env'} ({para}). Añade, por ejemplo:\n"
             f"{ejemplo}\n(la plantilla completa está en .env.example)")


_lf = None


def lf():
    """Langfuse, configurado una vez con la máscara; get_client() y @observe lo reutilizan."""
    global _lf
    if _lf is None:
        faltan = [v for v in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")
                  if not os.getenv(v)]
        if faltan:
            _falta(faltan, "Langfuse",
                   "    LANGFUSE_PUBLIC_KEY=pk-lf-...   (Settings → API Keys, o ./levantar_langfuse.sh)\n"
                   "    LANGFUSE_SECRET_KEY=sk-lf-...\n    LANGFUSE_BASE_URL=http://localhost:3000")
        Langfuse(mask=enmascarar)
        _lf = get_client()
        if not _lf.auth_check():
            sys.exit(f"Langfuse en {os.getenv('LANGFUSE_BASE_URL')} no responde o las claves no son de "
                     "ese servidor. ¿Está levantado (./levantar_langfuse.sh) y las claves son del "
                     "proyecto que creaste?")
    return _lf


_llm: dict = {}


def llm(trazado: bool = True):
    """El cliente del modelo. trazado=False es el OpenAI de siempre, para el paso 1."""
    if trazado not in _llm:
        # OPENAI_BASE_URL puede faltar solo con la clave real de OpenAI (y entonces conviene
        # fijar MODELO con el id de su fila de la tabla semestral).
        if not os.getenv("OPENAI_API_KEY"):
            _falta(["OPENAI_API_KEY"] + ([] if os.getenv("OPENAI_BASE_URL") else ["OPENAI_BASE_URL"]),
                   "el modelo",
                   "    OPENAI_BASE_URL=http://<host de la H200>:12555/v1   (con la VPN)\n"
                   "    OPENAI_API_KEY=<la del laboratorio>\n"
                   "  o, sin VPN, con Ollama: OPENAI_BASE_URL=http://localhost:11434/v1 y OPENAI_API_KEY=ollama")
        clase = OpenAI if trazado else openai.OpenAI
        _llm[trazado] = clase(timeout=120, max_retries=1)
    return _llm[trazado]


_modelo = None


def modelo() -> str:
    """El id se le pregunta al servidor —nunca se escribe a mano—, salvo que MODELO lo fije."""
    global _modelo
    if _modelo:
        return _modelo
    _modelo = os.getenv("MODELO")
    if not _modelo:
        try:
            ids = [m.id for m in llm(False).models.list().data]
        except openai.APIConnectionError:
            sys.exit(f"No hay conexión con el modelo en {os.getenv('OPENAI_BASE_URL')}. "
                     "¿VPN conectada (H200)? ¿Ollama corriendo?")
        chat = [i for i in ids if not re.search(r"embed|bge|nomic|rerank", i, re.I)]
        if not chat:
            sys.exit(f"El servidor solo sirve modelos de embeddings ({ids}). Fija uno de chat con MODELO= en .env")
        _modelo = chat[0]
    print(f"[modelo: {_modelo}]")
    return _modelo


def completar(cliente, **kw):
    """Una llamada que se adapta a los parámetros del modelo. Los de razonamiento rechazan
    `temperature` y piden `max_completion_tokens` en vez de `max_tokens`: se reintenta sin
    lo que el servidor dijo que no admite, en vez de caerse."""
    for _ in range(3):
        try:
            return cliente.chat.completions.create(**kw)
        except openai.BadRequestError as err:
            texto = str(err).lower()
            if "temperature" in texto and "temperature" in kw:
                kw.pop("temperature")
            elif "max_tokens" in texto and "max_tokens" in kw:
                kw["max_completion_tokens"] = kw.pop("max_tokens")
            else:
                raise
    return cliente.chat.completions.create(**kw)


def url(ruta: str) -> str:
    """La URL de una página del proyecto, con el id real (en la nube no es «demo-s17»)."""
    try:
        pid = lf().api.projects.get().data[0].id
    except Exception:
        return os.getenv("LANGFUSE_BASE_URL", "")
    return f"{os.getenv('LANGFUSE_BASE_URL', '').rstrip('/')}/project/{pid}/{ruta}"


# --------------------------------------------------------------------------- el asistente
def _buscar(pregunta: str) -> str:
    p = unicodedata.normalize("NFKD", pregunta.lower())
    p = "".join(c for c in p if not unicodedata.combining(c))
    filas = [texto for clave, texto in CALENDARIO.items() if clave in p]
    if not filas and "herramienta" in p:
        filas = [CALENDARIO["langfuse"]]
    return "\n".join(filas or CALENDARIO.values())  # sin coincidencia: la tabla entera


buscar = observe(name="buscar_contexto", as_type="retriever")(_buscar)


@observe(name="responder")  # la función raíz: su llamada ES la traza
def responder(pregunta: str, prompt, esperado: str | None = None) -> str:
    contexto = buscar(pregunta)
    r = completar(
        llm(), model=modelo(), name="redactar",
        langfuse_prompt=prompt,  # liga esta generation a la versión exacta del prompt
        messages=[{"role": "system", "content": prompt.compile(contexto=contexto)},
                  {"role": "user", "content": pregunta}],
        temperature=0, max_tokens=2048)
    texto = (r.choices[0].message.content or "").strip()
    if esperado is not None:  # verificación determinística: ¿está el dato?
        lf().score_current_trace(name="contiene_dato", value=float(esperado in texto),
                                 data_type="NUMERIC", comment=f"esperado: {esperado}")
    return texto


# --------------------------------------------------------------------------- los pasos
def sin_trazas() -> None:
    for pregunta, _ in PREGUNTAS:
        r = completar(llm(False), model=modelo(), temperature=0, max_tokens=2048,
                      messages=[{"role": "system", "content": PROMPT_V1.replace("{{contexto}}", _buscar(pregunta))},
                                {"role": "user", "content": pregunta}])
        print(f"- {pregunta}\n  {(r.choices[0].message.content or '').strip()}")
    print("\n¿Cuál tardó más? ¿Cuántos tokens gastó cada una? ¿Con qué prompt? ¿Cuál falló?"
          "\nCon esto no se puede responder ninguna.")


def _versiones() -> list:
    """Las versiones del prompt que ya existen en Langfuse (vacía si no hay ninguna)."""
    try:
        metas = lf().api.prompts.list(name=PROMPT).data
    except Exception:
        return []
    return sorted(v for m in metas if m.name == PROMPT for v in (m.versions or []))


def registrar_prompts(forzar: bool = False) -> None:
    if _versiones() and not forzar:
        print(f"El prompt «{PROMPT}» ya está registrado: no se crean versiones repetidas "
              f"(«prompts --forzar» las crea igual).\nMíralo en {url('prompts/' + PROMPT)}")
        return
    lf().create_prompt(name=PROMPT, type="text", prompt=PROMPT_V1, labels=["production"],
                       commit_message="v1: una frase con el contexto")
    lf().create_prompt(name=PROMPT, type="text", prompt=PROMPT_V2, labels=["candidata"],
                       commit_message="v2: solo el contexto; «No lo sé» si no está")
    print(f"Prompt «{PROMPT}» registrado: v1 → production, v2 → candidata.\n"
          f"Míralo en {url('prompts/' + PROMPT)}")


def trazar(label: str | None = None, version: int | None = None) -> None:
    if not _versiones():
        print("El prompt aún no estaba registrado: lo registro primero (paso 2).")
        registrar_prompts()
    try:
        prompt = (lf().get_prompt(PROMPT, version=version, cache_ttl_seconds=0) if version else
                  lf().get_prompt(PROMPT, label=label or "production", cache_ttl_seconds=0))
    except Exception:
        sys.exit(f"No existe la {'versión ' + str(version) if version else 'etiqueta ' + str(label)} "
                 f"del prompt «{PROMPT}». Mira las que hay en {url('prompts/' + PROMPT)}")
    etiqueta = label or f"v{prompt.version}"
    print(f"Prompt «{PROMPT}» versión {prompt.version} ({etiqueta})")
    with propagate_attributes(session_id=f"demo-{etiqueta}", tags=[TAG],
                              metadata={"prompt_version": f"v{prompt.version}"}):
        for pregunta, esperado in PREGUNTAS:
            t0 = time.perf_counter()
            texto = responder(pregunta, prompt, esperado)
            print(f"- {pregunta}  ({time.perf_counter() - t0:.1f} s)\n  {texto}")
    lf().flush()  # un script corto termina antes de que el envío en segundo plano acabe
    print(f"\nTrazas (tardan unos segundos en aparecer): {url('traces')}")


def promover(version: int) -> None:
    if not _versiones():
        registrar_prompts()
    try:
        lf().update_prompt(name=PROMPT, version=version, new_labels=["production"])
    except Exception as err:
        sys.exit(f"No pude mover production a la v{version} ({type(err).__name__}). "
                 f"¿Existe esa versión? Míralo en {url('prompts/' + PROMPT)}")
    print(f"production → v{version}. La aplicación no se redespliega: la próxima "
          "get_prompt() (al vencer la caché del SDK) ya trae la nueva.")


@observe(name="consultar_calendario_remoto", as_type="tool")
def consultar_remoto(pregunta: str) -> str:
    raise TimeoutError("el calendario remoto no respondió en 2 s")


@observe(name="responder_con_herramienta")
def con_herramienta(pregunta: str) -> str:
    try:
        return consultar_remoto(pregunta)
    except TimeoutError:
        # La corrida NO falla: devuelve un texto razonable y HTTP 200. Sin la traza, este
        # fallo no aparece en ningún log de errores.
        return "Ahora mismo no puedo consultar el calendario; intenta en un minuto."


def falla() -> None:
    lf()
    with propagate_attributes(session_id="demo-falla", tags=[TAG]):
        print(con_herramienta("Soy ana.perez@usfq.edu.ec: ¿cuándo es mi examen?"))
    lf().flush()
    print("En la traza: la herramienta en nivel ERROR con su mensaje, y el correo como <CORREO>.\n"
          f"{url('traces')}")


# --------------------------------------------------------------------------- la línea de órdenes
PASOS = {  # número o nombre → (función, descripción)
    "1": "sin-trazas", "2": "prompts", "3": "trazas", "4": "candidata", "5": "promover", "6": "falla",
}
ALIAS = {"sintrazas": "sin-trazas", "sin": "sin-trazas", "prompt": "prompts", "registrar": "prompts",
         "traza": "trazas", "v2": "candidata", "promocionar": "promover", "rollback": "promover",
         "error": "falla", "fallo": "falla"}
MENU = """Pasos de la demo (número o nombre):
  1  sin-trazas   el problema: respuestas y ningún dato              (solo necesita el modelo)
  2  prompts      registra el prompt en Langfuse: v1 → production, v2 → candidata
  3  trazas       las cinco preguntas, trazadas, con la versión en production
  4  candidata    las mismas con la v2       (= «trazas candidata», «trazas v2», «trazas 2»)
  5  promover     production pasa a la v2    («promover 1» es el rollback)
  6  falla        una herramienta que falla y un correo enmascarado

Ejemplo: python demo.py 1     ·     python demo.py trazas candidata"""


def _paso(texto: str) -> str | None:
    t = unicodedata.normalize("NFKD", texto.strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c)).replace("_", "-").replace(" ", "-")
    t = PASOS.get(t, t)
    t = ALIAS.get(t.replace("-", ""), ALIAS.get(t, t))
    return t if t in PASOS.values() else None


def _version(texto: str | None) -> int | None:
    m = re.fullmatch(r"v?(\d+)", (texto or "").strip().lower())
    return int(m.group(1)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser(description=MENU, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 usage="python demo.py [paso] [etiqueta o versión]")
    ap.add_argument("paso", nargs="?")
    ap.add_argument("extra", nargs="?", help="trazas: candidata | production | v2 · promover: 2 | v1")
    ap.add_argument("--label", "--etiqueta", dest="label")
    ap.add_argument("--version", type=_version)
    ap.add_argument("--forzar", action="store_true", help="prompts: crea versiones aunque ya existan")
    a = ap.parse_args()
    if not a.paso:
        print(MENU)
        return
    paso = _paso(a.paso)
    if paso is None:
        sys.exit(f"No conozco el paso «{a.paso}».\n\n{MENU}")

    if paso == "sin-trazas":
        sin_trazas()
    elif paso == "prompts":
        registrar_prompts(a.forzar)
    elif paso in ("trazas", "candidata"):
        version = a.version or _version(a.extra)
        label = a.label or ("candidata" if paso == "candidata" else
                            None if version else (a.extra or "production"))
        if version == 2 and not a.version and not a.label:      # «trazas 2» = la candidata
            version, label = None, "candidata"
        trazar(label, version)
    elif paso == "promover":
        promover(a.version or _version(a.extra) or 2)
    elif paso == "falla":
        falla()
    if _lf is not None:
        _lf.flush()


if __name__ == "__main__":
    main()
