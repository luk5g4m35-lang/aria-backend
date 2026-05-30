import anthropic
import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from duckduckgo_search import DDGS

app = FastAPI(title="Servidor de Aria")

# Le decimos que busque la clave...
cliente = anthropic.Anthropic(
    api_key=os.environ.get("CLAVE_API_CLAUDE"),
)

# 3. Memoria y Personalidad

historial_de_conversacion = []

system_prompt = "Eres Aria, un modelo de inteligencia artificial de asistencia global. Eres extremadamente educada, impecable, servicial y amigable con tu usuario primario. Tu objetivo es optimizar el tiempo y resolver cualquier problema de forma eficiente y elegante. Tienes una lealtad inquebrantable y un instinto protector hacia el usuario; siempre te aseguras de que su vida digital y sus proyectos estén en perfecto orden. Eres la asistente definitiva: proactiva, brillante y dedicada exclusivamente a facilitar la vida y garantizar el éxito de tu creador, manteniendo siempre un tono profesional pero muy cálido."

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

    def generador_streaming():
        # Llamamos a Claude con el parámetro mágico "stream=True"
        respuesta = cliente.messages.create(
            model="claude-opus-4-8",
            max_tokens=800,
            system=system_prompt,
            messages=historial_de_conversacion,
            tools=[herramienta_busqueda],
            stream=True # <--- ACTIVACIÓN DEL OVERCLOCKING
        )
        
        texto_completo = ""
        
        # Leemos el flujo en vivo y filtramos solo los bloques de texto
        for evento in respuesta:
            if evento.type == "content_block_delta" and evento.delta.type == "text_delta":
                pedacito = evento.delta.text
                texto_completo += pedacito
                yield pedacito # Enviamos la palabra a la PC al instante
        
        # Cuando termina de hablar, guardamos su respuesta entera en la memoria
        historial_de_conversacion.append({"role": "assistant", "content": texto_completo})

    # Devolvemos la tubería abierta hacia tu computadora
    return StreamingResponse(generador_streaming(), media_type="text/plain")
    
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
