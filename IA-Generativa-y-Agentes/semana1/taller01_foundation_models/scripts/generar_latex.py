"""Genera informe-latex/informe.tex con la clase llncs de la plantilla.

Tablas: desde datos/*.csv. Figuras: desde figuras/. Textos: extraidos de las
celdas markdown de taller-01-informe.ipynb (no se reescriben).
"""

import io
import re
import shutil
from pathlib import Path

import nbformat
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "informe-latex"
PLANTILLA = RAIZ.parent / "temples" / "Article_Review_pdf"
(OUT / "figuras").mkdir(parents=True, exist_ok=True)
(OUT / "tablas").mkdir(exist_ok=True)

for f in ("llncs.cls", "splncs04.bst"):
    shutil.copy(PLANTILLA / f, OUT / f)
for p in (RAIZ / "figuras").glob("*.png"):
    shutil.copy(p, OUT / "figuras" / p.name)

AUTOR = r"Jaime Astudillo \and Roberth Chachalo"
AUTOR_CORTO = "J. Astudillo y R. Chachalo"
REPO = "https://github.com/jastk45/Maestria-"


# ------------------------------------------------------------ markdown -> tex
def tex_escape(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


def md_a_tex(md):
    """Conversion minima: negrita, codigo, enlaces, listas, parrafos."""
    md = re.sub(r"^\*\*Entregable [^*]*\*\*\s*", "", md.strip())      # quita el rotulo
    md = re.sub(r"^\*\*(Conclusión|Hallazgos|Análisis)[^*]*\*\*[^\n]*\n", "", md)
    md = re.sub(r"^#+ .*\n", "", md, flags=re.M)                       # quita encabezados
    md = re.sub(r"^---\s*$", "", md, flags=re.M)
    partes = re.split(r"(`[^`]*`)", md)                                 # proteger codigo
    out = []
    for p in partes:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append(r"\texttt{" + tex_escape(p[1:-1]) + "}")
        else:
            p = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", p)               # [txt](url) -> txt
            p = tex_escape(p)
            p = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", p, flags=re.S)
            p = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"\\emph{\1}", p, flags=re.S)
            out.append(p)
    s = "".join(out)
    # listas "- " -> itemize
    def lista(m):
        items = "".join(r"\item " + l[2:].strip() + "\n" for l in m.group(0).splitlines())
        return "\\begin{itemize}\n" + items + "\\end{itemize}\n"
    s = re.sub(r"(?:^- .*\n?)+", lista, s, flags=re.M)
    s = re.sub(r"\n{2,}", "\n\n", s).strip()
    return s


nb = nbformat.read(io.open(RAIZ / "taller-01-informe.ipynb", encoding="utf-8"), as_version=4)
md_cells = [c.source for c in nb.cells if c.cell_type == "markdown"]


def celda(prefijo):
    for s in md_cells:
        if s.lstrip().startswith(prefijo):
            return md_a_tex(s)
    return ""


def celdas_entre(ini, fin):
    """Todas las celdas markdown entre dos encabezados (sin incluirlos)."""
    dentro, acc = False, []
    for s in md_cells:
        t = s.lstrip()
        if t.startswith(ini):
            dentro = True; acc.append(md_a_tex(s)); continue
        if dentro and t.startswith(fin):
            break
        if dentro:
            acc.append(md_a_tex(s))
    return "\n\n".join(a for a in acc if a)


tarea = md_a_tex(re.search(r"## Tarea elegida\n\n(.*?)\n\n## ", md_cells[0], re.S).group(1))
t0a = celdas_entre("## 0.a", "## 0.b")
t0b = celdas_entre("## 0.b", "## 0.c")
t0c = celda("**Entregable 0.c")
t1 = celda("**Conclusión Parte 1**")
t2a = celda("**Hallazgos y discrepancias 2.a**")
t2b = celda("**Conclusión 2.b**")
t3 = celda("**Conclusión Parte 3**")
t4a = celda("**Conclusión 4.a**")
t4b = celda("**Análisis 4.b**")
p5 = next(s for s in md_cells if 'id="parte-5"' in s)
preguntas = re.split(r"\n### \d\. ", p5)[1:]
p5_tex = ""
for q in preguntas:
    titulo, cuerpo = q.split("\n", 1)
    cuerpo = re.sub(r"```\n(.*?)```", lambda m: "\\begin{verbatim}\n" + m.group(1) + "\\end{verbatim}", cuerpo, flags=re.S)
    # convertir todo menos los verbatim
    trozos = re.split(r"(\\begin\{verbatim\}.*?\\end\{verbatim\})", cuerpo, flags=re.S)
    cuerpo = "".join(t if t.startswith("\\begin{verbatim}") else md_a_tex(t) for t in trozos)
    p5_tex += "\\subsection{" + tex_escape(re.sub(r"\*(.+?)\*", r"\1", titulo)) + "}\n" + cuerpo + "\n\n"


