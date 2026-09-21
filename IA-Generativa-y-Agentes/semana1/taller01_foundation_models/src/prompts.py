"""Las cuatro variantes de prompting de la Parte 3.

La instruccion zero-shot es la misma que recibe GPT-2 en la Parte 0.c: es lo
que permite comparar que hace un modelo base con la misma orden.
"""


def prompt_zero_shot(caso):
    """Solo la instruccion."""
    return (
        "Resuelve el siguiente problema. Responde únicamente con un número "
        "entero, sin explicación ni unidades.\n\n"
        + caso["pregunta"]
    )


# Ejemplos inventados, NO tomados de los 10 casos: usar casos reales como
# ejemplos contaminaria la medicion.
_EJEMPLOS = [
    ("Una caja trae 8 lápices. Se compran 5 cajas y se regalan 12 lápices. "
     "¿Cuántos quedan?", 28),
    ("Un depósito tiene 400 litros. Se sacan 25 litros por hora durante "
     "6 horas. ¿Cuántos litros quedan?", 250),
    ("Se reparten 96 sillas en filas de 8. ¿Cuántas filas se forman?", 12),
]


def prompt_few_shot(caso):
    """2-3 ejemplos del tipo de respuesta esperada."""
    ejemplos = "\n\n".join(
        f"Problema: {p}\nRespuesta: {r}" for p, r in _EJEMPLOS
    )
    return (
        "Resuelve el problema. Responde únicamente con un número entero, "
        "sin explicación ni unidades.\n\n"
        f"{ejemplos}\n\n"
        f"Problema: {caso['pregunta']}\nRespuesta:"
    )


def prompt_cot(caso):
    """La instruccion de razonar paso a paso ANTES de responder."""
    return (
        "Resuelve el siguiente problema. Razona paso a paso y al final "
        "escribe la respuesta en una línea aparte con el formato "
        "'Respuesta: <número entero>'.\n\n"
        + caso["pregunta"]
    )


def prompt_structured(caso):
    """El formato de salida exigido: JSON con esquema.

    Pedir JSON en el prompt no garantiza nada; el modo JSON del proveedor
    garantiza que parsea; ninguno de los dos garantiza que el valor sea
    correcto. Esa comprobacion la hace el verificador.
    """
    return (
        "Resuelve el siguiente problema y devuelve exclusivamente un objeto "
        'JSON con esta forma: {"respuesta": <número entero>}. '
        "Sin texto adicional.\n\n"
        + caso["pregunta"]
    )
