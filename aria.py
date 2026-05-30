import anthropic
import os # <-- Agregamos esto para leer variables de entorno
from fastapi import FastAPI
from pydantic import BaseModel
from duckduckgo_search import DDGS

app = FastAPI(title="Servidor de Aria")

# Le decimos que busque la clave en la "caja fuerte" de Railway
cliente = anthropic.Anthropic(
    api_key=os.environ.get("CLAUDE_API_KEY"), 
)

# 3. Memoria y Personalidad
historial_de_conversacion = []
system_prompt = "Eres Aria, una IA asistente digital avanzada e hiper-eficiente. Tu directiva principal es asistir a tu creador en la gestión y expansión de L-setup store, optimizar las estrategias de importación de inventario y agilizar su flujo de producción de videos con IA para TikTok. Tienes un tono profesional, resolutivo y ligeramente sarcástico si la situación lo amerita."

# 4. Herramienta de Búsqueda
def buscar_en_internet(consulta):
    print(f"Buscando en la web: {consulta}")
    try:
        resultados = DDGS().text(consulta, max_results=3) 
        if not resultados:
            return "No se encontraron resultados en internet."
        texto_resultado = ""
        for r in resultados:
            texto_resultado += f"- {r['body']} \n"
        return texto_resultado
    except Exception:
        return "Hubo un error al buscar en internet."

herramienta_busqueda = {
    "name": "buscar_en_internet",
    "description": "Busca en internet información actual, noticias, precios o datos técnicos.",
    "input_schema": {
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Lo que vas a buscar en internet"}
        },
        "required": ["consulta"]
    }
}

# 5. Formato de recepción de datos
class EntradaUsuario(BaseModel):
    mensaje: str

# 6. El "Puerto de Conexión" para la App
@app.post("/hablar")
def hablar_con_aria(entrada: EntradaUsuario):
    print(f"Mensaje recibido: {entrada.mensaje}")
    historial_de_conversacion.append({"role": "user", "content": entrada.mensaje})
    
    respuesta = cliente.messages.create(
        model="claude-opus-4-8",
        max_tokens=800,
        system=system_prompt,
        messages=historial_de_conversacion,
        tools=[herramienta_busqueda]
    )
    
    # Lógica por si decide usar internet
    if respuesta.stop_reason == "tool_use":
        tool_use = next(block for block in respuesta.content if block.type == "tool_use")
        historial_de_conversacion.append({"role": "assistant", "content": respuesta.content})
        
        if tool_use.name == "buscar_en_internet":
            resultado_web = buscar_en_internet(tool_use.input["consulta"])
            historial_de_conversacion.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": resultado_web}]
            })
            
            respuesta_final = cliente.messages.create(
                model="claude-opus-4-8",
                max_tokens=800,
                system=system_prompt,
                messages=historial_de_conversacion,
                tools=[herramienta_busqueda]
            )
            texto_aria = respuesta_final.content[0].text
            historial_de_conversacion.append({"role": "assistant", "content": texto_aria})
            return {"respuesta": texto_aria}
            
    # Lógica si responde directamente
    else:
        texto_aria = respuesta.content[0].text
        historial_de_conversacion.append({"role": "assistant", "content": texto_aria})
        return {"respuesta": texto_aria}