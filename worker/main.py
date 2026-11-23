import os
import json
import time

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
fila = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def analisar_texto(texto):
    texto = texto.lower()

    positivas = ["excelente", "bom", "Ã³timo", "otimo", "maravilhoso"]
    negativas = ["ruim", "pÃ©ssimo", "pessimo", "horrÃ­vel", "horrivel"]

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

            resultado = {
                "id": tarefa_id,
                "texto": texto,
                "resultado": analisar_texto(texto),
                "modelo": "simulado"
            }

            chave = f"resultado:{tarefa_id}"
            fila.lpush(chave, json.dumps(resultado))
            fila.expire(chave, 60)

            print(f"[worker] Tarefa processada: {tarefa_id}")

        except redis.RedisError as erro:
            print(f"[worker] Erro no Redis: {erro}")
            time.sleep(2)

        except Exception as erro:
            print(f"[worker] Erro ao processar tarefa: {erro}")


if __name__ == "__main__":
    executar()