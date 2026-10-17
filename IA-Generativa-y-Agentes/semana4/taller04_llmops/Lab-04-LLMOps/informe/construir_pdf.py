"""informe.md -> informe.html -> informe.pdf (Edge/Chrome sin interfaz), como en el Taller 3."""
import shutil
import subprocess
from pathlib import Path

import markdown

AQUI = Path(__file__).resolve().parent
CSS = """
body{font:10pt/1.42 Georgia,serif;max-width:48em;margin:auto;color:#1a1a1a}
h1{font-size:18pt;margin:0 0 .2em}h2{font-size:12.5pt;border-bottom:1px solid #999;margin-top:1.3em}
h3{font-size:10.5pt;margin:1em 0 .3em}
code{font:8.4pt Consolas,monospace;background:#f2f2f2;padding:0 .2em}
pre{background:#f6f6f6;padding:.45em .65em;white-space:pre-wrap;overflow-wrap:anywhere;font-size:7.4pt;line-height:1.28}
pre code{background:none;padding:0;font-size:7.4pt}
table{border-collapse:collapse;margin:.5em 0;font-size:8.6pt;width:100%}
th,td{border:1px solid #bbb;padding:.18em .4em;text-align:left;vertical-align:top}th{background:#eee}
hr{border:0;border-top:1px solid #ddd;margin:1.1em 0}@page{size:A4;margin:15mm}
"""
html = markdown.markdown((AQUI / "informe.md").read_text(encoding="utf-8"),
                         extensions=["tables", "fenced_code"])
ruta_html = AQUI / "informe.html"
ruta_html.write_text(f"<!doctype html><meta charset=utf-8><title>Taller 04</title>"
                     f"<style>{CSS}</style>{html}", encoding="utf-8")
navegador = next(p for p in [shutil.which("msedge"), shutil.which("chrome"),
                             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                             r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
                 if p and Path(p).exists())
subprocess.run([navegador, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={AQUI / 'informe.pdf'}", ruta_html.as_uri()], check=True)
print("✓", AQUI / "informe.pdf")
