"""Taller 03 — Las cuatro herramientas del agente, con su contrato.

Cada herramienta = función + nombre + descripción + esquema JSON (regla 1). Los límites
(filas, carpeta de gráficos, tamaño de la observación) son constantes de este módulo, no
argumentos: el modelo no los puede cambiar (regla 3).

REGLA 4 — cómo se pasan datos las herramientas: `consultar_sql` guarda el resultado
COMPLETO en memoria, bajo un id corto (`r1`, `r2`…), y al modelo le devuelve solo una vista
previa. `estadisticas` y `grafico` reciben ese id, no una ruta. Así:
  - las estadísticas se calculan sobre todas las filas, no sobre las 50 que ve el modelo;
  - no hay ninguna ruta de archivo en ningún esquema (lo que rompía la 0.c);
  - el almacén vive en la instancia de la corrida: no queda estado entre preguntas.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

DB_PATH = Path(os.getenv("AGENT_DB_PATH", "data/database.sqlite"))
CARPETA_GRAFICOS = Path("graficos")      # REGLA 3: fija, fuera del alcance del modelo
MAX_FILAS_VISTA = 50                     # REGLA 3: lo que vuelve al modelo
MAX_FILAS_GUARDADAS = 100_000            # tope del resultado completo en memoria
MAX_SEGUNDOS_CONSULTA = 10               # REGLA 3: una consulta que no termina se interrumpe

# Mensaje claro para el modelo; la garantía la da mode=ro + query_only, no esta lista.
ESCRITURA = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|"
                       r"pragma|vacuum|reindex|replace\s+into)\b", re.I)


class ErrorHerramienta(Exception):
    """Un error que vuelve al modelo como {"error": ...}; nunca termina la corrida."""


class Herramientas:
    def __init__(self, id_corrida: str = "manual"):
        self.id_corrida = id_corrida
        self.resultados: dict[str, pd.DataFrame] = {}
        self.n_graficos = 0

    # ── REGLA 2: solo lectura de verdad ───────────────────────────────────────────────
    def _conectar(self) -> sqlite3.Connection:
        if not DB_PATH.exists():
            raise ErrorHerramienta(f"No existe la base {DB_PATH}: corre crear_base.py")
        conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON")
        limite = time.monotonic() + MAX_SEGUNDOS_CONSULTA
        conn.set_progress_handler(lambda: time.monotonic() > limite, 10_000)
        return conn

    def describir_esquema(self) -> dict:
        with self._conectar() as conn:
            tablas = {}
            for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                cols = [f"{c[1]} {c[2]}" for c in conn.execute(f'PRAGMA table_info("{t}")')]
                n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                tablas[t] = {"columnas": cols, "filas": n}
            rango = conn.execute("SELECT MIN(fecha), MAX(fecha) FROM ventas").fetchone()
            dominios = {
                "clientes.region": [r[0] for r in conn.execute("SELECT DISTINCT region FROM clientes")],
                "clientes.segmento": [r[0] for r in conn.execute("SELECT DISTINCT segmento FROM clientes")],
                "productos.categoria": [r[0] for r in conn.execute("SELECT DISTINCT categoria FROM productos")],
            }
        return {
            "tablas": tablas,
            "relaciones": ["ventas.cliente_id -> clientes.cliente_id",
                           "ventas.producto_id -> productos.producto_id"],
            "metricas_derivadas": {
                "importe de una venta": "cantidad * precio_unitario * (1 - descuento)",
                "facturación / ventas en dinero": "SUM(importe)",
            },
            "fechas": {"formato": "YYYY-MM-DD (texto)", "desde": rango[0], "hasta": rango[1]},
            "valores_posibles": dominios,
        }

    def consultar_sql(self, consulta: str) -> dict:
        sql = consulta.strip().rstrip(";").strip()
        if ";" in sql:
            raise ErrorHerramienta("Una sola sentencia por llamada (sin ';' intermedios).")
        if not re.match(r"^(select|with)\b", sql, re.I):
            raise ErrorHerramienta("Solo se permite SELECT o WITH ... SELECT.")
        if ESCRITURA.search(sql):
            raise ErrorHerramienta("Consulta rechazada: contiene una operación de escritura. "
                                   "La base es de solo lectura.")
        with self._conectar() as conn:
            try:
                cur = conn.execute(sql)
            except sqlite3.Error as e:
                raise ErrorHerramienta(f"SQLite: {e}. Usa describir_esquema para ver tablas y "
                                       "columnas.") from e
            columnas = [d[0] for d in cur.description]
            filas = cur.fetchmany(MAX_FILAS_GUARDADAS + 1)     # REGLA 3: el tope es del código
        truncado_memoria = len(filas) > MAX_FILAS_GUARDADAS
        df = pd.DataFrame(filas[:MAX_FILAS_GUARDADAS], columns=columnas)
        rid = f"r{len(self.resultados) + 1}"
        self.resultados[rid] = df
        return {
            "resultado_id": rid,
            "columnas": columnas,
            "total_filas": len(df),
            "filas": df.head(MAX_FILAS_VISTA).round(4).to_dict(orient="records"),
            "vista_truncada": len(df) > MAX_FILAS_VISTA,
            "nota": (f"Ves {min(len(df), MAX_FILAS_VISTA)} de {len(df)} filas. Para medias, "
                     f"medianas o dispersión usa estadisticas con resultado_id='{rid}'.")
                    + (" Resultado recortado a 100 000 filas." if truncado_memoria else ""),
        }

    def _df(self, resultado_id: str) -> pd.DataFrame:
        if resultado_id not in self.resultados:
            raise ErrorHerramienta(f"No existe el resultado '{resultado_id}'. Disponibles: "
                                   f"{list(self.resultados) or 'ninguno: llama antes a consultar_sql'}")
        return self.resultados[resultado_id]

    def estadisticas(self, resultado_id: str, columna: str) -> dict:
        df = self._df(resultado_id)
        if columna not in df.columns:
            raise ErrorHerramienta(f"Columna '{columna}' no existe. Columnas: {list(df.columns)}")
        s = pd.to_numeric(df[columna], errors="coerce").dropna()
        if s.empty:
            raise ErrorHerramienta(f"La columna '{columna}' no tiene valores numéricos.")
        return {"resultado_id": resultado_id, "columna": columna, "n": int(s.size),
                "media": round(float(s.mean()), 4), "mediana": round(float(s.median()), 4),
                "desviacion_estandar_muestral": round(float(s.std(ddof=1)), 4) if s.size > 1 else None,
                "minimo": float(s.min()), "maximo": float(s.max()),
                "p25": round(float(s.quantile(0.25)), 4), "p75": round(float(s.quantile(0.75)), 4),
                "suma": round(float(s.sum()), 4)}

    def grafico(self, resultado_id: str, x: str, y: str, tipo: str = "barras") -> dict:
        df = self._df(resultado_id)
        faltan = [c for c in (x, y) if c not in df.columns]
        if faltan:
            raise ErrorHerramienta(f"Columnas {faltan} no existen. Columnas: {list(df.columns)}")
        self.n_graficos += 1
        CARPETA_GRAFICOS.mkdir(exist_ok=True)
        # REGLA 3: nombre único por corrida y gráfico; ninguno pisa a otro
        ruta = CARPETA_GRAFICOS / f"{self.id_corrida}-{self.n_graficos}-{tipo}.png"
        fig, ax = plt.subplots(figsize=(8, 4))
        {"barras": ax.bar, "linea": ax.plot, "dispersion": ax.scatter}[tipo](df[x].astype(str) if tipo != "dispersion" else df[x], df[y])
        ax.set_xlabel(x), ax.set_ylabel(y), ax.set_title(f"{y} por {x}")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout(), fig.savefig(ruta), plt.close(fig)
        return {"grafico": str(ruta), "tipo": tipo, "x": x, "y": y, "puntos": len(df)}


# ── REGLA 1 — el catálogo: nombre, descripción y esquema ──────────────────────────────────
def _esq(props: dict, req: list) -> dict:
    return {"type": "object", "properties": props, "required": req, "additionalProperties": False}


CATALOGO = [
    {"name": "describir_esquema",
     "description": "Devuelve las tablas, columnas, relaciones, rango de fechas, valores posibles "
                    "de las columnas categóricas y cómo se calcula el importe. Úsala PRIMERO, "
                    "antes de escribir SQL. No devuelve datos de ventas.",
     "parameters": _esq({}, [])},
    {"name": "consultar_sql",
     "description": "Ejecuta UNA consulta SQLite de solo lectura (SELECT o WITH ... SELECT) y "
                    "guarda el resultado completo con un resultado_id. Devuelve las columnas y "
                    "como máximo 50 filas de vista previa. Úsala para filtrar, agrupar y sumar. "
                    "No modifica datos: cualquier escritura se rechaza.",
     "parameters": _esq({"consulta": {"type": "string", "minLength": 6,
                                      "description": "Una sentencia SELECT de SQLite, sin ';' intermedios"}},
                        ["consulta"])},
    {"name": "estadisticas",
     "description": "Calcula n, media, mediana, desviación estándar muestral, mínimo, máximo, "
                    "cuartiles y suma de una columna numérica de un resultado de consultar_sql, "
                    "usando TODAS sus filas (no solo la vista previa). Úsala para medianas y "
                    "dispersión.",
     "parameters": _esq({"resultado_id": {"type": "string", "pattern": "^r[0-9]+$",
                                          "description": "id devuelto por consultar_sql, p. ej. r1"},
                         "columna": {"type": "string", "description": "nombre exacto de la columna"}},
                        ["resultado_id", "columna"])},
    {"name": "grafico",
     "description": "Dibuja un gráfico de un resultado de consultar_sql y lo guarda como PNG en "
                    "la carpeta de gráficos del laboratorio. Devuelve la ruta. Úsala solo si "
                    "piden un gráfico o una visualización.",
     "parameters": _esq({"resultado_id": {"type": "string", "pattern": "^r[0-9]+$"},
                         "x": {"type": "string", "description": "columna del eje x"},
                         "y": {"type": "string", "description": "columna numérica del eje y"},
                         "tipo": {"type": "string", "enum": ["barras", "linea", "dispersion"]}},
                        ["resultado_id", "x", "y"])},
]
