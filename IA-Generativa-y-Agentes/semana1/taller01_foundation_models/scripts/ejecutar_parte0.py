"""Ejecuta y guarda solo el setup y la Parte 0 del notebook del informe.

Uso: .venv/Scripts/python.exe scripts/ejecutar_parte0.py
Cada ejecución añade nueve generaciones al CSV crudo (no borra corridas).
"""

import os
import sys
import time
from pathlib import Path
from queue import Empty

import nbformat
from jupyter_client import KernelManager


def main():
    raiz = Path(__file__).resolve().parent.parent
    ruta = raiz / "taller-01-informe.ipynb"
    notebook = nbformat.read(ruta, as_version=4)
    runtime = raiz / ".jupyter_runtime"
    runtime.mkdir(exist_ok=True)
    entorno = {**os.environ, "JUPYTER_RUNTIME_DIR": str(runtime),
               "IPYTHONDIR": str(runtime / "ipython"), "MPLCONFIGDIR": str(runtime / "matplotlib"),
               "PYTHONUTF8": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1"}
    km = KernelManager(connection_file=str(runtime / "parte0-kernel.json"))
    km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    km.start_kernel(cwd=str(raiz), env=entorno)
    cliente = km.client()
    cliente.start_channels()
    try:
        cliente.wait_for_ready(timeout=60)
        for indice, celda in enumerate(notebook.cells):
            if 'id="parte-1"' in celda.source:
                break
            if celda.cell_type != "code":
                continue
            print(f"Ejecutando celda {indice}...", flush=True)
            celda.outputs = []
            mensaje_id = cliente.execute(celda.source, stop_on_error=True)
            limite = time.monotonic() + 600
            fallo = None
            while True:
                if time.monotonic() > limite:
                    raise TimeoutError(f"Celda {indice}: más de 10 minutos")
                try:
                    mensaje = cliente.get_iopub_msg(timeout=1)
                except Empty:
                    continue
                if mensaje.get("parent_header", {}).get("msg_id") != mensaje_id:
                    continue
                tipo, contenido = mensaje["msg_type"], mensaje["content"]
                if tipo == "execute_input":
                    celda.execution_count = contenido["execution_count"]
                elif tipo in {"stream", "display_data", "execute_result", "error"}:
                    celda.outputs.append(nbformat.v4.output_from_msg(mensaje))
                    if tipo == "error":
                        fallo = "\n".join(contenido["traceback"])
                elif tipo == "status" and contenido["execution_state"] == "idle":
                    break
            nbformat.write(notebook, ruta)
            if fallo:
                raise RuntimeError(fallo)
        nbformat.validate(notebook)
        print("Parte 0 ejecutada y guardada en el notebook.", flush=True)
    finally:
        cliente.stop_channels()
        km.shutdown_kernel(now=True)


if __name__ == "__main__":
    main()
