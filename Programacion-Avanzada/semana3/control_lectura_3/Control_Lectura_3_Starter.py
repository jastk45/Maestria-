# -*- coding: utf-8 -*-
# Versión alternativa del notebook; Python 3 sin dependencias externas.


# # Control de lectura 3
# ## Verificación numérica de gradientes mediante diferencias finitas
# **20 minutos · Individual · Notebook principal**
# 
# Compare dos gradientes candidatos con una aproximación numérica. No necesita derivar
# a mano, usar PyTorch ni entrenar una neurona. La lectura previa se realiza antes del control.
# Complete una sola expresión, conserve su predicción inicial y justifique con sus resultados.

# **Nombre:** [ESCRIBA SU NOMBRE]

# ## Forma de trabajo
# 1. Responda P0 antes de ejecutar (3 minutos).
# 2. Complete `diferencia_central` (5 minutos).
# 3. Ejecute y observe las dos tablas (5 minutos).
# 4. Responda P1 a P3 (5 minutos).
# 5. Guarde y entregue (2 minutos).
# 
# Modifique solo nombre, respuestas y la expresión pendiente. Use `Shift + Enter`.
# No borre celdas. El mensaje PENDIENTE indica que falta su implementación, no es una solución.
# Si cambia la función, reejecute las celdas desde arriba. No redondee cálculos ni cambie
# el punto o los pasos. La notación `1e-5` significa diez elevado a menos cinco.

# P0. Antes de ejecutar: ¿qué dos cantidades se comparan al verificar un gradiente? ¿Un h menor siempre mejora la aproximación? Justifique y conserve su predicción.
#
# PREDICCION (escrita antes de ejecutar):
# Se comparan dos cantidades: (1) el gradiente numerico g_num, obtenido por diferencias
# centrales evaluando solo la funcion f en w+h y w-h, y (2) el gradiente candidato, calculado
# analiticamente (aqui g_A o g_B). La comparacion es valida porque g_num es evidencia
# independiente: no usa la formula de la derivada.
#
# No, un h menor NO siempre mejora la aproximacion. Predigo dos efectos opuestos:
#   - Error de truncamiento: baja al reducir h (la diferencia central es O(h^2)).
#   - Error de redondeo: SUBE al reducir h, porque f(w+h) y f(w-h) se vuelven casi iguales
#     y al restarlos se cancelan las cifras significativas, dividiendo luego entre un 2h
#     minusculo que amplifica el ruido.
# Por tanto espero un h intermedio optimo. Predigo que con h = 1e-16 el resultado sera
# inservible: 2.0 + 1e-16 no es representable como distinto de 2.0 en float de 53 bits de
# mantisa, asi que w+h y w-h quedaran almacenados como el mismo numero, el numerador dara
# exactamente 0 y g_num sera 0 por un problema de representacion, no porque la derivada
# real valga cero.

# ## Función y candidatos proporcionados
# $$f(w)=w^3-2w,\qquad g_A(w)=3w^2-2,\qquad g_B(w)=3w-2.$$
# Compruebe en **w = 2** usando diferencias centrales con los tres pasos proporcionados.
# El objetivo es obtener evidencia independiente de los candidatos: no llame a sus
# funciones para calcular la aproximación numérica ni devuelva un valor fijo.

import csv
import math
import sys
from pathlib import Path

# Funciones y configuración proporcionadas. No modificar.
def funcion(w):
    return w**3 - 2*w

def gradiente_A(w):
    return 3*w**2 - 2

def gradiente_B(w):
    return 3*w - 2

w = 2.0
pasos = (1e-1, 1e-5, 1e-16)
assert sys.float_info.radix == 2 and sys.float_info.mant_dig == 53, "Se requiere float binario de doble precisión. Consulte al docente."
print("Entorno preparado: float binario de doble precisión, sin bibliotecas externas.")

# ## Complete su función
# Sustituya `...` por una expresión que use la función recibida `f`, el punto `w` y el paso `h`.
# Debe devolver la aproximación por diferencias centrales estudiada en la lectura.
# Conserve el resto de esta celda: la guarda solo permite mostrar PENDIENTE si falta su expresión.

def diferencia_central(f, w, h):
    aproximacion = (f(w + h) - f(w - h)) / (2 * h)  # diferencia central
    if aproximacion is Ellipsis:
        return None
    return aproximacion

