# Informe individual — Ejercicio de la semana 2

**Estudiante:** Jaime Astudillo

Complete las respuestas con frases propias. Cite los resultados numéricos obtenidos por su programa. Una salida de software sin interpretación no constituye una respuesta.

## Parte 1. Contrato de análisis previo

Responda antes de ejecutar la comparación estadística.

1. ¿Qué dos modelos se comparan?

   **Respuesta:** Dos modelos de regresión ya entrenados, A y B, que pronostican la demanda semanal de las mismas 16 tiendas. Se comparan sus errores registrados en `data/model_errors.csv`, no sus arquitecturas.

2. ¿Qué población o proceso objetivo propone para interpretar el ejercicio? Aclare qué impide afirmar que los datos sintéticos representan realmente esa población.

   **Respuesta:** Propongo el pronóstico semanal de demanda en tiendas comparables a las 16 observadas. Lo impide la procedencia: los datos son sintéticos, no provienen de tiendas reales ni de un muestreo aleatorio de esa población. La inferencia se limita al conjunto observado.

3. ¿Cuál es la métrica principal y qué dirección representa un mejor resultado?

   **Respuesta:** El error absoluto de pronóstico por tienda, en unidades vendidas. Menor es mejor.

4. ¿Cuál es la unidad de análisis?

   **Respuesta:** La tienda, identificada por `store_id`. Cada una aporta una sola observación: su diferencia de error. Son n = 16 unidades, no 32, porque los dos errores de una tienda no son independientes.

5. ¿Por qué las observaciones están emparejadas y cómo verificará los pares?

   **Respuesta:** Porque ambos modelos se evaluaron sobre las mismas 16 tiendas y cada par comparte el contexto de su tienda, que se cancela al restar. Verificaré por `store_id` que sea único y no nulo, y calcularé la diferencia dentro de cada fila, no por el orden de dos vectores.

6. Defina el estimando y la diferencia por tienda. Explique qué significa una diferencia positiva.

   **Respuesta:** d_i = e_A(i) − e_B(i), en unidades vendidas; el estimando es Δ = E(d_i). Una diferencia positiva indica que A erró más que B en esa tienda: como menor error es mejor, favorece a B. Una negativa favorece a A.

7. Escriba la hipótesis nula y la alternativa bilateral.

   **Respuesta:** H₀: Δ = 0 (ningún modelo pronostica sistemáticamente mejor). H₁: Δ ≠ 0. Es bilateral porque antes de ver los datos no espero que gane un modelo en particular.

8. ¿Cuál será el procedimiento principal y qué supuestos requiere?

   **Respuesta:** Prueba t de una muestra sobre las 16 diferencias, bilateral, con intervalo t del 95 %. Supone independencia entre tiendas, diferencias aproximadamente normales (con n = 16 es sensible a atípicos) y varianza finita con pares bien construidos.

9. ¿Qué resultados reportará además del p-value?

   **Respuesta:** n, la diferencia media como efecto, la desviación muestral, el error estándar, el intervalo t del 95 %, el estadístico t con sus grados de libertad, el conteo de tiendas por modelo, la figura por tienda, el p-value por cambios de signo y el intervalo bootstrap.

10. ¿Qué afirmaciones no permite realizar este diseño?

    **Respuesta:** No permite generalizar a otras tiendas ni a un mercado real, ni atribuir causalmente la diferencia a una característica del modelo. Tampoco leer el p-value como probabilidad de que H₀ sea cierta, ni tomar un resultado no concluyente como prueba de equivalencia.

## Parte 2. Auditoría y evidencia por tienda

11. Confirme que los 16 pares fueron validados mediante `store_id`. Explique por qué comprobar únicamente que ambas columnas tienen la misma longitud no es suficiente.

    **Respuesta:** Confirmado: `load_model_errors` valida columnas, nulos y unicidad de `store_id`, y la resta se hace dentro de cada fila. La longitud no basta: 16 contra 16 es compatible con un desalineamiento, y si B llegara en otro orden se restarían tiendas distintas sin que nada lo delate.

12. Indique cuántas tiendas favorecen a A, cuántas favorecen a B y si existen empates. Identifique las diferencias de mayor magnitud en cada dirección.

    **Respuesta:** **10 favorecen a B** y **6 a A**, sin empates. La mayor a favor de B es **S08 (+2.1)** y la mayor a favor de A es **S09 (−1.8)**, las barras más largas de cada lado en `output/store_differences.png`. Hay mayoría para B, pero magnitudes del mismo orden en ambos lados.