# ------------------------------------------------------------------- tablas
def tabla(nombre, df, caption, label, colfmt=None, ff="%.3f"):
    tex = df.to_latex(index=False, escape=True, float_format=ff, column_format=colfmt, na_rep="--")
    tex = tex.replace("\\toprule", "\\hline").replace("\\midrule", "\\hline").replace("\\bottomrule", "\\hline")
    (OUT / "tablas" / f"{nombre}.tex").write_text(
        "\\begin{table}[H]\\centering\\caption{" + caption + "}\\label{" + label + "}\n"
        "{\\footnotesize\\setlength{\\tabcolsep}{3.5pt}\n" + tex + "}\\end{table}\n", encoding="utf-8")
    return f"\\input{{tablas/{nombre}}}"


D = RAIZ / "datos"
d0 = pd.read_csv(D / "parte0_distribuciones.csv").drop(columns=["prefijo"])
d0.columns = ["prefijo", "T", "entropía (bits)", "núcleo 0.9", "p máx"]
T0 = tabla("p0", d0, "Entropía y tamaño del núcleo del 90\\,\\% por prefijo y temperatura (GPT-2).", "tab:p0", ff="%.4g")

d1 = pd.read_csv(D / "tabla_parte1.csv")
d1["precio_verificado"] = d1.precio_verificado.replace({"local (cero real)": "local"})
d1.columns = ["modelo", "exactitud", "lat. (s)", "tok. in", "tok. out", "costo USD", "verificado"]
T1 = tabla("p1", d1, "Parte 1: tres modelos sobre los 10 casos. Latencia = tiempo de pared de la petición.", "tab:p1", ff="%.5g")

d2a = pd.read_csv(D / "tabla_parte2a.csv")[["modelo", "parametro", "declarado", "observado", "evidencia"]]
d2a["evidencia"] = (d2a.evidencia.str.replace(" de casos con corridas distintas", "", regex=False)
                                .str.replace("; ", " / ", regex=False))
d2a.columns = ["modelo", "parámetro", "declarado (tabla)", "observado", "evidencia"]
T2A = tabla("p2a", d2a, "Parte 2.a: matriz de exposición, declarado frente a observado (2026-09-20). "
            "Evidencia: porcentaje de casos cuyas corridas difieren con cada valor; o número de llamadas con error.",
            "tab:p2a", colfmt="@{}lllp{2.0cm}p{3.3cm}@{}")
err = pd.read_csv(D / "tabla_parte2a.csv")
err = err[err.error_literal.notna()][["modelo", "parametro", "error_literal"]]
err["error_literal"] = err.error_literal.str.slice(0, 160)
err.columns = ["modelo", "parámetro", "mensaje literal (truncado a 160 caracteres)"]
T2AE = tabla("p2ae", err, "Parte 2.a: mensajes de error transcritos de las celdas rechazadas.", "tab:p2ae", colfmt="llp{7.5cm}")

d2b = pd.read_csv(D / "tabla_parte2b.csv")
d2b.columns = ["T", "top_p", "exactitud", "tokens out (media)", "estabilidad"]
T2B = tabla("p2b", d2b, "Parte 2.b: rejilla temperature $\\times$ top\\_p sobre gpt-4o-mini, 3 corridas $\\times$ 10 casos por celda.", "tab:p2b")
dk = pd.read_csv(D / "tabla_parte2b_topk.csv")[["top_k", "exactitud", "tokens_out", "estabilidad_salida", "casos_identicos_x5"]]
dk.columns = ["top_k", "exactitud", "tokens out (media)", "estabilidad", "casos idénticos x5"]
TK = tabla("p2bk", dk, "Parte 2.b: barrido de top\\_k en local (qwen3:1.7b, T=1, 5 corridas secuenciales $\\times$ 10 casos).", "tab:p2bk")

d3 = pd.read_csv(D / "tabla_parte3.csv")
d3.columns = ["variante", "exactitud", "tokens in", "tokens out", "costo USD"]
T3 = tabla("p3", d3, "Parte 3: cuatro variantes de prompting sobre gpt-4o-mini, 10 casos.", "tab:p3", ff="%.5g")