# ## Obtenga la evidencia
# El código imprime `g_num`, los candidatos y sus discrepancias **absolutas** con la
# aproximación: `abs(g_num - g_candidato)`. Estas columnas permiten comparar este caso
# de escala fija; no son una regla universal de validación. La segunda tabla muestra
# los puntos perturbados y una comparación de igualdad de los valores almacenados.

# Código proporcionado. Usa su función; no la sustituye por una solución.
resultados = []
print(f"{'h':>10} {'g_num':>18} {'g_A':>8} {'g_B':>8} {'discrep_A':>14} {'discrep_B':>14}")
for h in pasos:
    g = diferencia_central(funcion, w, h)
    if g is None:
        print(f"{h:10.0e}  PENDIENTE: complete diferencia_central y reejecute desde arriba.")
        continue
    if not isinstance(g, (float, int)) or not math.isfinite(g):
        raise ValueError("La función debe devolver un número real finito para estos casos.")
    a, b = gradiente_A(w), gradiente_B(w)
    fila = dict(h=h, g_num=g, g_A=a, g_B=b,
                discrep_A=abs(g-a), discrep_B=abs(g-b),
                w_mas_h=w+h, w_menos_h=w-h, puntos_iguales=(w+h == w-h))
    resultados.append(fila)
    print(f"{h:10.0e} {g:18.12g} {a:8.4g} {b:8.4g} {abs(g-a):14.6e} {abs(g-b):14.6e}")

print("\nPuntos almacenados (17 cifras significativas; no se redondean los cálculos):")
print(f"{'h':>10} {'w + h':>23} {'w - h':>23} {'¿iguales?':>11}")
for h in pasos:
    print(f"{h:10.0e} {w+h:23.17g} {w-h:23.17g} {str(w+h == w-h):>11}")

if len(resultados) == len(pasos):
    destino = Path("resultados_control_3.csv")
    with destino.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(resultados[0]))
        escritor.writeheader()
        escritor.writerows(resultados)
    print("\nResultados guardados. Su existencia no certifica que la función o las respuestas sean correctas.")
else:
    print("\nACTIVIDAD INCOMPLETA. No se ha generado un CSV nuevo; un archivo anterior no acredita este intento.")

# P1. ¿Qué candidato respalda una fila fiable? Cite h, la aproximación y ambas discrepancias para justificar su elección.
#
# La evidencia respalda al candidato A, g_A(w) = 3w^2 - 2.
#
# La fila fiable es la de h = 1e-5, el paso intermedio: es lo bastante pequeno para que el
# error de truncamiento sea despreciable y lo bastante grande para que w+h y w-h sigan
# siendo numeros distintos en memoria (la tabla de puntos almacenados lo confirma:
# w+h = 2.0000100000000001, w-h = 1.9999899999999999, ¿iguales? False).
#
#   h = 1e-5   g_num = 10.0000000002   (aprox.)
#              g_A(2) = 10.0   ->  discrep_A = 1.987388e-10
#              g_B(2) =  4.0   ->  discrep_B = 6.000000e+00
#
# La discrepancia con A es del orden de 1e-10, compatible con el error residual esperado del
# metodo; la discrepancia con B es de 6.0, un orden de magnitud comparable al propio valor
# del gradiente, es decir, un desacuerdo total.
#
# La fila h = 1e-1 apunta en la misma direccion (g_num = 10.01, discrep_A = 1.0e-2 frente a
# discrep_B = 6.01), aunque su discrepancia con A es mayor porque ahi domina el error de
# truncamiento. La fila h = 1e-16 NO sirve como evidencia (ver P2).
#
# Nota: esta pequena discrepancia apoya la compatibilidad local de g_A en w = 2; no
# constituye una prueba de igualdad exacta ni una tolerancia universal (ver P3).

