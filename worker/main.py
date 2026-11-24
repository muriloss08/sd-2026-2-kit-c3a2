
import os
import json
import time
import redis

# OpenTelemetry
from opentelemetry import trace, propagate
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


# Configuracao do rastreamento
recurso = Resource.create({
    "service.name": os.getenv("OTEL_SERVICE_NAME", "worker")
})

provedor = TracerProvider(resource=recurso)
exportador = OTLPSpanExporter()
provedor.add_span_processor(BatchSpanProcessor(exportador))
trace.set_tracer_provider(provedor)

tracer = trace.get_tracer(__name__)

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
fila = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def analisar_texto(texto):
    texto = texto.lower()

    positivas = [
        "excelente", "bom", "ótimo", "otimo", "maravilhoso"
    ]

    negativas = [
        "ruim", "péssimo", "pessimo", "horrível", "horrivel"
    ]

    if any(palavra in texto for palavra in positivas):
        sentimento = "positivo"
    elif any(palavra in texto for palavra in negativas):
        sentimento = "negativo"
    else:
        sentimento = "neutro"

    return sentimento


def executar():
    print("[worker] Aguardando tarefas na fila Redis...")

    while True:
        try:
            item = fila.brpop("fila:inferencia", timeout=5)

            if item is None:
                continue

            _, conteudo = item
            tarefa = json.loads(conteudo)

            tarefa_id = tarefa["id"]
            texto = tarefa["texto"]

            # Recupera o contexto enviado pela inferencia.
            contexto = propagate.extract(
                tarefa.get("trace_context", {})
            )

            # Cria um span vinculado ao rastreamento original.
            with tracer.start_as_current_span(
                "worker.processar_tarefa",
                context=contexto
            ) as span:

                span.set_attribute("tarefa.id", tarefa_id)
                span.set_attribute("fila.nome", "fila:inferencia")

                resultado = {
                    "id": tarefa_id,
                    "texto": texto,
                    "resultado": analisar_texto(texto),
                    "modelo": "simulado"
                }

                chave = f"resultado:{tarefa_id}"

                fila.lpush(chave, json.dumps(resultado))
                fila.expire(chave, 60)

                span.add_event("Tarefa processada e resultado enviado")

                print(
                    f"[worker] Tarefa processada: {tarefa_id}"
                )

        except redis.RedisError as erro:
            print(f"[worker] Erro no Redis: {erro}")
            time.sleep(2)

        except Exception as erro:
            print(f"[worker] Erro ao processar tarefa: {erro}")


if __name__ == "__main__":
    executar()
