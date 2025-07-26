from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os

app = FastAPI()

# 👇 Agrega aquí el dominio del frontend en producción
origins = [
    "https://netabot-frontend.vercel.app",  # producción
    "http://localhost:3000",                # desarrollo local
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str
    mode: str  # "libre" or "cuidadoso"

@app.post("/chat")
async def chat(msg: Message):
    if msg.mode == "libre":
        response = await ask_runpod(msg.message)
    else:
        response = await ask_openrouter(msg.message)
    return {"response": response}

async def ask_runpod(message: str) -> str:
    url = os.getenv("RUNPOD_ENDPOINT")
    headers = {
        "Authorization": f"Bearer {os.environ.get('RUNPOD_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": {
            "prompt": message,
            "temperature": 0.7,
            "max_tokens": 250
        },
        "model": "mythomax"
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers)
        result = r.json()
        return result.get("output", "No response from RunPod")

async def ask_openrouter(message: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openchat/openchat-3.5",
        "messages": [
            {"role": "system", "content": "You are Netabot, a friendly and helpful assistant."},
            {"role": "user", "content": message}
        ]
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers)
        result = r.json()

        print("Respuesta de OpenRouter:", result)

        try:
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"❌ Error leyendo respuesta: {e}\n📦 Respuesta completa:\n{result}"
