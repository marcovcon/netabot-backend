from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
import asyncio

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.netabot.com",
        "https://netabot.com",
        "https://netabot-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ENV
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT")  # p.ej. https://api.runpod.ai/v2/<id>/run

class MessageRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"message": "Netabot backend funcionando"}

def extract_text(output):
    """
    Intenta extraer texto de múltiples formatos posibles de RunPod.
    """
    if output is None:
        return None

    # 1) Si ya es string
    if isinstance(output, str):
        return output

    # 2) Diccionario con campos comunes
    if isinstance(output, dict):
        # Directos
        for key in ["text", "output_text", "generated_text", "response", "result"]:
            val = output.get(key)
            if isinstance(val, str) and val.strip():
                return val

        # OpenRouter-like / Chat API
        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            c0 = choices[0]
            if isinstance(c0, dict):
                # OpenAI-like
                msg = c0.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, str) and content.strip():
                        return content
                # Text
                if isinstance(c0.get("text"), str):
                    return c0["text"]
                # Tokens
                tokens = c0.get("tokens")
                if isinstance(tokens, list) and all(isinstance(t, str) for t in tokens):
                    return "".join(tokens)

        # Algunos wrappers devuelven "outputs" como lista de dicts
        outputs = output.get("outputs")
        if isinstance(outputs, list) and outputs:
            f = outputs[0]
            if isinstance(f, dict):
                for key in ["text", "generated_text", "output", "response"]:
                    val = f.get(key)
                    if isinstance(val, str) and val.strip():
                        return val

    # 3) Lista con strings o dicts
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str) and first.strip():
            return first
        if isinstance(first, dict):
            for key in ["text", "generated_text", "output", "response"]:
                val = first.get(key)
                if isinstance(val, str) and val.strip():
                    return val
            choices = first.get("choices")
            if isinstance(choices, list) and choices:
                c0 = choices[0]
                if isinstance(c0, dict):
                    if isinstance(c0.get("text"), str):
                        return c0["text"]
                    tokens = c0.get("tokens")
                    if isinstance(tokens, list) and all(isinstance(t, str) for t in tokens):
                        return "".join(tokens)

    return None

async def fetch_status(client: httpx.AsyncClient, job_id: str, headers: dict) -> dict:
    """
    Intenta obtener el status via:
    - GET /status/{id}
    - si falla, POST /status con {"id": id}
    """
    base = RUNPOD_ENDPOINT.rsplit("/", 1)[0]  # quita /run
    get_url = f"{base}/status/{job_id}"
    post_url = f"{base}/status"

    # Primero GET
    try:
        r = await client.get(get_url, headers=headers)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError:
        # Fallback a POST
        r = await client.post(post_url, headers=headers, json={"id": job_id})
        r.raise_for_status()
        return r.json()

@app.post("/chat")
async def chat_endpoint(data: MessageRequest):
    prompt = data.message.strip() if data.message else ""
    if not prompt:
        return {"response": "No se recibió ningún mensaje."}

    if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT:
        return {"response": "❌ Falta configuración de RUNPOD_API_KEY o RUNPOD_ENDPOINT en el backend."}

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
            "stop": ["</s>", "### Human:"],
        }
    }

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            # 1) Iniciar job
            start = await client.post(RUNPOD_ENDPOINT, json=payload, headers=headers)
            start.raise_for_status()
            start_json = start.json()
            job_id = start_json.get("id")
            if not job_id:
                return {"response": "❌ RunPod no devolvió un ID de trabajo."}

            # 2) Polling de status (máx. ~45s)
            for _ in range(45):
                status_data = await fetch_status(client, job_id, headers)
                status = status_data.get("status")

                if status == "COMPLETED":
                    output = status_data.get("output")
                    text = extract_text(output)
                    if text:
                        return {"response": text}
                    # Último intento: si el output viene como string o anidado raro
                    if isinstance(output, (dict, list)):
                        # Devuelve un resumen mínimo para depurar en caso extremo
                        return {"response": "(Modelo completó sin formato estándar)", "debug_keys": list(output.keys()) if isinstance(output, dict) else "list"}
                    return {"response": "(Modelo completó, pero sin salida legible)"}

                if status in ["FAILED", "CANCELLED"]:
                    return {"response": f"❌ Job {status.lower()} en RunPod."}

                await asyncio.sleep(1)

            return {"response": "❌ Tiempo de espera agotado para RunPod."}

    except httpx.HTTPStatusError as e:
        return {"response": f"❌ Error RunPod: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"response": f"❌ Error inesperado: {str(e)}"}

