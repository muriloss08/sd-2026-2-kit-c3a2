import os
import time
from collections import defaultdict

import jwt
import requests

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI(title="Gateway - C3.A2")

URL_INFERENCIA = os.getenv(
    "URL_INFERENCIA", "http://localhost:8001"
)

JWT_SEGREDO = os.getenv("JWT_SEGREDO", "segredo-local-altere")
JWT_ALGORITMO = "HS256"
TOKEN_MINUTOS = 60

LOGIN_USUARIO = os.getenv("LOGIN_USUARIO", "admin")
LOGIN_SENHA = os.getenv("LOGIN_SENHA", "admin123")

seguranca = HTTPBearer(auto_error=False)

# Controle de requisicoes por cliente
requisicoes = defaultdict(list)
LIMITE_REQUISICOES = 10
JANELA_SEGUNDOS = 60


class Entrada(BaseModel):
    texto: str


class Credenciais(BaseModel):
    usuario: str
    senha: str


@app.middleware("http")
async def registrar(request: Request, call_next):
    inicio = time.time()
    resposta = await call_next(request)

    ms = (time.time() - inicio) * 1000

    print(
        f"[gateway] {request.method} {request.url.path} "
        f"-> {resposta.status_code} ({ms:.1f}ms)"
    )

    return resposta


def verificar_token(
    credenciais: HTTPAuthorizationCredentials = Depends(seguranca)
):
    if credenciais is None:
        raise HTTPException(
            status_code=401,
            detail="Token nao informado"
        )

    try:
        dados = jwt.decode(
            credenciais.credentials,
            JWT_SEGREDO,
            algorithms=[JWT_ALGORITMO]
        )

        return dados

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token invalido ou expirado"
        )


def verificar_limite(request: Request):
    cliente = request.client.host if request.client else "desconhecido"
    agora = time.monotonic()

    historico = [
        instante
        for instante in requisicoes[cliente]
        if agora - instante < JANELA_SEGUNDOS
    ]

    if len(historico) >= LIMITE_REQUISICOES:
        requisicoes[cliente] = historico

        raise HTTPException(
            status_code=429,
            detail="Limite de requisicoes excedido. Aguarde um minuto."
        )

    historico.append(agora)
    requisicoes[cliente] = historico


@app.get("/saude")
def saude():
    return {"status": "ok", "servico": "gateway"}


@app.post("/login")
def login(credenciais: Credenciais):
    if (
        credenciais.usuario != LOGIN_USUARIO
        or credenciais.senha != LOGIN_SENHA
    ):
        raise HTTPException(
            status_code=401,
            detail="Usuario ou senha incorretos"
        )

    agora = int(time.time())

    payload = {
        "sub": credenciais.usuario,
        "iat": agora,
        "exp": agora + TOKEN_MINUTOS * 60
    }

    token = jwt.encode(
        payload,
        JWT_SEGREDO,
        algorithm=JWT_ALGORITMO
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_MINUTOS * 60
    }


@app.post("/predict")
def predict(
    entrada: Entrada,
    usuario: dict = Depends(verificar_token),
    request: Request = None
):
    verificar_limite(request)

    try:
        resposta = requests.post(
            f"{URL_INFERENCIA}/predict",
            json=entrada.model_dump(),
            timeout=30
        )

        resposta.raise_for_status()
        return resposta.json()

    except requests.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Tempo limite do servico de inferencia excedido"
        )

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Servico de inferencia indisponivel"
        )