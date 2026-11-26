# Serviço de Worker

Consumidor assíncrono em **Python** responsável por ler tarefas da fila `fila:inferencia` no **Redis**, executar a análise de sentimento do texto, devolver o resultado com expiração de 60 segundos e propagar o contexto de rastreamento distribuído via **OpenTelemetry**.

## Fluxo de processamento

1. Aguarda mensagens na lista `fila:inferencia` via `BRPOP`.
2. Extrai o `trace_context` enviado pelo serviço de Inferência e abre um span vinculado (`worker.processar_tarefa`).
3. Classifica o texto em `positivo`, `negativo` ou `neutro`.
4. Publica o JSON de resposta na chave `resultado:<tarefa_id>` no Redis com TTL de `60s`.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Endereço de conexão com a fila Redis |
| `OTEL_SERVICE_NAME` | `worker` | Nome do serviço exibido nos traces do OpenTelemetry/Jaeger |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | Endpoint OTLP HTTP para exportação dos spans |

## Execução com Docker

O container inicia o script `main.py` sem expor portas HTTP, operando na rede interna do `docker-compose.yml`:

```bash
docker build -t servico-worker .
docker run --env-file ../.env servico-worker