import os
import time
import uuid
import json

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Servico de Inferencia")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
fila = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class Entrada(BaseModel):
    texto: str


@app.get("/saude")
def saude():
    return {"status": "ok", "servico": "inferencia"}


@app.post("/predict")
def predict(entrada: Entrada):
    tarefa_id = str(uuid.uuid4())

    tarefa = {
        "id": tarefa_id,
        "texto": entrada.texto
    }

    try:
        fila.rpush("fila:inferencia", json.dumps(tarefa))

        limite = time.monotonic() + 25

        while time.monotonic() < limite:
            resultado = fila.blpop(f"resultado:{tarefa_id}", timeout=1)

            if resultado:
                return json.loads(resultado[1])

        raise HTTPException(
            status_code=504,
            detail="Tempo limite aguardando o processamento"
        )

    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Fila Redis indisponivel"
        )