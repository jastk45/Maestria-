# Hackathon 2 — PCA con Palmer Penguins

Lea primero `Hackathon_2_Enunciado.docx` o su copia en PDF.

## Inicio rápido

Desde esta carpeta:

```bash
uv sync --locked
uv run jupyter lab
```

Abra `Hackathon_2_Starter.ipynb`, escriba los nombres de ambos integrantes y complete las celdas en orden.

## Reglas técnicas

- Use `numpy.linalg.svd`; no use `sklearn.decomposition.PCA`.
- No modifique `data/penguins.csv`.
- El notebook debe ejecutarse de principio a fin sin errores.
- El gráfico final debe guardarse en `output/pca_penguins.png`.

## Verificación

Después de completar y guardar el notebook:

```bash
uv run python verify_notebook.py
```

El verificador ejecuta una copia del notebook desde cero y guarda la evidencia en `output/Hackathon_2_Verificado.ipynb`.

## Entrega

Entregue:

- `Hackathon_2_Starter.ipynb` ejecutado y guardado;
- `output/pca_penguins.png`;
- nombres de ambos integrantes visibles al inicio del notebook.
