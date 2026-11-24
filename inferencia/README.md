# Serviço de Inferência

Microsserviço desenvolvido em **FastAPI** responsável por receber solicitações de inferência, enfileirar tarefas para processamento assíncrono no **Redis**, persistir e consultar embeddings no **Qdrant** e exportar rastreamento distribuído via **OpenTelemetry**.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/saude` | Verifica a disponibilidade do serviço |
| `POST` | `/predict` | Enfileira o texto no Redis, aguarda o processamento do Worker e indexa o vetor no Qdrant |
| `POST` | `/buscar` | Realiza busca por similaridade vetorial (cosine) no Qdrant |

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Endereço de conexão com a fila Redis |
| `QDRANT_URL` | `http://localhost:6333` | URL do banco vetorial Qdrant |
| `OTEL_SERVICE_NAME` | `inferencia` | Nome do serviço exibido nos traces do OpenTelemetry/Jaeger |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | Endpoint OTLP HTTP para exportação dos spans |

## Execução com Docker

O container expõe a porta **`8001`** e é orquestrado pelo `docker-compose.yml` na raiz do projeto:

```bash
docker build -t servico-inferencia .
docker run -p 8001:8001 --env-file ../.env servico-inferencia