from dotenv import load_dotenv; load_dotenv()      # LANGFUSE_* y OPENAI_* del .env
from langfuse import observe, get_client
from langfuse.openai import OpenAI                   # el cliente de OpenAI, con trazas

llm = OpenAI()
MODELO = llm.models.list().data[0].id                # el que sirve el servidor

@observe(name="contar_palabras", as_type="tool")
def contar_palabras(texto):
    return len(texto.split())

@observe(name="resumir")                             # la raíz: una traza por llamada
def resumir(texto):
    r = llm.chat.completions.create(model=MODELO, name="llm_resumir",
        messages=[{"role": "user", "content": f"Resume en una frase: {texto}"}])
    resumen = r.choices[0].message.content
    return resumen, contar_palabras(resumen)

print(resumir("Langfuse guarda trazas y observations de una aplicación con LLM."))
get_client().flush()                                 # enviar antes de terminar
