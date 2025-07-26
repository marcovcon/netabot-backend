import os

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

chat_modes = {
    "cuidadoso": {
        "name": "Cuidadoso",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        },
        "body": lambda message: {
            "model": "openchat/openchat-3.5",
            "messages": [
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": message}
            ]
        },
        "parse_response": lambda response: response["choices"][0]["message"]["content"]
    },
    "libre": {
        "name": "Libre",
        "api_url": "https://api.runpod.ai/v2/wj4t4xg8lb3819/run",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RUNPOD_API_KEY}"
        },
        "body": lambda message: {
            "input": {
                "prompt": message
            }
        },
        "parse_response": lambda response: response["output"]
    },
}