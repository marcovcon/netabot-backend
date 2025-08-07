from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

# CORS para permitir acceso desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.netabot.com",
        "https://netabot.com",
        "https://netabot-frontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno necesarias
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Modelo de datos de entrada
class MessageRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"message": "Netabot backend funcionando"}

@app.post("/chat")
async def chat_endpoint(data: MessageRequest):
    prompt = data.message
    if not prompt:
        return {"response": "No se recibió ningún mensaje."}

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "input": {
            "prompt": prompt,
            "temperature": 0.8,
            "max_tokens": 300,
            "top_p": 0.9,
            "stop": ["</s>", "### Human:"]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(RUNPOD_ENDPOINT, json=payload, headers=headers)
            r.raise_for_status()
            result = r.json()

            # Extraer texto desde la respuesta del modelo
            output = result.get("output")
            if isinstance(output, list) and output:
                choices = output[0].get("choices", [])
                if choices and isinstance(choices[0], dict):
                    tokens = choices[0].get("tokens", [])
                    response_text = "".join(tokens)
                    return {"response": response_text or "(Sin respuesta del modelo)"}

            return {"response": "(No se pudo interpretar la respuesta del modelo)."}

    except httpx.HTTPStatusError as e:
        return {"response": f"❌ Error RunPod: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"response": f"❌ Error inesperado: {str(e)}"}

@app.post("/runpod")
async def runpod():
    if not RUNPOD_API_KEY:
        return {"error": "RUNPOD_API_KEY no configurada"}
    return {"message": "runpod endpoint funcionando correctamente", "api_key": RUNPOD_API_KEY[:4] + "..."}

@app.post("/openrouter")
async def openrouter():
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY no configurada"}
    return {"message": "openrouter endpoint funcionando correctamente", "api_key": OPENROUTER_API_KEY[:4] + "..."}
