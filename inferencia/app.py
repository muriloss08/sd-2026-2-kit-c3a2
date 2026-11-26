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

# Aplicacao e instrumentacao automatica HTTP/cliente
app = FastAPI(title="Servico de Inferencia")

FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

# Parametros de conexao e configuracao vetorial via ambiente
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLECAO = "textos"
DIMENSAO_VETOR = 16

# Conexao com o Redis usada para fila de tarefas e recebimento de respostas
fila = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class Entrada(BaseModel):
    texto: str


def gerar_vetor(texto):
    """Gera uma representacao numerica demonstrativa do texto."""
    # Normaliza acentos e caixa antes de extrair os termos
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )

    palavras = re.findall(r"\w+", texto)
    vetor = [0.0] * DIMENSAO_VETOR

    # Mapeia cada palavra para um indice e sinal via hash SHA-256
    for palavra in palavras:
        hash_palavra = hashlib.sha256(palavra.encode("utf-8")).digest()
        indice = int.from_bytes(hash_palavra[:4], "big") % DIMENSAO_VETOR
        sinal = 1.0 if hash_palavra[4] % 2 == 0 else -1.0
        vetor[indice] += sinal

    # Normaliza o vetor pela norma euclidiana quando nao for nulo
    norma = math.sqrt(sum(valor * valor for valor in vetor))

    if norma > 0:
        vetor = [valor / norma for valor in vetor]

    return vetor


def preparar_qdrant():
    # Garante que a colecao exista no Qdrant antes de ler ou gravar pontos
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
    # Persiste o vetor e os metadados da tarefa no Qdrant
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
    # Endpoint simples de verificacao de saude do servico
    return {
        "status": "ok",
        "servico": "inferencia"
    }


@app.post("/predict")
def predict(entrada: Entrada):
    # Abre o span principal de processamento da tarefa na inferencia
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
            # Enfileira a tarefa para consumo assincrono pelo worker
            fila.rpush("fila:inferencia", json.dumps(tarefa))

            span.add_event("Tarefa enviada para Redis")

            # Aguarda o resultado da tarefa ate o limite de 25 segundos
            limite = time.monotonic() + 25

            while time.monotonic() < limite:
                resultado = fila.blpop(
                    f"resultado:{tarefa_id}",
                    timeout=1
                )

                if resultado:
                    dados = json.loads(resultado[1])

                    # Registra o armazenamento vetorial em um sub-span proprio
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
    # Consulta textos similares no Qdrant a partir do vetor da consulta
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
