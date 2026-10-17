"""Taller 04 · 2.b — La hoja para etiquetar a mano (calibración contra una persona).

    python hoja_etiquetas.py --resultados resultados_base.csv --ids P13 P14 AM1 AM2 N7 ... -o etiquetar.html

Muestra, por caso: la pregunta, la respuesta del agente tal como la vieron el juez y el
verificador (la columna `respuesta` del CSV, cortada en 600 caracteres; se avisa si se cortó), la referencia (la cifra de su sql_verificacion y debe_contener)
y el MISMO criterio que recibe el juez. No muestra nada del juez ni del verificador automático:
las etiquetas se escriben antes de mirarlos. Al terminar, el botón descarga etiquetas.csv
(id,etiqueta), el formato de `evaluar_llmops.py --calibrar`.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path

from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
load_dotenv(AQUI / ".env")

from evaluar_llmops import CRITERIO_POR_TIPO  # noqa: E402


def respuesta_completa(traza_id: str, corta: str) -> str:
    try:
        from langfuse import get_client
        r = get_client().api.observations.get_many(trace_id=traza_id, fields="core,io", limit=100,
                                                    is_root_observation=True)
        for o in r.data:
            salida = o.dict(by_alias=True).get("output")
            if isinstance(salida, str):
                salida = json.loads(salida)
            if isinstance(salida, dict) and salida.get("answer"):
                return salida["answer"]
    except Exception as e:  # noqa: BLE001
        print(f"  {traza_id}: sin respuesta completa de Langfuse ({type(e).__name__}); uso la del CSV")
    return corta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resultados", default="resultados_base.csv")
    ap.add_argument("--golden", default="golden_set.json")
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("-o", "--salida", default="etiquetar.html")
    ap.add_argument("--quien", default="Jaime Astudillo", help="quién etiqueta (va en el título)")
    ap.add_argument("--descarga", default="etiquetas.csv", help="nombre del CSV que descarga la hoja")
    a = ap.parse_args()
    casos = {c["id"]: c for c in json.loads(Path(a.golden).read_text(encoding="utf-8"))["preguntas"]}
    with open(a.resultados, encoding="utf-8") as f:
        filas = {r["id"]: r for r in csv.DictReader(f)}
    tarjetas = []
    for i in a.ids:
        c, r = casos[i], filas[i]
        criterio = c.get("criterio_juez") or CRITERIO_POR_TIPO[c["tipo"]]
        ref = []
        if r.get("esperado"):
            ref.append(f"cifra correcta (de su sql_verificacion): {float(r['esperado']):,.2f}")
        if c.get("debe_contener"):
            ref.append(f"debe mencionar: {c['debe_contener']}")
        completa = respuesta_completa(r["traza_id"], r["respuesta"])
        resp = r["respuesta"] + ("\n[…recortada a 600 caracteres: es el texto que vio el juez]"
                                 if len(completa) > len(r["respuesta"]) else "")
        tarjetas.append(f"""
<section class="caso" data-id="{i}">
  <h2>{i} <span class="tipo">{c['tipo']}</span></h2>
  <p class="et">Pregunta</p><p>{html.escape(c['pregunta'][:600])}{' …' if len(c['pregunta']) > 600 else ''}</p>
  <p class="et">Criterio (el mismo que recibe el juez)</p><p class="crit">{html.escape(criterio)}</p>
  <p class="et">Referencia</p><p>{html.escape('; '.join(ref) or '(sin referencia: la decide el criterio)')}</p>
  <p class="et">Respuesta del agente (el mismo texto que calificaron el juez y el verificador)</p><pre>{html.escape(resp)}</pre>
  <div class="botones">
    <label><input type="radio" name="{i}" value="aprueba"> aprueba</label>
    <label><input type="radio" name="{i}" value="falla"> falla</label>
  </div>
</section>""")
    pagina = f"""<!doctype html><html lang="es"><meta charset="utf-8">
<title>Etiquetas a mano — Taller 04</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;max-width:56rem;margin:2rem auto;padding:0 1rem;color:#1b1b1b;background:#fafafa}}
h1{{font-size:1.4rem}} .caso{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1rem 1.2rem;margin:1rem 0}}
h2{{font-size:1.1rem;margin:0 0 .5rem}} .tipo{{font-weight:400;color:#666;font-size:.9rem;margin-left:.5rem}}
.et{{font-size:.75rem;text-transform:uppercase;letter-spacing:.04em;color:#777;margin:.8rem 0 .1rem}}
.crit{{background:#f3f6ff;padding:.4rem .6rem;border-radius:4px}}
pre{{white-space:pre-wrap;background:#f6f6f6;padding:.6rem;border-radius:4px;font-size:.85rem}}
.botones label{{margin-right:1.5rem;font-weight:600}} button{{font-size:1rem;padding:.6rem 1.2rem}}
#estado{{margin-left:1rem;color:#555}}
</style>
<h1>Etiquetas a mano — Taller 04 ({html.escape(a.quien)})</h1>
<p>{len(a.ids)} casos de la corrida base. Lee la pregunta, el criterio, la referencia y la respuesta, y marca
<b>aprueba</b> o <b>falla</b> con tu criterio. Esta hoja no muestra qué dijo el juez ni el verificador
automático: así las etiquetas se escriben antes de mirarlos. Al final, «Descargar {a.descarga}».</p>
{''.join(tarjetas)}
<p><button id="bajar">Descargar {a.descarga}</button><span id="estado"></span></p>
<script>
document.getElementById('bajar').onclick = () => {{
  const casos = [...document.querySelectorAll('.caso')];
  const filas = casos.map(c => [c.dataset.id, (c.querySelector('input:checked')||{{}}).value || '']);
  const faltan = filas.filter(f => !f[1]).map(f => f[0]);
  if (faltan.length) {{ document.getElementById('estado').textContent = 'Faltan: ' + faltan.join(', '); return; }}
  const csv = 'id,etiqueta\\n' + filas.map(f => f.join(',')).join('\\n') + '\\n';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {{type: 'text/csv'}}));
  a.download = '{a.descarga}'; a.click();
  document.getElementById('estado').textContent = 'Listo: ' + filas.length + ' etiquetas descargadas.';
}};
</script></html>"""
    Path(a.salida).write_text(pagina, encoding="utf-8")
    print(f"✓ {a.salida}: {len(a.ids)} casos")


if __name__ == "__main__":
    main()
