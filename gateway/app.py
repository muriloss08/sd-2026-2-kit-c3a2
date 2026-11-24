
import os
import time
from collections import defaultdict

import jwt
import requests

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


# Configuracao do rastreamento
recurso = Resource.create({
    "service.name": os.getenv("OTEL_SERVICE_NAME", "gateway")
})

provedor = TracerProvider(resource=recurso)
exportador = OTLPSpanExporter()
provedor.add_span_processor(BatchSpanProcessor(exportador))
trace.set_tracer_provider(provedor)

tracer = trace.get_tracer(__name__)

# Aplicacao
app = FastAPI(title="Gateway - C3.A2")

FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

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

# Configuracao do Circuit Breaker
FALHAS_LIMITE = 3
TEMPO_ABERTO = 20

falhas_consecutivas = 0
circuito_aberto_ate = 0


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


def chamar_inferencia(caminho, dados):
    global falhas_consecutivas, circuito_aberto_ate

    with tracer.start_as_current_span("gateway.chamar_inferencia") as span:
        span.set_attribute("inferencia.endpoint", caminho)

        agora = time.monotonic()

        if agora < circuito_aberto_ate:
            restante = int(circuito_aberto_ate - agora)

            raise HTTPException(
                status_code=503,
                detail=f"Circuit Breaker aberto. Tente novamente em {restante + 1} segundos."
            )

        if circuito_aberto_ate:
            print("[gateway] Circuit Breaker em teste de recuperacao")

        ultimo_erro = None

        # Retry: ate 3 tentativas com espera progressiva
        for tentativa in range(3):
            try:
                span.set_attribute("retry.tentativa", tentativa + 1)

                resposta = requests.post(
                    f"{URL_INFERENCIA}{caminho}",
                    json=dados,
                    timeout=(3, 30)
                )

                if resposta.status_code >= 500:
                    resposta.raise_for_status()

                if resposta.status_code >= 400:
                    raise HTTPException(
                        status_code=resposta.status_code,
                        detail="Erro retornado pelo servico de inferencia"
                    )

                falhas_consecutivas = 0
                circuito_aberto_ate = 0

                span.set_attribute("inferencia.status", resposta.status_code)
                return resposta.json()

            except HTTPException:
                raise

            except requests.RequestException as erro:
                ultimo_erro = erro
                span.record_exception(erro)

                print(
                    f"[gateway] Falha na tentativa "
                    f"{tentativa + 1}/3: {erro}"
                )

                if tentativa < 2:
                    espera = 0.5 * (2 ** tentativa)
                    time.sleep(espera)

        # Registra uma falha apos esgotar as tentativas
        falhas_consecutivas += 1

        span.set_attribute("retry.falhas_consecutivas", falhas_consecutivas)

        print(
            f"[gateway] Falhas consecutivas: "
            f"{falhas_consecutivas}/{FALHAS_LIMITE}"
        )

        if falhas_consecutivas >= FALHAS_LIMITE:
            circuito_aberto_ate = time.monotonic() + TEMPO_ABERTO
            print("[gateway] Circuit Breaker ABERTO por 20 segundos")

        if isinstance(ultimo_erro, requests.Timeout):
            raise HTTPException(
                status_code=504,
                detail="Tempo limite do servico de inferencia excedido"
            )

        raise HTTPException(
            status_code=503,
            detail="Servico de inferencia indisponivel apos 3 tentativas"
        )


@app.get("/saude")
def saude():
    return {
        "status": "ok",
        "servico": "gateway"
    }


@app.get("/resiliencia")
def resiliencia():
    aberto = time.monotonic() < circuito_aberto_ate

    return {
        "circuit_breaker": "aberto" if aberto else "fechado",
        "falhas_consecutivas": falhas_consecutivas,
        "limite_falhas": FALHAS_LIMITE,
        "tempo_aberto_segundos": TEMPO_ABERTO
    }


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
    request: Request,
    entrada: Entrada,
    usuario: dict = Depends(verificar_token)
):
    verificar_limite(request)

    return chamar_inferencia(
        "/predict",
        entrada.model_dump()
    )


@app.post("/buscar")
def buscar(
    request: Request,
    entrada: Entrada,
    usuario: dict = Depends(verificar_token)
):
    verificar_limite(request)

    return chamar_inferencia(
        "/buscar",
        entrada.model_dump()
    )
