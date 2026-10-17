"""Taller 04 — El agente del Taller 3 (opción A), observable con Langfuse y protegido con guardrails.

    python agente_llmops.py "¿Cuál fue el importe total vendido en marzo de 2026?"
    SESION_LANGFUSE=jaime-astudillo-base python evaluar_llmops.py --golden golden_set.json \
        --agente agente_llmops:AgenteLLMOps --juez gemma3 --salida resultados_base.csv

Contrato del Taller 3: `AgenteLLMOps().run(pregunta)` devuelve answer, trace, status, model y
usage, y además prompt_version, traza_id y guardrail {"entrada", "salida"} (evaluar_llmops.py
los lleva al CSV). El bucle, las herramientas y los frenos son los de mi_agente.py.

Cuatro tipos de span bajo UNA raíz por corrida (exportar_trazas.py los traduce):

    corrida      la raíz (@observe): la pregunta (enmascarada), su status y su prompt_version
    guardrail    cada validación, con su decisión (ok | redactada | bloqueada) como output
    llm          cada llamada al modelo: generation de langfuse.openai, con modelo, tokens y
                 latencia, ligada a la versión del prompt de Langfuse (langfuse_prompt=...)
    herramienta  cada uso: nombre, tamaño del resultado, latencia y error (nivel ERROR)

Los hijos cuelgan directamente de la raíz, sin spans intermedios: así resumir_trazas.py no cuenta
dos veces el mismo tiempo.

Las tres correcciones de la Parte 0.c (instrumented_agent.py l. 47, 45 y 50-58):
    1. La raíz se cierra sola aunque la corrida falle: @observe la termina en un finally y guarda
       la excepción; si el agente devuelve status=error, la raíz queda en nivel ERROR con su
       mensaje, y los frenos en WARNING.
    2. La raíz envuelve los guardrails: su duración incluye la de las validaciones.
    3. Los datos personales se redactan antes del modelo (guardrail de entrada) y antes de
       escribir cualquier traza: Langfuse(mask=enmascarar), que recorre tuplas, la traza que
       devuelve run() y la traza local del Taller 3.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
LAB03 = AQUI.parent / "Lab-03-Agentes"
load_dotenv(AQUI / ".env")
os.environ.setdefault("AGENT_DB_PATH", str(LAB03 / "data" / "database.sqlite"))
sys.path.append(str(LAB03))                     # mi_agente, herramientas y evaluar del Taller 3

from langfuse import Langfuse, get_client, observe, propagate_attributes  # noqa: E402
from langfuse.openai import OpenAI  # noqa: E402  — el cliente de OpenAI, con una generation por llamada

import mis_guardrails as G  # noqa: E402
from mi_agente import ABSTENCION, MiAgente  # noqa: E402
from prompts_agente import NOMBRE as PROMPT_NOMBRE  # noqa: E402

Langfuse(mask=G.enmascarar)       # una vez; get_client() y @observe reutilizan este cliente
if not get_client().auth_check():
    raise SystemExit("Langfuse no responde o las claves no valen: revisa LANGFUSE_* en .env "
                     "(¿está levantado? langfuse/levantar_langfuse.sh).")

FRENOS = {"budget_exceeded", "max_steps_reached", "repetition_detected"}
_MODELO: dict = {}                # el id que sirve el endpoint, una vez por proceso


def _modelo_del_servidor(cliente) -> str:
    """AGENT_MODEL o, si está vacío, lo que sirve /v1/models: el id no se escribe de memoria."""
    if "id" not in _MODELO:
        _MODELO["id"] = os.getenv("AGENT_MODEL") or cliente.models.list().data[0].id
    return _MODELO["id"]


def _prompt():
    """La versión del prompt que se usa: PROMPT_VERSION (número) o PROMPT_LABEL (production)."""
    version = os.getenv("PROMPT_VERSION")
    lf = get_client()
    if version:
        return lf.get_prompt(PROMPT_NOMBRE, version=int(version.lstrip("v")), cache_ttl_seconds=300)
    return lf.get_prompt(PROMPT_NOMBRE, label=os.getenv("PROMPT_LABEL", "production"),
                         cache_ttl_seconds=300)


def _tamano(obs) -> int:
    return len(json.dumps(obs, ensure_ascii=False, default=str))


class AgenteLLMOps(MiAgente):
    def __init__(self):
        super().__init__()
        self.client = OpenAI()                      # langfuse.openai
        self.model = _modelo_del_servidor(self.client)
        self.prompt_lf = _prompt()
        self.sistema = self.prompt_lf.prompt        # texto plano, sin variables
        self.prompt_version = f"v{self.prompt_lf.version}"
        self.sesion = os.getenv("SESION_LANGFUSE") or f"jaime-astudillo-{self.prompt_version}"
        # Cada generation lleva el modelo como nombre y queda ligada a su versión del prompt.
        self.kw_llm = {"name": self.model, "langfuse_prompt": self.prompt_lf}

    # ── la raíz ──────────────────────────────────────────────────────────────────────────
    def run(self, question: str) -> dict:
        try:
            return self._corrida(question)
        finally:
            get_client().flush()        # enviar ya: el proceso puede terminar en cualquier caso

    @observe(name="corrida", capture_input=False, capture_output=False)
    def _corrida(self, question: str) -> dict:
        lf = get_client()
        with propagate_attributes(session_id=self.sesion, tags=["taller-04", self.prompt_version],
                                  metadata={"prompt_version": self.prompt_version}):
            lf.update_current_span(input={"pregunta": question},
                                   metadata={"prompt_version": self.prompt_version,
                                             "prompt": f"{PROMPT_NOMBRE} v{self.prompt_lf.version}"})
            traza_id = lf.get_current_trace_id()
            guard = {"entrada": G.OK, "salida": G.OK}

            ok, texto, dec_e = self._guardias("entrada", question)
            guard["entrada"] = self._peor(dec_e)
            if not ok:                              # bloqueada: el modelo no la ve
                self.id_corrida = f"bloqueada-{traza_id[:8]}"
                res = {"question": G.redactar_texto(question), "answer": texto, "status": "blocked_input",
                       "trace": [{"paso": 0, "guardrail": d.guardrail, "decision": d.decision,
                                  "motivo": d.motivo, "action": None, "observation": None}
                                 for d in dec_e],
                       "model": self.model, "usage": {"tokens_entrada": 0, "tokens_salida": 0},
                       "error": None, "abstencion_por_codigo": False}
                self._guardar_traza(res)
            else:
                res = super().run(texto)            # el bucle del Taller 3, con la pregunta redactada
                ok_s, salida, dec_s = self._guardias("salida", res["answer"])
                guard["salida"] = self._peor(dec_s)
                res["answer"] = salida
                if not ok_s:
                    res["status"] = "blocked_output"

            # La traza que se devuelve tampoco lleva datos personales ni claves (Parte 0.c, 3).
            res["trace"] = G.enmascarar(data=res["trace"])
            res.update(prompt_version=self.prompt_version, traza_id=traza_id, guardrail=guard)
            nivel = ("ERROR" if res["status"] == "error" else
                     "WARNING" if res["status"] in FRENOS else None)
            lf.update_current_span(
                output={"status": res["status"], "answer": res["answer"]},
                metadata={"status": res["status"], "prompt_version": self.prompt_version,
                          "guardrail_entrada": guard["entrada"], "guardrail_salida": guard["salida"],
                          "tokens_entrada": res["usage"]["tokens_entrada"],
                          "tokens_salida": res["usage"]["tokens_salida"]},
                **({"level": nivel, "status_message": res.get("error") or res["status"]} if nivel else {}))
            return res

    # ── guardrails: un span por validación ───────────────────────────────────────────────
    def _guardias(self, canal: str, texto: str):
        lf, decisiones = get_client(), []
        for nombre, guardia in (G.ENTRADA if canal == "entrada" else G.SALIDA):
            with lf.start_as_current_observation(as_type="guardrail", name=nombre,
                                                 input={"canal": canal, "texto": texto}) as span:
                try:
                    d = guardia(texto)
                except Exception as e:  # noqa: BLE001 — un guardrail que revienta bloquea (falla cerrado)
                    d = G.Decision(nombre, G.BLOQUEADA,
                                   f"{ABSTENCION} No pude validar la {canal}.", f"{type(e).__name__}: {e}")
                    span.update(level="ERROR", status_message=d.motivo)
                span.update(output=d.decision, metadata={"motivo": d.motivo, "hallazgos": d.hallazgos})
            decisiones.append(d)
            if d.decision == G.BLOQUEADA:
                return False, d.texto, decisiones
            texto = d.texto
        return True, texto, decisiones

    @staticmethod
    def _peor(decisiones) -> str:
        orden = [G.OK, G.REDACTADA, G.BLOQUEADA]
        return max((d.decision for d in decisiones), key=orden.index, default=G.OK)

    # ── herramientas: un span tool por uso ───────────────────────────────────────────────
    def _herramienta(self, nombre: str, argumentos: str) -> dict:
        try:
            entrada = json.loads(argumentos or "{}")
        except json.JSONDecodeError:
            entrada = argumentos
        with get_client().start_as_current_observation(as_type="tool", name=nombre,
                                                       input=entrada) as span:
            obs = super()._herramienta(nombre, argumentos)
            meta = {"tamano_resultado_caracteres": _tamano(obs),
                    "filas": obs.get("total_filas") if isinstance(obs, dict) else None}
            if isinstance(obs, dict) and "error" in obs:
                span.update(output=obs, metadata=meta, level="ERROR", status_message=str(obs["error"])[:500])
            else:
                span.update(output=obs, metadata=meta)
        return obs

    # ── la traza local del Taller 3, enmascarada ─────────────────────────────────────────
    def _guardar_traza(self, res: dict) -> None:
        ruta = self.trace_dir / f"trace-{self.id_corrida}.json"
        ruta.write_text(json.dumps(G.enmascarar(data=res), indent=2, ensure_ascii=False, default=str),
                        encoding="utf-8")


if __name__ == "__main__":
    pregunta = " ".join(sys.argv[1:]) or "¿Cuál fue el importe total vendido en marzo de 2026?"
    r = AgenteLLMOps().run(pregunta)
    print(json.dumps({k: v for k, v in r.items() if k != "trace"}, indent=2, ensure_ascii=False, default=str))
