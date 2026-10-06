"""Taller 03 · Parte 4.B — Prueba: añadir una herramienta sin tocar el código del agente.

    python parte4_mcp.py

Se importa `herramienta_nueva.py`, que solo se registra en servidor_mcp.EXTRAS. MiAgenteMCP
la descubre en tools/list y el modelo la usa. mi_agente.py y la clase MiAgenteMCP no cambian.
"""
import json

from servidor_mcp import ClienteMCP, MiAgenteMCP, servidor_analitico
from herramientas import Herramientas

PREGUNTA = "¿Cuál es el percentil 90 del importe por venta en 2025?"

antes = ClienteMCP(servidor_analitico(Herramientas())).descubrir()
import herramienta_nueva  # noqa: E402,F401 — el único cambio: un módulo nuevo
despues = ClienteMCP(servidor_analitico(Herramientas())).descubrir()
print("tools/list antes  :", antes)
print("tools/list después:", despues)

r = MiAgenteMCP().run(PREGUNTA)
usadas = [p["action"]["name"] for p in r["trace"] if p.get("action")]
print("herramientas usadas:", usadas)
print("respuesta:", r["answer"][:300])
print("tokens:", json.dumps(r["usage"]))