## Parte 3. Efecto e incertidumbre

13. Reporte el número de tiendas, la diferencia media, la desviación estándar muestral y el error estándar. Interprete el signo y la magnitud de la diferencia media en unidades vendidas.

    **Respuesta:** n = **16**, media = **0.41875**, desviación muestral = **1.25338**, error estándar = **0.31334** (1.25338 / √16). El signo positivo indica que A erró más que B en promedio, a favor de B. La magnitud es pequeña: 0.42 unidades frente a errores de 7.2 a 16.0. La desviación mide la variación **entre tiendas**; el error estándar, la precisión de **la media**, y al ser comparable a ella la estimación es imprecisa.

14. Reporte el intervalo t del 95 %. Explique qué valores del efecto son compatibles con los datos bajo el modelo utilizado. No interprete el intervalo como una probabilidad posterior sobre el parámetro.

    **Respuesta:** IC 95 % = **(−0.24913, 1.08663)**, de 0.41875 ± 2.1314 × 0.31334 con 15 gl. Son compatibles desde ~0.25 unidades a favor de A hasta ~1.09 a favor de B; contiene el cero y descarta ventajas grandes. La lectura es sobre el procedimiento: al repetirlo, ~95 % de tales intervalos cubrirían el Δ verdadero. Δ es fijo: este intervalo lo contiene o no.

## Parte 4. Referencias nulas y sensibilidad

15. Reporte el estadístico t, sus grados de libertad y el p-value bilateral. Explique correctamente qué representa ese p-value.

    **Respuesta:** **t = 1.336388**, **15 gl**, **p = 0.201342**. Es condicional: bajo la nula y sus supuestos, es la probabilidad de un estadístico al menos tan extremo como el observado, en cualquier dirección. Datos así ocurrirían ~20 % de las veces si los modelos fueran equivalentes. **No** es la probabilidad de que H₀ sea verdadera.

16. Reporte el p-value de la prueba exacta por cambios de signo. Explique por qué esta referencia nula y la prueba t no tienen supuestos idénticos.

    **Respuesta:** De las **2¹⁶ = 65 536** configuraciones, **13 372** fueron al menos tan extremas: **p = 0.204041**. No son intercambiables: la t asume normalidad aproximada y usa una distribución t teórica; el sign-flip no asume forma distribucional sino **simetría alrededor de cero**, y construye su referencia por enumeración exacta. La cercanía numérica sugiere robustez, pero con datos asimétricos podrían discrepar.

17. Reporte el intervalo bootstrap pareado, la semilla y el número de remuestras. Explique por qué se remuestrean tiendas completas y qué problema no puede corregir automáticamente el bootstrap.

    **Respuesta:** IC percentil 95 % = **(−0.19375, 1.00625)**, semilla **20260829**, **10 000 remuestras**. Coherente con el IC t: más estrecho y también contiene el cero. Se remuestrean tiendas completas porque la unidad es la tienda; hacerlo por separado rompería los pares y su correlación, ensanchando el intervalo. El bootstrap solo remuestrea lo que ya está en la muestra: no repara sesgo de selección ni que los datos sean sintéticos.

## Parte 5. Informe ejecutivo

18. Redacte un máximo de 150 palabras que incluya unidad, procedencia, métrica, emparejamiento, efecto, incertidumbre, procedimiento, p-value, análisis de sensibilidad, al menos dos limitaciones y una afirmación explícita sobre lo que no puede concluirse.

**Informe:**

**Diseño.** Se compararon los modelos A y B sobre 16 tiendas, la unidad de análisis. Los datos son sintéticos, creados para esta actividad. La métrica es el error absoluto en unidades vendidas, donde menor es mejor. Los pares se validaron por `store_id`, restando dentro de cada fila.

**Efecto e incertidumbre.** B mejora en 10 tiendas y A en 6, sin empates. La diferencia media es 0.41875 unidades a favor de B, con error estándar 0.31334.

**Procedimiento y sensibilidad.** La prueba t pareada bilateral dio t = 1.336 (gl = 15), p = 0.2013 e intervalo (−0.2491, 1.0866), condicional a la nula y sus supuestos. El sign-flip exacto dio p = 0.2040 y el bootstrap pareado (10 000 remuestras, semilla 20260829) dio (−0.1938, 1.0063): las tres referencias cruzan el cero.

**Límites.** El n es pequeño y los datos no son reales. **No puede concluirse que B sea superior a A, ni que ambos modelos sean equivalentes.**

*(147 palabras)*