# P2. Compare el menor h con el intermedio: aproximación, w + h y w - h. Explique la causa del cambio y contraste con P0.
#
#   h = 1e-5    g_num = 10.0000000002   w+h = 2.0000100000000001   w-h = 1.9999899999999999   iguales? False
#   h = 1e-16   g_num = 0.0             w+h = 2                    w-h = 2                    iguales? True
#
# CAUSA. El paso mas pequeno da un resultado peor, no mejor. Un float de doble precision
# tiene 53 bits de mantisa, asi que cerca de 2.0 el espaciado entre numeros representables
# consecutivos (el ULP) es de orden 2^-51 ~ 4.4e-16, mayor que h = 1e-16. Al calcular 2.0 +
# 1e-16 el resultado se redondea de vuelta al mismo float 2.0, y lo mismo ocurre con 2.0 -
# 1e-16. Los dos puntos, matematicamente distintos, quedan almacenados como el MISMO valor:
# la columna ¿iguales? lo confirma con True. Entonces f(w+h) - f(w-h) = 0 exactamente, y
# g_num = 0 / (2e-16) = 0.
#
# Ese 0 es un artefacto de la representacion en punto flotante, no una afirmacion sobre la
# derivada: la derivada real en w = 2 vale 10. Notese ademas que con h = 1e-16 la
# discrepancia menor corresponde a B (4.0 frente a 10.0 de A), lo que llevaria a elegir el
# candidato equivocado si se tomara esa fila como evidencia. Una fila numericamente
# degenerada puede parecer que "favorece" al candidato incorrecto.
#
# CONTRASTE CON P0. Mi prediccion se confirma. Anticipe que un h menor no siempre mejora,
# por la competencia entre error de truncamiento y error de redondeo, y que 1e-16 colapsaria
# a numerador cero por representacion. Los tres pasos muestran ese comportamiento no
# monotono: 1e-1 tiene discrepancia 1e-2 (domina el truncamiento), 1e-5 alcanza 2e-10 (mejor
# equilibrio) y 1e-16 se degrada por completo (domina la cancelacion). El optimo esta en un h
# intermedio, no en el mas pequeno posible.

# P3. ¿Coincidir en w = 2 demuestra corrección para cualquier entrada? Justifique y proponga otra comprobación, sin programarla.
#
# No. Coincidir en un solo punto no demuestra correccion general: es evidencia LOCAL, no una
# certificacion de la implementacion. La comprobacion solo dice que ambas funciones toman
# valores compatibles en w = 2, no que sean la misma funcion.
#
# El propio w = 2 lo ilustra bien. Un candidato erroneo puede coincidir por casualidad en
# puntos aislados: g_A(w) = 3w^2 - 2 y g_B(w) = 3w - 2 son iguales justo donde 3w^2 = 3w, es
# decir en w = 0 y w = 1. Si el control se hubiera hecho en w = 1, ambos candidatos habrian
# dado 1 y la prueba no habria distinguido nada, pese a que B es incorrecto. Pasar en un
# punto es condicion necesaria, no suficiente.
#
# OTRA COMPROBACION PROPUESTA (sin programarla). Repetir la verificacion en varios puntos
# elegidos deliberadamente distintos entre si, con al menos un valor negativo y evitando los
# puntos de coincidencia accidental: por ejemplo w = -3, w = 0.5 y w = 4. En cada punto se
# usaria de nuevo un h intermedio (del orden de 1e-5, escalado al tamano de w para que w+h y
# w-h sigan siendo distintos en memoria) y se compararian ambas discrepancias. Se exigiria
# que el candidato mantenga discrepancia pequena en TODOS los puntos; basta un punto con
# desacuerdo claro para descartarlo. En w = -3, por ejemplo, g_A daria 25 y g_B daria -11,
# valores muy separados, de modo que el punto es informativo.
#
# Complementariamente, y como indica la lectura, si el problema tuviera varios parametros se
# perturbaria una componente cada vez manteniendo las demas y los datos fijos, comprobando
# asi una componente del gradiente por vez.

# ## Entrega y evaluación
# Reinicie el kernel, ejecute todo y guarde. Entregue este notebook con su nombre, función,
# tablas y respuestas P0 a P3, junto con `resultados_control_3.csv`.
# Si usa la alternativa `.py`, entregue el script con las respuestas y el CSV.
# Si no termina, conserve su trabajo parcial e indique qué falta.
# 
# Se evalúan implementación (30%), evidencia (30%) e interpretación (40%). Una predicción
# inicialmente incorrecta puede recibir crédito si está razonada y se contrasta honestamente.
# El programa no califica sus respuestas ni verifica el orden en que las escribió.
# Los resultados y las respuestas deben corresponder a esta ejecución, no a un CSV anterior.