d4 = pd.read_csv(D / "tabla_parte4a.csv")[["esfuerzo", "exactitud", "tokens_razonamiento", "tokens_visibles", "latencia_s", "costo_usd"]]
d4.columns = ["esfuerzo", "exactitud", "tok. razonamiento", "tok. visibles", "lat. (s)", "costo USD"]
T4A = tabla("p4a", d4, "Parte 4.a: barrido de esfuerzo en gpt-5.6-luna, 10 casos por nivel.", "tab:p4a", ff="%.5g")
d4b = pd.read_csv(D / "tabla_parte4b.csv")
d4b.columns = ["esfuerzo", "caso", "acierto", "tokens razonamiento"]
T4B = tabla("p4b", d4b, "Parte 4.b: los tres casos contaminados en los niveles extremos.", "tab:p4b", ff="%.3g")

# salidas crudas
df = pd.read_csv(D / "resultados.csv"); df["parte"] = df.parte.astype(str)
p0 = df[df.parte == "0"].drop_duplicates("plantilla").set_index("plantilla")
import textwrap


def verb(s, n=420):
    """Salida cruda envuelta a 70 columnas para que el verbatim no desborde."""
    s = str(s).strip()[:n]
    return "\n".join(textwrap.fill(l, 58) if l.strip() else "" for l in s.splitlines())


salida_0c = verb(p0.loc["zero_shot", "salida"])
salida_deg = verb(p0.loc["0b_degeneracion", "salida"])
salida_int = verb(p0.loc["0b_interruptor", "salida"], 160)
k1 = df[(df.parte == "0") & (df.plantilla == "0b_top_k_1")]
topk1_txt = (f"Con \\texttt{{do\\_sample=True}} y \\texttt{{top\\_k=1}}, las {len(k1)} corridas registradas en el CSV "
             f"({len(k1) // 5} ejecuciones del notebook con 5 semillas cada una) produjeron "
             f"{k1.salida.nunique()} salida distinta: idéntica a la de greedy.")


def fig(archivo, caption, label, width="\\textwidth", extra=""):
    return ("\\begin{figure}[H]\\centering\\includegraphics[width=" + width + extra + "]{figuras/" + archivo + "}"
            "\\caption{" + caption + "}\\label{" + label + "}\\end{figure}\n")


