# Demo de la sesión 17 — observabilidad con Langfuse

Un asistente mínimo que responde preguntas sobre el calendario de la semana 4: un buscador de
cuatro filas (*retriever*) y una llamada al modelo (*generation*). Es más pequeño que el agente
del Lab 04 a propósito: aquí se mira la traza, no el agente. Diez minutos en clase.

Probado el **2026-10-06** con `langfuse` **4.17.0** (SDK de Python, ≥ 3.10), Langfuse **4.50.0**
(servidor, Docker) y `openai` 3.22.1, contra el vLLM de la H200.

## Antes de clase (una vez)

```bash
pip install -r requirements.txt     # en un venv con Python 3.11+
./levantar_langfuse.sh              # la primera vez baja ~4 GB de imágenes
```

`levantar_langfuse.sh` baja el `docker-compose.yml` oficial en la versión fijada, quita los
puertos de los servicios internos (para no chocar con un Postgres local), genera los secretos
y crea el proyecto `demo-s17` con sus claves y un usuario —sin pasar por la interfaz— en
`.langfuse/.env`, y escribe en `./.env` las tres variables `LANGFUSE_*`. Los dos `.env` están
en `.gitignore`.

Añade a `./.env` el modelo, igual que en el Lab 03:

```
OPENAI_BASE_URL=http://<host de la H200>:12555/v1
OPENAI_API_KEY=<la del laboratorio>
```

Sin VPN, cualquier servidor compatible con OpenAI sirve; con Ollama local,
`OPENAI_BASE_URL=http://localhost:11434/v1` y `OPENAI_API_KEY=ollama`. El modelo no se escribe:
`demo.py` le pregunta al servidor cuál sirve.

Interfaz: <http://localhost:3000>, usuario `profesor@demo.local`, contraseña en la línea
`LANGFUSE_INIT_USER_PASSWORD` de `.langfuse/.env`.

## El guion (comprobado en la interfaz de Langfuse 4.50.0 el 2026-10-06)

`python demo.py` sin nada muestra el menú; cada paso se pide por número o por nombre
(`python demo.py 3` = `python demo.py trazas`). Si al `.env` le falta algo, lo dice y no se cae;
la plantilla es `.env.example`. Desde el 2026-10-06 por la noche `trazas` registra el prompt si
no existe —antes se rompía con `NotFoundError` si iba antes de `prompts` o tras un `--borrar`—, y
repetir `prompts` ya no duplica versiones.

Dos ventanas lado a lado: la terminal en esta carpeta y el navegador en
<http://localhost:3000> con la sesión iniciada → **Go to project** en «Demo sesion 17». Todos los
comandos con `.venv/bin/python`.

| Paso | Comando | Dónde mirar | Qué decir |
|---|---|---|---|
| 1 | `demo.py 1` (sin-trazas) | solo la terminal | cinco respuestas; ¿cuál tardó más, cuánto gastó, con qué prompt, cuál falló? Ninguna tiene respuesta. La de Mongolia es plausible, falsa para el producto y HTTP 200 |
| 2 | `demo.py 2` (prompts) | menú **Prompts** → `asistente-calendario`, pestaña **Versions** | #1 con `production`, #2 con `candidata` y `latest`; cada una con su mensaje de cambio. Desplegar = mover una etiqueta |
| 3 | `demo.py 3` (trazas) | menú **Tracing**: una fila por traza (`responder`). Clic en la de Mongolia (la última de las cinco) | arriba: duración, **tokens**, la sesión y el score **`contiene_dato 0.00`**; a la izquierda el árbol `responder` → `buscar_contexto` + `redactar` |
| 3b | — | en el panel, el selector **Tree** → **Timeline**, y **Show labels** | la barra de `redactar` es casi toda la duración; la búsqueda, 0 ms |
| 3c | — | clic en `redactar` | el modelo, el chip **Prompt: asistente-calendario - v1** (lleva al prompt), el *System* con la tabla entera como contexto: por eso gasta más entrada |
| 4 | `demo.py 4` (= `trazas candidata`) | **Prompts** → `asistente-calendario` → pestaña **Metrics** | una fila por versión: latencia, tokens de entrada y salida, generaciones y **`contiene_dato` promedio** (en la prueba, v1 Ø 0,80 y v2 Ø 1,00). Ésa es la comparación de versiones |
| 5 | `demo.py 5` (= `promover 2`) | **Prompts** → Versions | `production` pasó a la #2 sin tocar código; `promover 1` es el rollback |
| 6 | `demo.py 6` (falla) | **Tracing** → `responder_con_herramienta` | la respuesta salió bien (HTTP 200) y la tool `consultar_calendario_remoto` está en **ERROR** con su mensaje; el *Input* dice `Soy <CORREO>`: la máscara corrió antes de enviar |
| 7 | `python ../../../labs/Lab-04-LLMOps/exportar_trazas.py --tag demo-s17 -o spans_demo.jsonl` y `resumir_trazas.py spans_demo.jsonl` | la terminal | lo mismo, de vuelta en un archivo: lo que se entrega en el Taller 4 |

Otras vistas para las preguntas: **Sessions** agrupa por `demo-production`, `demo-candidata` y
`demo-falla`; el filtro de la izquierda de **Tracing** (*Name*, *Type*, *Trace Tags*) y los
atajos **Slow** y **Cost**; y arriba a la derecha el rango de fechas (*Past 1 day*), que es lo
primero que hay que mirar si «no aparece nada».

Las cifras cambian de una corrida a otra —el modelo muestrea—; las de la diapositiva 32 del deck
son de la corrida del 2026-10-06 por la tarde.

Para repetir la demo desde cero: `./levantar_langfuse.sh --borrar` (pide escribir BORRAR) y otra vez
`./levantar_langfuse.sh`. **`--borrar` borra los volúmenes enteros: todos los proyectos del
servidor, no solo el de la demo**, y el que se creó a mano en la interfaz no vuelve (el de la
demo sí, con las mismas claves). Para apagar y conservar: `--apagar`.

## Lo que la demo enseña sin decirlo

- **El servidor 4.x no lista trazas por la API pública** (modo *events_only*: `GET
  /api/public/traces` responde 404). La consulta que funciona es la de *observations* v2, y es
  la que usa `exportar_trazas.py`.
- **La máscara tiene que recorrer tuplas.** `@observe` guarda los argumentos como
  `{"args": (…), "kwargs": {…}}`; una máscara que solo mira listas dejó pasar el correo sin
  ningún aviso. Se ve en el paso 5 si se quita `tuple` de `enmascarar`.
- **Los tokens de razonamiento se registran solos** con `langfuse.openai`: el modelo de la H200
  razona y esos tokens se cobran como salida.
- **Docker Compose es para probar**: «lacks high-availability, scaling capabilities, and backup
  functionality» (fuentes/web/fuentes-web.md, «Consultadas el 2026-10-06»).
