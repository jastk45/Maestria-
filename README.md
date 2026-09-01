# Maestría — Inteligencia Artificial

Trabajos y ejercicios de la maestría, organizados por materia y semana.

## Programación Avanzada

### Semana 1
| Trabajo | Carpeta |
|---|---|
| Ejercicio de refuerzo — pipeline de mediciones de servidores | `semana1/ejercicio_semana1/` |
| Control de lectura 1 | `semana1/Control_Lectura_1.ipynb` |
| Hackathon 1 | `semana1/hackathon1/` |

### Semana 2
| Trabajo | Carpeta |
|---|---|
| Ejercicio de refuerzo — comparación pareada de dos modelos | `semana2/ejercicio_semana2/` |
| Control de lectura 2 | `semana2/Control_Lectura_2.ipynb` |
| Hackathon 2 — PCA sobre penguins | `semana2/hackathon2/` |

## Ejecutar un ejercicio

Desde la carpeta del trabajo correspondiente:

```bash
uv sync --group dev
uv run pytest -q
```

## Notas

- Los entornos virtuales (`.venv/`), cachés y archivos `.zip` de entrega no se versionan.
- Cada ejercicio conserva su `git_history.txt` con el historial de commits pedido por el enunciado.