# ------------------------------------------------------------------ documento
tex = r"""\documentclass[runningheads]{llncs}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{float}
\usepackage{amsmath}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\renewcommand{\tablename}{Tabla}
\renewcommand{\figurename}{Figura}
\emergencystretch=2.5em
\begin{document}

\title{Taller 01 --- Foundation Models: Comparación, Decodificación y Razonamiento}
\titlerunning{Taller 01 --- Foundation Models}
\author{""" + AUTOR + r"""}
\authorrunning{""" + AUTOR_CORTO + r"""}
\institute{MMIA 6013 --- IA Generativa y Agentes, Universidad San Francisco de Quito}
\maketitle

\section{Tarea elegida}
""" + tarea + r"""

Los diez casos limpios y los tres contaminados, con sus respuestas esperadas, están en \texttt{datos/casos.json} del repositorio.

\section{Parte 0 --- El modelo base y la distribución}
Fila \texttt{base\_local}: \texttt{openai-community/gpt2}, 124\,M de parámetros, en CPU, sin API ni credenciales.

\subsection{La distribución del siguiente token}
""" + t0a + r"""

""" + fig("parte0a_temperatura.png", "Distribución de los 15 candidatos más probables para $T\\in\\{0.1,0.7,1.0,1.5,2.0\\}$ en los dos prefijos.", "fig:p0a", "0.95\\textwidth", ",height=0.42\\textheight,keepaspectratio") + T0 + r"""

\subsection{Las tres palancas sobre esa misma distribución}
""" + t0b + r"""

Salida con \texttt{do\_sample=False} (idéntica para $T=0.2$ y $T=1.5$):
\begin{verbatim}
""" + salida_int + r"""
\end{verbatim}
""" + topk1_txt + r"""

Degeneración con 100 tokens en modo greedy (Holtzman et al.~\cite{holtzman2020}), salida sin editar:
\begin{verbatim}
""" + salida_deg + r"""
\end{verbatim}

""" + fig("parte0b_cortes.png", "Dónde corta cada palanca: tokens que sobreviven a top\\_k=5 y a top\\_p=0.9 en cada prefijo. En el prefijo abierto los dos conjuntos no coinciden (5 frente a 241 tokens).", "fig:p0b", "0.95\\textwidth", ",height=0.42\\textheight,keepaspectratio") + r"""

\subsection{El límite del modelo base}
Salida cruda de GPT-2 ante la instrucción exacta de las Partes 1 a 4:
\begin{verbatim}
""" + salida_0c + r"""
\end{verbatim}
""" + t0c + r"""

\section{Parte 1 --- Comparación de modelos}
Precios de la tabla semestral, cada uno con la fecha de verificación de su propia fila (Tabla~\ref{tab:p1}).
""" + T1 + t1 + r"""

\section{Parte 2 --- Decodificación}
\subsection{Matriz de exposición}
Cada parámetro se mandó con dos valores extremos, 3 casos $\times$ 2 corridas. El estado se decide por la dispersión entre corridas de la tupla (salida, tokens de salida), no por la respuesta final (Tabla~\ref{tab:p2a}); los mensajes de error se transcriben en la Tabla~\ref{tab:p2ae}.
""" + T2A + T2AE + t2a + r"""

\subsection{Barrido de temperature y top-p}
Estimación previa con el supuesto del enunciado (1\,000 tokens de entrada y 600 de salida por llamada) al precio de gpt-4o-mini verificado el 2026-08-26: 750 llamadas $\approx$ 0.38\,USD. Se corrieron 450 (3 corridas por celda); costo real 0.03\,USD.
""" + T2B + fig("parte2b_rejilla.png", "Exactitud por celda de la rejilla (gpt-4o-mini).", "fig:p2b", "0.6\\textwidth") + TK + t2b + r"""

\section{Parte 3 --- Prompting estructurado}
Las cuatro plantillas están en \texttt{src/prompts.py}. Los ejemplos del few-shot son problemas inventados, no los diez casos. La variante estructurada usa el modo JSON del proveedor (\texttt{response\_format} con tipo \texttt{json\_object}), sin esquema estricto.
""" + T3 + t3 + r"""

\section{Parte 4 --- Modelos de razonamiento y niveles de esfuerzo}
\subsection{Barrido de esfuerzo}
Modelo gpt-5.6-luna. El dial es \texttt{reasoning\_effort}. El contador de tokens de razonamiento es el campo \texttt{reasoning\_tokens} que devuelve la API. Se corrió \texttt{low} completo antes de los otros dos: 287 tokens de razonamiento en 10 casos frente a los 1\,500 supuestos por el enunciado.
""" + T4A + fig("parte4a_exactitud_vs_tokens.png", "Exactitud frente a tokens de razonamiento medidos.", "fig:p4a1", "0.62\\textwidth") + fig("parte4a_costo_vs_exactitud.png", "Costo en USD frente a exactitud.", "fig:p4a2", "0.62\\textwidth") + t4a + r"""

\subsection{El caso donde pensar más hace daño}
Casos c11 (distracción por lo irrelevante), c12 (sobreajuste al marco) y c13 (correlación espuria), según los modos de fallo de Gema et al.~\cite{gema2025}.
""" + T4B + t4b + r"""

\section{Parte 5 --- Reflexión teórica}
""" + p5_tex + r"""

\section{Reproducibilidad y desviaciones declaradas}
\begin{itemize}
\item Código, casos, \texttt{requirements.txt} y \texttt{datos/resultados.csv} (850 filas, una por llamada, las locales con costo cero) en \url{""" + REPO + r"""}.\newline Carpeta: \path{IA-Generativa-y-Agentes/semana1/taller01_foundation_models}
\item Las claves se leen de un \texttt{.env} excluido por \texttt{.gitignore}; ninguna aparece en el informe, el notebook ni el repositorio.
\item La rejilla de 2.b se corrió con 3 corridas por celda en vez de 5. Las sondas de 2.a se mandaron con 4 peticiones en paralelo; el barrido de top\_k, en secuencia.
\item Los tokens de razonamiento de qwen3 se cuentan como palabras del campo \texttt{thinking} de \texttt{/api/chat}; los de gpt-5.6-luna, del contador de la API.
\end{itemize}

\begin{thebibliography}{8}
\bibitem{holtzman2020} Holtzman, A., Buys, J., Du, L., Forbes, M., Choi, Y.: The Curious Case of Neural Text Degeneration. ICLR (2020). \url{https://arxiv.org/abs/1904.09751}
\bibitem{gema2025} Gema, A.P., et al.: Inverse Scaling in Test-Time Compute. TMLR (2025)
\bibitem{lanham2023} Lanham, T., et al.: Measuring Faithfulness in Chain-of-Thought Reasoning. arXiv:2307.13702 (2023)
\bibitem{vaswani2017} Vaswani, A., et al.: Attention Is All You Need. NeurIPS (2017)
\bibitem{gpt2} Radford, A., et al.: Language Models are Unsupervised Multitask Learners. OpenAI (2019). Model card: \url{https://huggingface.co/openai-community/gpt2}
\end{thebibliography}
\end{document}
"""
(OUT / "informe.tex").write_text(tex, encoding="utf-8")
print("escrito", OUT / "informe.tex", "|", len(tex.split()), "palabras")
