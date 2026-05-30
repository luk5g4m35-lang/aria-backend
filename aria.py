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
    historial_de_conversacion.append({"role": "user", "content": entrada.mensaje})

    def generador_streaming():
        try:
            # Usamos el motor de streaming nativo y blindado de Anthropic
            with cliente.messages.stream(
                model="claude-3-haiku-20240307", # <--- EL NÚCLEO MÁS RÁPIDO DEL MUNDO
                max_tokens=800,
                system=system_prompt,
                messages=historial_de_conversacion
            ) as stream:
                texto_completo = ""
                # Transmitimos cada sílaba en tiempo real
                for texto in stream.text_stream:
                    texto_completo += texto
                    yield texto
                
                # Guardamos en la memoria cuando termina
                historial_de_conversacion.append({"role": "assistant", "content": texto_completo})
                
        except Exception as e:
            # Si el servidor colapsa, enviamos el error a la pantalla de tu PC
            yield f"\n\n[! FALLO DEL NÚCLEO DE LA IA !] Detalles: {str(e)}"

    # Mantenemos la tubería abierta
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
