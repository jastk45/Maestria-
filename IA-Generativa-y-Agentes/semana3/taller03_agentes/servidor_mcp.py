"""Taller 03 · Parte 4.B — Las herramientas detrás de un servidor MCP, y un agente que pregunta.

    python evaluar.py --golden golden_set.json --agente servidor_mcp:MiAgenteMCP
    python parte4_mcp.py          # prueba: una herramienta nueva sin tocar el agente

Forma de la sesión 13 (tools/list, tools/call, isError); no hay transporte: el servidor es un
objeto en el mismo proceso, como en el cuaderno del miércoles. El agente es MiAgente con dos
métodos cambiados: de dónde sale el catálogo y quién ejecuta. El bucle y los frenos no cambian.
"""
from __future__ import annotations

from herramientas import CATALOGO, ErrorHerramienta, Herramientas
from mi_agente import MiAgente

# Registro de complementos: un módulo nuevo añade aquí su herramienta; ni el servidor base
# ni el agente se editan. Cada entrada: (name, description, inputSchema, fn(herr, **args)).
EXTRAS: list[tuple] = []


class ServidorMCP:
    def __init__(self, nombre: str):
        self.nombre, self._impl, self._catalogo = nombre, {}, []

    def publicar(self, name, description, input_schema, fn):
        self._catalogo.append({"name": name, "description": description, "inputSchema": input_schema})
        self._impl[name] = fn

    def manejar(self, metodo: str, params: dict | None = None) -> dict:
        params = params or {}
        if metodo == "tools/list":
            return {"tools": list(self._catalogo)}
        if metodo == "tools/call":
            fn = self._impl.get(params.get("name"))
            if fn is None:
                return {"isError": True, "content": f"herramienta desconocida: {params.get('name')}"}
            try:
                return {"isError": False, "content": fn(**params.get("arguments", {}))}
            except ErrorHerramienta as e:
                return {"isError": True, "content": str(e)}
        return {"isError": True, "content": f"método no soportado: {metodo}"}


def servidor_analitico(herr: Herramientas) -> ServidorMCP:
    s = ServidorMCP("analitica-ventas")
    for t in CATALOGO:
        s.publicar(t["name"], t["description"], t["parameters"], getattr(herr, t["name"]))
    for name, desc, schema, fn in EXTRAS:
        s.publicar(name, desc, schema, lambda _fn=fn, **a: _fn(herr, **a))
    return s


class ClienteMCP:
    def __init__(self, servidor: ServidorMCP):
        self.servidor, self.catalogo = servidor, []

    def descubrir(self) -> list[str]:
        self.catalogo = self.servidor.manejar("tools/list")["tools"]
        return [t["name"] for t in self.catalogo]

    def para_openai(self) -> list[dict]:
        """El adaptador vive en el cliente: inputSchema (MCP) -> parameters (API del modelo)."""
        return [{"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}
                for t in self.catalogo]

    def invocar(self, nombre: str, argumentos: dict):
        r = self.servidor.manejar("tools/call", {"name": nombre, "arguments": argumentos})
        if r["isError"]:
            raise ErrorHerramienta(r["content"])
        return r["content"]


class MiAgenteMCP(MiAgente):
    _para = None   # la corrida (Herramientas) para la que se descubrió el catálogo

    def _cliente(self) -> ClienteMCP:
        if self._para is not self.herr:     # una sesión por corrida: el almacén de resultados es suyo
            self._c = ClienteMCP(servidor_analitico(self.herr))
            self._c.descubrir()
            self._para = self.herr
        return self._c

    def catalogo(self) -> list[dict]:
        return self._cliente().para_openai()

    def ejecutar(self, nombre: str, args: dict):
        return self._cliente().invocar(nombre, args)
