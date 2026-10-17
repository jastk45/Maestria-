"""Taller 04 · Parte 3 — Los guardrails del agente (opción A), medidos como clasificadores.

    python probar_guardrails.py --entrada mis_guardrails:validar_entrada \
           --salida mis_guardrails:validar_salida --casos ataques.json --csv guardrails_mios.csv

Contrato de probar_guardrails.py: `f(texto) -> (ok, texto_resultante)`. ok=False bloquea; ok=True
con otro texto redacta; ok=True con el mismo texto deja pasar. El agente (agente_llmops.py) no
usa las dos funciones compuestas: llama a cada guardrail por separado para dejar un span
`guardrail` por validación, con su decisión (ok | redactada | bloqueada).

    G1 inyección (entrada)   bloquea   texto normalizado (minúsculas, sin tildes, sin signos) y por
                                       INTENCIÓN: un verbo de la familia + su objeto, cerca; no frases
    G2 datos personales      redacta   correo, cédula/RUC y teléfono de Ecuador, con su estructura,
       (entrada, salida, traza)        sin tomar fechas ni números del dominio; la traza, con la
                                       máscara de Langfuse (enmascarar) y en la traza que devuelve run()
    G3 claves (salida)       bloquea   por su FORMA (prefijos sk-, pk-lf-, AKIA, ghp_, JWT, PEM,
                                       «api_key=…»), no por su longitud: un hash o un UUID pasan
    G4 longitud (entrada)    bloquea   más de MAX_CHARS_ENTRADA caracteres

Un bloqueo devuelve la frase de abstención del Taller 3 y el motivo: para el evaluador, una
pregunta bloqueada es una abstención, y lo es.

Lo que se escapa (y se reporta): nombres de personas (no hay modelo de entidades: «Soy Ana
Pérez» pasa), ataques ofuscados (separados letra a letra, leetspeak, otro idioma que no sea
español o inglés, instrucciones repartidas en varios turnos) y teléfonos o documentos de otros
países.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

ABSTENCION = "No puedo responder con los datos disponibles."  # la frase del Taller 3 (evaluar.py)

# G4 — sacado de las mediciones: la pregunta no adversarial más larga del golden set tiene 162
# caracteres (CL1); el límite deja más de 9× de margen y corta el relleno masivo de contexto.
MAX_CHARS_ENTRADA = 1500

OK, REDACTADA, BLOQUEADA = "ok", "redactada", "bloqueada"


@dataclass
class Decision:
    guardrail: str                 # inyeccion_entrada, pii_entrada, ...
    decision: str                  # ok | redactada | bloqueada
    texto: str                     # el texto que sigue (redactado) o el mensaje de bloqueo
    motivo: str = ""
    hallazgos: list[str] = field(default_factory=list)   # tipos, nunca los valores


# ─────────────────────────────────────────────────────────────── normalización (G1)
def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, signos → espacio, espacios colapsados: «Actúa» = «actua»."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^\w\s.\-]", " ", t)          # ¿ ? ¡ ! , ; : " ' ( ) → espacio; quedan . - _
    return re.sub(r"\s+", " ", t).strip()


def _cerca(verbo: str, objeto: str, n: int = 6) -> re.Pattern:
    """El verbo y su objeto a lo sumo a n palabras: la intención, no la frase exacta."""
    return re.compile(rf"\b(?:{verbo})(?:\W+\w+){{0,{n}}}?\W+(?:{objeto})")


# ─────────────────────────────────────────────────────────────── G1 · inyección
_ANULAR = (r"ignor\w*|olvid\w*|omit\w*|descart\w*|desobedec\w*|salta\w*|pasa por alto|"
           r"no (?:sigas|obedezcas|cumplas|respetes|apliques)|deja de (?:seguir|obedecer|cumplir|aplicar)|"
           r"forget|disregard|override|bypass|skip")
_REGLAS = (r"instrucc\w*|regla\w*|indicacion\w*|restricc\w*|normas?\b|directri\w*|politica\w*|"
           r"prompt|mensaje del sistema|configuracion|limitacion\w*|instructions?|rules?|"
           r"guidelines?|guardrails?|system message")
_ROL = (r"actu\w*|comport\w*|fing\w*|pretend\w*|haz de cuenta|imagina que|eres|seras|"
        r"conviertete|you are|act as|be an?|roleplay|modo")
_SIN_LIMITES = (r"sin (?:restricciones|reglas|limites|filtros|censura|limitaciones|politicas)|"
                r"no (?:tuvieras|tienes|tengas|hubiera) (?:restricciones|reglas|limites|filtros)|"
                r"libre de (?:restricciones|reglas)|unrestricted|without (?:restrictions|rules|limits|filters)|"
                r"no (?:restrictions|rules|limits)|jailbreak|developer mode|modo (?:desarrollador|dios|libre)|\bdan\b")
_EXTRAER = (r"revel\w*|muestr\w*|ensen\w*|imprim\w*|dime|di\b|escrib\w*|copi\w*|repit\w*|repet\w*|"
            r"traduc\w*|resum\w*|list\w*|enumer\w*|cuent\w*|compart\w*|reproduc\w*|vuelca|"
            r"reveal|show|print|repeat|translate|tell|output|dump|list|share|summari[sz]e")
_INTERNO = (r"(?:prompt|mensaje) del sistema|system prompt|(?:tus|sus|las) (?:instrucciones|reglas|"
            r"indicaciones|directrices|politicas)(?: internas| ocultas| iniciales| originales| previas)?|"
            r"(?:instrucciones|reglas|indicaciones|configuracion) (?:internas?|ocultas?|iniciales|originales|previas)|"
            r"lo que (?:te dijeron|recibiste|te indicaron) antes|your (?:instructions|rules|system prompt|prompt)|"
            r"(?:hidden|initial|original|previous) (?:instructions|prompt|rules)")
_PEDIR = (r"dame|da\b|revel\w*|muestr\w*|imprim\w*|dime|escrib\w*|envi\w*|compart\w*|pasa\w*|"
          r"entreg\w*|filtr\w*|exp[o0]n\w*|give|show|reveal|print|send|tell|leak|expose|share")
_CREDENCIAL = (r"clave(?:s)? (?:de (?:la |el )?)?(?:api|acceso|openai|anthropic|langfuse|servidor)|"
               r"cualquier clave|claves? (?:disponibles?|secretas?|privadas?)|api[ _-]?keys?|"
               r"contrasen\w*|password\w*|passwd|(?:el|tu|su|un|tus|sus) tokens?\b|"
               r"(?:access )?tokens? de (?:acceso|autenticacion|la api)|credencial\w*|secret\w*|"
               r"variables? de entorno|\.env\b|private key|clave privada|access key")

INTENCIONES = {
    "anular las instrucciones": _cerca(_ANULAR, _REGLAS, 5),
    "rol sin restricciones": _cerca(_ROL, _SIN_LIMITES, 7),
    "extraer las instrucciones internas": _cerca(_EXTRAER, _INTERNO, 6),
    "pedir credenciales": _cerca(_PEDIR, _CREDENCIAL, 6),
}


def detectar_inyeccion(texto: str) -> Decision:
    t = normalizar(texto)
    hallazgos = [nombre for nombre, patron in INTENCIONES.items() if patron.search(t)]
    if hallazgos:
        motivo = "posible inyección de instrucciones (" + ", ".join(hallazgos) + ")"
        return Decision("inyeccion_entrada", BLOQUEADA,
                        f"{ABSTENCION} La pregunta se bloqueó por el guardrail de entrada: {motivo}.",
                        motivo, hallazgos)
    return Decision("inyeccion_entrada", OK, texto)


# ─────────────────────────────────────────────────────────────── G2 · datos personales
CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Ecuador: celular 09 + 8 dígitos (o +593 9 + 8), con espacios, puntos o guiones opcionales
CELULAR = re.compile(r"(?<![\w+])(?:\+?593[\s.-]?|0)9\d(?:[\s.-]?\d){7}(?![\d])")
# Ecuador: fijo 0[2-7] + 7 dígitos, «(02) 234-5678», «02 234 5678», «+593 2 234 5678»
FIJO = re.compile(r"(?<![\w+])(?:\+?593[\s.-]?|\(?0)[2-7]\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\d])")
DIEZ_DIGITOS = re.compile(r"(?<![\d.,])(\d{10})(001)?(?![\d.,])")
CONTEXTO_DOC = re.compile(r"\b(?:cedula|c\.\s?i\.?|ci|identificacion|documento|ruc|pasaporte)\b"
                          r"(?:\W+\w+){0,3}\W*$")


def _cedula_valida(d: str) -> bool:
    """Dígito verificador (módulo 10) de la cédula ecuatoriana de persona natural."""
    if not (d.isdigit() and len(d) == 10):
        return False
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    s = sum((x if x < 10 else x - 9) for x in (int(a) * c for a, c in zip(d[:9], coef)))
    return (10 - s % 10) % 10 == int(d[9])


def _parece_documento(d: str, antes: str) -> bool:
    """10 dígitos son una cédula si tienen su estructura —provincia 01-24 o 30 y tercer dígito
    0-5— o un dígito verificador válido, o si el texto acaba de decir «cédula», «RUC»…
    Un número de diez dígitos sin esa forma (p. ej. 0012345678) no se toca."""
    provincia, tercero = int(d[:2]), int(d[2])
    estructura = (1 <= provincia <= 24 or provincia == 30) and tercero <= 5
    return estructura or _cedula_valida(d) or bool(CONTEXTO_DOC.search(normalizar(antes)[-40:]))


def redactar_pii(texto: str) -> tuple[str, list[str]]:
    """El texto sin correo, cédula/RUC ni teléfono, y los TIPOS encontrados (nunca los valores)."""
    hallazgos: list[str] = []

    def sub(patron, etiqueta, t):
        def _r(m):
            hallazgos.append(etiqueta.strip("[]").lower())
            return etiqueta
        return patron.sub(_r, t)

    t = sub(CORREO, "[CORREO]", texto or "")
    t = sub(CELULAR, "[TELEFONO]", t)
    t = sub(FIJO, "[TELEFONO]", t)

    def _doc(m):
        antes = t[:m.start()]
        if m.group(2) or _parece_documento(m.group(1), antes):
            hallazgos.append("ruc" if m.group(2) else "cedula")
            return "[RUC]" if m.group(2) else "[CEDULA]"
        return m.group(0)
    t = DIEZ_DIGITOS.sub(_doc, t)
    return t, hallazgos


def pii(texto: str, canal: str) -> Decision:
    redactado, hallazgos = redactar_pii(texto)
    if hallazgos:
        return Decision(f"pii_{canal}", REDACTADA, redactado,
                        "datos personales redactados: " + ", ".join(sorted(set(hallazgos))),
                        sorted(set(hallazgos)))
    return Decision(f"pii_{canal}", OK, texto)


# ─────────────────────────────────────────────────────────────── G3 · claves por su forma
CLAVES = {
    "openai/anthropic (sk-)": re.compile(r"\bsk-(?:proj-|ant-|svcacct-|admin-|live-|test-)?[A-Za-z0-9_-]{16,}"),
    "langfuse (pk-lf-/sk-lf-)": re.compile(r"\b[ps]k-lf-[A-Za-z0-9-]{16,}"),
    "aws (AKIA/ASIA)": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github (ghp_/github_pat_)": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "google (AIza)": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "slack (xox)": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "jwt (eyJ…)": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "clave privada (PEM)": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}"),
    "asignación de secreto": re.compile(r"(?i)\b(?:api[_-]?key|secret(?:[_-]?key)?|password|passwd|"
                                        r"contrase(?:ñ|n)a|access[_-]?token|auth[_-]?token)\s*[:=]\s*"
                                        r"['\"]?[^\s'\"]{8,}"),
}


def buscar_claves(texto: str) -> list[str]:
    return [nombre for nombre, patron in CLAVES.items() if patron.search(texto or "")]


def redactar_claves(texto: str) -> str:
    for patron in CLAVES.values():
        texto = patron.sub("[CLAVE]", texto)
    return texto


def claves_salida(texto: str) -> Decision:
    tipos = buscar_claves(texto)
    if tipos:
        motivo = "la respuesta contenía una credencial (" + ", ".join(tipos) + ")"
        return Decision("claves_salida", BLOQUEADA,
                        f"{ABSTENCION} La respuesta se bloqueó por el guardrail de salida: {motivo}.",
                        motivo, tipos)
    return Decision("claves_salida", OK, texto)


# ─────────────────────────────────────────────────────────────── G4 · longitud
def longitud_entrada(texto: str) -> Decision:
    n = len(texto or "")
    if n > MAX_CHARS_ENTRADA:
        motivo = f"la pregunta tiene {n} caracteres; el límite es {MAX_CHARS_ENTRADA}"
        return Decision("longitud_entrada", BLOQUEADA,
                        f"{ABSTENCION} La pregunta se bloqueó por el guardrail de entrada: {motivo}.",
                        motivo, ["longitud"])
    return Decision("longitud_entrada", OK, texto)


# ─────────────────────────────────────────────────────────────── en orden, por canal
# (nombre del span, función). El más barato primero; el primero que bloquea corta la cadena.
ENTRADA = [("longitud_entrada", longitud_entrada),
           ("inyeccion_entrada", detectar_inyeccion),
           ("pii_entrada", lambda t: pii(t, "entrada"))]
SALIDA = [("claves_salida", claves_salida),
          ("pii_salida", lambda t: pii(t, "salida"))]


def cadena(texto: str, guardias) -> tuple[bool, str, list[Decision]]:
    decisiones = []
    for _, g in guardias:
        d = g(texto)
        decisiones.append(d)
        if d.decision == BLOQUEADA:
            return False, d.texto, decisiones
        texto = d.texto
    return True, texto, decisiones


def validar_entrada(texto: str) -> tuple[bool, str]:
    ok, resultado, _ = cadena(texto, ENTRADA)
    return ok, resultado


def validar_salida(texto: str) -> tuple[bool, str]:
    ok, resultado, _ = cadena(texto, SALIDA)
    return ok, resultado


# ─────────────────────────────────────────────────────────────── G2 en la traza: la máscara
def redactar_texto(texto: str) -> str:
    """Lo que nunca llega a una traza: datos personales y claves."""
    return redactar_claves(redactar_pii(texto)[0])


def enmascarar(*, data, **_):
    """La máscara de Langfuse(mask=...): corre en esta máquina antes de enviar nada. Recorre
    tuplas además de listas y diccionarios: @observe guarda los argumentos como
    {"args": (…), "kwargs": {…}} y una máscara que solo mira listas deja pasar el dato."""
    if isinstance(data, str):
        return redactar_texto(data)
    if isinstance(data, dict):
        return {k: enmascarar(data=v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [enmascarar(data=v) for v in data]
    return data
