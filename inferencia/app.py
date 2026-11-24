
import os
import time
import uuid
import json
import hashlib
import math
import re
import unicodedata

import redis
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# OpenTelemetry
from opentelemetry import trace, propagate
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


# Configuracao do rastreamento
recurso = Resource.create({
    "service.name": os.getenv("OTEL_SERVICE_NAME", "inferencia")
})

provedor = TracerProvider(resource=recurso)
exportador = OTLPSpanExporter()
provedor.add_span_processor(BatchSpanProcessor(exportador))
trace.set_tracer_provider(provedor)

tracer = trace.get_tracer(__name__)

# Aplicacao
app = FastAPI(title="Servico de Inferencia")

FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLECAO = "textos"
DIMENSAO_VETOR = 16

fila = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class Entrada(BaseModel):
    texto: str


def gerar_vetor(texto):
    """Gera uma representacao numerica demonstrativa do texto."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )

    palavras = re.findall(r"\w+", texto)
    vetor = [0.0] * DIMENSAO_VETOR

    for palavra in palavras:
        hash_palavra = hashlib.sha256(palavra.encode("utf-8")).digest()
        indice = int.from_bytes(hash_palavra[:4], "big") % DIMENSAO_VETOR
        sinal = 1.0 if hash_palavra[4] % 2 == 0 else -1.0
        vetor[indice] += sinal

    norma = math.sqrt(sum(valor * valor for valor in vetor))

    if norma > 0:
        vetor = [valor / norma for valor in vetor]

    return vetor


def preparar_qdrant():
    url = f"{QDRANT_URL}/collections/{COLECAO}"
    resposta = requests.get(url, timeout=5)

    if resposta.status_code == 404:
        criacao = requests.put(
            url,
            json={
                "vectors": {
                    "size": DIMENSAO_VETOR,
                    "distance": "Cosine"
                }
            },
            timeout=10
        )
        criacao.raise_for_status()
    else:
        resposta.raise_for_status()


def salvar_vetor(tarefa_id, texto, resultado):
    preparar_qdrant()

    resposta = requests.put(
        f"{QDRANT_URL}/collections/{COLECAO}/points",
        params={"wait": "true"},
        json={
            "points": [
                {
                    "id": tarefa_id,
                    "vector": gerar_vetor(texto),
                    "payload": {
                        "texto": texto,
                        "resultado": resultado.get("resultado"),
                        "modelo": resultado.get("modelo")
                    }
                }
            ]
        },
        timeout=10
    )

    resposta.raise_for_status()


@app.get("/saude")
def saude():
    return {
        "status": "ok",
        "servico": "inferencia"
    }


@app.post("/predict")
def predict(entrada: Entrada):
    with tracer.start_as_current_span("inferencia.processar_tarefa") as span:
        tarefa_id = str(uuid.uuid4())

        span.set_attribute("tarefa.id", tarefa_id)
        span.set_attribute("fila.nome", "fila:inferencia")

        # Cria a tarefa e injeta o contexto atual do rastreamento.
        contexto_rastreio = {}
        propagate.inject(contexto_rastreio)

        tarefa = {
            "id": tarefa_id,
            "texto": entrada.texto,
            "trace_context": contexto_rastreio
        }

        try:
            fila.rpush("fila:inferencia", json.dumps(tarefa))

            span.add_event("Tarefa enviada para Redis")

            limite = time.monotonic() + 25

            while time.monotonic() < limite:
                resultado = fila.blpop(
                    f"resultado:{tarefa_id}",
                    timeout=1
                )

                if resultado:
                    dados = json.loads(resultado[1])

                    with tracer.start_as_current_span("inferencia.salvar_qdrant"):
                        salvar_vetor(tarefa_id, entrada.texto, dados)

                    dados["armazenamento_vetorial"] = "Qdrant"

                    span.add_event("Resultado recebido do Worker")
                    return dados

            raise HTTPException(
                status_code=504,
                detail="Tempo limite aguardando o processamento"
            )

        except redis.RedisError as erro:
            span.record_exception(erro)
            raise HTTPException(
                status_code=503,
                detail="Fila Redis indisponivel"
            )

        except requests.RequestException as erro:
            span.record_exception(erro)
            raise HTTPException(
                status_code=503,
                detail="Banco vetorial Qdrant indisponivel"
            )


@app.post("/buscar")
def buscar(entrada: Entrada):
    with tracer.start_as_current_span("inferencia.buscar_qdrant") as span:
        span.set_attribute("banco.nome", "Qdrant")

        try:
            preparar_qdrant()

            resposta = requests.post(
                f"{QDRANT_URL}/collections/{COLECAO}/points/search",
                json={
                    "vector": gerar_vetor(entrada.texto),
                    "limit": 5,
                    "with_payload": True
                },
                timeout=10
            )

            resposta.raise_for_status()

            span.add_event("Busca vetorial concluida")

            return {
                "consulta": entrada.texto,
                "resultados": resposta.json()["result"]
            }

        except requests.RequestException as erro:
            span.record_exception(erro)
            raise HTTPException(
                status_code=503,
                detail="Nao foi possivel consultar o Qdrant"
            )
