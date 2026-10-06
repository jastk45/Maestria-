"""Regenera los PNG que una traza cita y que ya no están en disco.

    python regenerar_graficos.py        # escribe entregables/graficos_regenerados.txt

Por qué es fiel: la base es determinista (crear_base.py, semilla 6013; su contenido se
verificó por hash en entregables/verificacion_base.txt) y la traza guarda la consulta exacta
que produjo el resultado_id del gráfico. Se vuelve a ejecutar esa consulta con la misma
herramienta y se dibuja con los mismos argumentos en la misma ruta. Cada archivo regenerado
queda listado en el manifiesto: no se presenta como el original.
"""
import glob
import json
from pathlib import Path

from herramientas import Herramientas

lineas = []
for ruta_traza in sorted(glob.glob("trazas/**/*.json", recursive=True)):
    traza = json.loads(Path(ruta_traza).read_text(encoding="utf-8"))
    pasos = traza.get("trace", [])
    for paso in pasos:
        obs, acc = paso.get("observation"), paso.get("action")
        if not (isinstance(obs, dict) and "grafico" in obs and acc):
            continue
        destino = Path(obs["grafico"].replace("\\", "/"))
        if destino.exists():
            continue
        args = json.loads(acc["args"])
        consulta = next(json.loads(p["action"]["args"])["consulta"] for p in pasos
                        if p.get("action") and p["action"]["name"] == "consultar_sql"
                        and isinstance(p.get("observation"), dict)
                        and p["observation"].get("resultado_id") == args["resultado_id"])
        id_corrida, n, _ = destino.stem.rsplit("-", 2)
        h = Herramientas(id_corrida)
        h.consultar_sql(consulta)                      # se guarda como r1 en la instancia nueva
        h.resultados[args["resultado_id"]] = h.resultados.pop("r1")
        h.n_graficos = int(n) - 1
        hecho = h.grafico(**args)
        assert Path(hecho["grafico"]) == destino, (hecho, destino)
        lineas.append(f"{destino.as_posix()}  <- {Path(ruta_traza).as_posix()}  ·  {consulta}")

manifiesto = Path("entregables/graficos_regenerados.txt")
if lineas:   # se añade: una segunda ejecución no borra el registro de la primera
    nuevo = not manifiesto.exists()
    with manifiesto.open("a", encoding="utf-8") as f:
        if nuevo:
            f.write("PNG regenerados desde la consulta registrada en su traza (ver regenerar_graficos.py):\n")
        f.write("\n".join(lineas) + "\n")
print("\n".join(lineas) or "nada que regenerar")
