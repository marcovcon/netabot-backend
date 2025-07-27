from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from pydantic import BaseModel


app = FastAPI()

# CORS para permitir acceso desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.netabot.com", "https://netabot.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno (deben estar definidas en Render)
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class MessageRequest(BaseModel):
    message: str
    mode: str


@app.get("/")
def root():
    return {"message": "Netabot backend funcionando"}

@app.post("/chat")
async def chat(req: MessageRequest):
    return {"response": f"Recibí tu mensaje: {req.message} en modo {req.mode}"}


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
