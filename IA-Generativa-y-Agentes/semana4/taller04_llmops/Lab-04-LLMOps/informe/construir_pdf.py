"""informe.md -> informe.html -> informe.pdf (Edge/Chrome sin interfaz), como en el Taller 3.

Diseño de impresión: tinta azul pizarra, un acento petróleo (el de un panel de trazas), Constantia para
el texto, Corbel para títulos y tablas (cifras tabulares) y Consolas para las salidas de consola: fuentes
estáticas de Windows (las variables de la web dejan contornos superpuestos en el PDF). Lo único que llama la atención es la ficha inicial —opción, ruta, modelos, fecha y
repositorio—, que es lo primero que pide la rúbrica; el resto, sobrio.
"""
import shutil
import subprocess
from pathlib import Path

import markdown

AQUI = Path(__file__).resolve().parent
CSS = """
:root{--tinta:#1d2433;--acento:#1f6f78;--acento-suave:#e8f1f2;--linea:#cfd6e0;--codigo:#f4f6f8;--gris:#5b6576}
@page{size:A4;margin:14mm 15mm 15mm 15mm}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;color:var(--tinta);background:#fff;font:9.6pt/1.46 Constantia,Georgia,serif;hyphens:auto;font-variant-numeric:lining-nums}
p,ul,ol{max-width:168mm;margin:0 0 2.2mm}
p{orphans:3;widows:3}
strong{font-weight:700}
h1,h2,h3{font-family:Corbel,"Segoe UI",sans-serif;break-after:avoid;line-height:1.2}
h1{font-size:21pt;font-weight:700;letter-spacing:-.01em;margin:0 0 1.6mm}
.autor{font:9.6pt/1.4 Corbel,"Segoe UI",sans-serif;color:var(--gris);margin:0 0 4.5mm}
h2{font-size:13.5pt;font-weight:700;color:var(--acento);margin:6.5mm 0 2.4mm;padding-bottom:1.2mm;
   border-bottom:.6pt solid var(--linea)}
h3{font-size:11pt;font-weight:700;margin:4.5mm 0 1.8mm}
ul{padding-left:4.6mm}li{margin:.7mm 0}
a{color:var(--acento);text-decoration:none;overflow-wrap:anywhere}
code{font:.86em Consolas,monospace;background:var(--codigo);padding:0 .22em;border-radius:2px}
pre{font:7.4pt/1.36 Consolas,monospace;background:var(--codigo);border-left:2pt solid var(--acento);
    padding:2mm 3mm;margin:1.4mm 0 2.6mm;white-space:pre-wrap;overflow-wrap:anywhere;break-inside:avoid}
pre code{background:none;padding:0;font:inherit}
table{width:100%;border-collapse:collapse;margin:1.8mm 0 3.4mm;font:8.5pt/1.3 Corbel,"Segoe UI",sans-serif;
      font-variant-numeric:lining-nums tabular-nums}
thead th{background:var(--acento-suave);color:var(--acento);font-weight:700;text-align:left;
         padding:1.3mm 1.7mm;border-bottom:.8pt solid var(--acento)}
td{padding:1.15mm 1.7mm;border-bottom:.4pt solid var(--linea);vertical-align:top}
tr{break-inside:avoid}
td code,th code{font-size:.9em}
td strong{color:var(--tinta)}
.ficha{background:var(--acento-suave);border-left:3pt solid var(--acento);padding:1.6mm 4mm 1.8mm;margin:0 0 5mm}
.ficha table{margin:0;font-size:9pt;line-height:1.38}
.ficha thead{display:none}
.ficha td{border-bottom:.4pt solid #c9dfe1;padding:1.25mm 1.6mm}
.ficha tr:last-child td{border-bottom:none}
.ficha td:first-child{width:31mm;font-weight:700;color:var(--acento);white-space:nowrap}
.ficha code{background:#fff}
.nota{font:8.5pt/1.4 Corbel,"Segoe UI",sans-serif;color:var(--gris);margin-top:-.6mm}
"""
html = markdown.markdown((AQUI / "informe.md").read_text(encoding="utf-8"),
                         extensions=["tables", "fenced_code", "md_in_html"])
ruta_html = AQUI / "informe.html"
ruta_html.write_text(f'<!doctype html><html lang="es"><meta charset="utf-8"><title>Taller 04</title>'
                     f'<style>{CSS}</style>{html}</html>',
                     encoding="utf-8")
navegador = next(p for p in [shutil.which("msedge"), shutil.which("chrome"),
                             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                             r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
                 if p and Path(p).exists())
subprocess.run([navegador, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={AQUI / 'informe.pdf'}",
                ruta_html.as_uri()], check=True)
ruta_html.unlink()          # el HTML es solo un paso intermedio: no se versiona
print("✓", AQUI / "informe.pdf")
