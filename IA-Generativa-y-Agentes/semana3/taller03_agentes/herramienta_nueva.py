"""Una herramienta nueva para el servidor MCP. Es todo lo que hay que escribir para añadirla."""
import pandas as pd

from herramientas import ErrorHerramienta
from servidor_mcp import EXTRAS


def percentil(herr, resultado_id: str, columna: str, p: float) -> dict:
    df = herr._df(resultado_id)
    if columna not in df.columns:
        raise ErrorHerramienta(f"Columna '{columna}' no existe. Columnas: {list(df.columns)}")
    s = pd.to_numeric(df[columna], errors="coerce").dropna()
    return {"resultado_id": resultado_id, "columna": columna, "p": p,
            "valor": round(float(s.quantile(p / 100)), 2), "n": int(s.size)}


EXTRAS.append((
    "percentil",
    "Calcula el percentil p (0-100) de una columna numérica de un resultado de consultar_sql, "
    "sobre TODAS sus filas. Úsala cuando pidan un percentil distinto de la mediana o los cuartiles.",
    {"type": "object", "additionalProperties": False, "required": ["resultado_id", "columna", "p"],
     "properties": {"resultado_id": {"type": "string", "pattern": "^r[0-9]+$"},
                    "columna": {"type": "string"},
                    "p": {"type": "number", "minimum": 0, "maximum": 100}}},
    percentil,
))
