# Plataforma de IA como Serviço — C3.A2

| Campo | Informação |
|---|---|
| **Disciplina** | Sistemas Distribuídos e Computação em Nuvem |
| **Instituição** | FAESA |
| **Período** | 2026/2 |
| **Professor** | Howard Cruz Roatti |
| **Entrega** | 26/11/2026 |

---

## 1. Apresentação

Este projeto tem como objetivo desenvolver uma Plataforma de IA como Serviço utilizando uma arquitetura distribuída baseada em microsserviços.

A solução foi construída com serviços independentes responsáveis pela autenticação, processamento de solicitações, execução assíncrona de tarefas, armazenamento vetorial e monitoramento da comunicação entre componentes.

O projeto demonstra a aplicação prática de conceitos de sistemas distribuídos e computação em nuvem, incluindo conteinerização, comunicação entre serviços, mensageria, segurança, resiliência e observabilidade.

---

## 2. Objetivos do projeto

- Implementar uma arquitetura baseada em microsserviços.
- Centralizar o acesso à aplicação por meio de um API Gateway.
- Implementar autenticação utilizando JWT.
- Realizar processamento assíncrono com Redis e Worker.
- Utilizar Qdrant para armazenamento e recuperação vetorial.
- Implementar mecanismos de resiliência.
- Monitorar a comunicação entre serviços utilizando OpenTelemetry e Jaeger.
- Conteinerizar os componentes utilizando Docker.
- Disponibilizar um serviço publicamente por meio de uma plataforma de nuvem.

---

## 3. Arquitetura da solução

A aplicação é composta pelos seguintes componentes:

| Componente | Responsabilidade |
|---|---|
| API Gateway | Receber requisições, autenticar usuários e encaminhar solicitações |
| Inferência | Coordenar o processamento das solicitações e a integração com os demais serviços |
| Worker | Consumir tarefas da fila e executar o processamento assíncrono |
| Redis | Gerenciar a fila de tarefas e a comunicação assíncrona |
| Qdrant | Armazenar e recuperar representações vetoriais |
| Jaeger | Visualizar os rastreamentos distribuídos |

### Fluxo de funcionamento

1. O cliente envia uma requisição ao API Gateway.
2. O Gateway valida a autenticação e verifica as regras de acesso.
3. A solicitação é encaminhada ao serviço de Inferência.
4. A Inferência registra uma tarefa na fila Redis.
5. O Worker consome a tarefa e executa o processamento.
6. O resultado é disponibilizado para a Inferência e retornado ao Gateway.
7. O Qdrant permite armazenar e consultar representações vetoriais.
8. O OpenTelemetry coleta informações de rastreamento, que podem ser visualizadas no Jaeger.

### Diagrama lógico

```text
                    +-------------+
                    |   CLIENTE   |
                    +------+------+
                           |
                           v
                    +-------------+
                    | API GATEWAY |
                    | JWT / REST  |
                    +------+------+
                           |
                           v
                    +-------------+
                    | INFERÊNCIA  |
                    +------+------+
                           |
             +-------------+-------------+
             |                           |
             v                           v
      +-------------+             +-------------+
      |    REDIS    |             |   QDRANT    |
      +------+------+             +-------------+
             |
             v
      +-------------+
      |   WORKER    |
      +-------------+

  =====================================================
  OpenTelemetry / Jaeger  ──►  Rastreamento distribuído
  =====================================================

```

O diagrama representa a arquitetura lógica da solução. Os componentes são executados em containers e se comunicam pela rede interna do Docker Compose.

---

## 4. Tecnologias utilizadas

| Tecnologia | Aplicação |
| --- | --- |
| Python 3.12 | Desenvolvimento dos serviços |
| FastAPI | Construção das APIs |
| Docker | Conteinerização |
| Docker Compose | Orquestração local |
| Redis | Mensageria e fila de tarefas |
| Qdrant | Banco de dados vetorial |
| OpenTelemetry | Instrumentação e rastreamento |
| Jaeger | Visualização de traces |
| JWT | Autenticação |
| Render | Publicação do Gateway |

---

## 5. Estrutura do repositório

```text
sd-2026-2-kit-c3a2/
│
├── gateway/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── inferencia/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── worker/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── deploy/
│   └── INSTRUCOES.md
│
├── docker-compose.yml
├── render.yaml
├── .env.example
├── .gitignore
└── README.md

```

---

## 6. Requisitos para execução

Para executar o projeto localmente, são necessários:

* Windows, Linux ou macOS.
* Docker instalado.
* Docker Compose.
* Git.
* Conexão com a internet para baixar as imagens e dependências na primeira execução.

O Docker Desktop é recomendado para usuários Windows.

---

## 7. Instalação e execução

### 7.1. Clonar o repositório

```bash
git clone [https://github.com/muriloss08/sd-2026-2-kit-c3a2.git](https://github.com/muriloss08/sd-2026-2-kit-c3a2.git)
cd sd-2026-2-kit-c3a2

```

### 7.2. Configurar as variáveis de ambiente

No Windows PowerShell:

```powershell
Copy-Item .env.example .env

```

No Linux ou macOS:

```bash
cp .env.example .env

```

Edite o arquivo `.env` e configure valores próprios para:

```env
JWT_SEGREDO=SUBSTITUA_POR_UMA_CHAVE_FORTE
LOGIN_USUARIO=admin
LOGIN_SENHA=DEFINA_UMA_SENHA_FORTE

```

As demais variáveis de ambiente necessárias estão documentadas no arquivo `.env.example`.

> [!IMPORTANT]
> nunca envie o arquivo `.env` ao GitHub. O repositório utiliza `.gitignore` para impedir o versionamento das credenciais locais.

### 7.3. Iniciar todos os serviços

Na pasta principal do projeto, execute:

```bash
docker compose up --build -d

```

Esse comando constrói as imagens e inicia os containers da aplicação.

### 7.4. Verificar os containers

```bash
docker compose ps

```

Para acompanhar os registros:

```bash
docker compose logs -f

```

Para acompanhar um serviço específico:

```bash
docker compose logs -f gateway

```

### 7.5. Encerrar a aplicação

```bash
docker compose down

```

Para remover também os volumes persistentes:

```bash
docker compose down -v

```

A segunda opção remove os dados persistidos pelo volume do Qdrant. Utilize-a somente quando desejar reiniciar o armazenamento.

---

## 8. Endpoints e interfaces

### Gateway

Endereço local:

```text
http://localhost:8000

```

Documentação Swagger:

```text
http://localhost:8000/docs

```

Verificação de saúde:

```text
http://localhost:8000/saude

```

### Jaeger

Interface de rastreamento:

```text
http://localhost:16686

```

### Qdrant

Interface HTTP:

```text
http://localhost:6333

```

### Redis

Endereço interno do ambiente Docker:

```text
redis://redis:6379/0

```

A Inferência e o Worker são acessados pela rede interna do Docker Compose, não sendo necessário expor suas portas diretamente ao cliente.

---

## 9. API e autenticação

O API Gateway disponibiliza os seguintes endpoints:

| Método | Endpoint | Finalidade |
| --- | --- | --- |
| GET | `/saude` | Verificação de saúde do Gateway |
| GET | `/resiliencia` | Consulta do estado do Circuit Breaker |
| POST | `/login` | Autenticação e geração de JWT |
| POST | `/predict` | Solicitação de processamento |
| POST | `/buscar` | Busca de informações vetoriais |

A documentação interativa dos endpoints pode ser acessada pelo Swagger em `/docs`.

### Autenticação JWT

A aplicação utiliza JSON Web Token (JWT) para controlar o acesso às rotas protegidas.

O fluxo de autenticação funciona da seguinte maneira:

1. O usuário envia suas credenciais para o endpoint `/login`.
2. O Gateway valida o usuário e a senha.
3. Após a validação, um token JWT é emitido.
4. O cliente utiliza o token nas próximas requisições protegidas.
5. O Gateway valida o token antes de permitir o acesso.

O token deve ser enviado no cabeçalho:

```text
Authorization: Bearer SEU_TOKEN

```

O projeto utiliza um tempo de validade configurado para o token. A configuração atual utiliza 60 minutos.

### Rate Limit

O Gateway possui limitação de requisições por endereço IP, reduzindo o risco de excesso de chamadas em um curto intervalo.

---

## 10. Mensageria e processamento assíncrono

O Redis é utilizado como mecanismo de fila para desacoplar a recepção das solicitações da execução do processamento.

A Inferência registra as tarefas, enquanto o Worker consome os itens da fila e executa o processamento.

Essa separação permite distribuir responsabilidades entre serviços independentes e facilita a evolução da arquitetura.

---

## 11. Armazenamento vetorial

O Qdrant é utilizado para armazenar e recuperar representações vetoriais.

A aplicação gera representações vetoriais a partir dos textos e permite realizar consultas de similaridade.

O armazenamento é persistido por meio de um volume Docker:

```yaml
volumes:
  qdrant_storage:

```

Essa configuração permite manter os dados mesmo após a interrupção dos containers, desde que o volume não seja removido.

As representações utilizadas no projeto têm finalidade demonstrativa e não representam necessariamente embeddings produzidos por um modelo de linguagem avançado.

---

## 12. Resiliência e tolerância a falhas

Foram implementados mecanismos para melhorar a tolerância a falhas na comunicação entre os serviços.

### Timeout

Define um limite de tempo para aguardar respostas de serviços externos.

### Retry

Executa novas tentativas quando ocorrem falhas temporárias de comunicação, utilizando espera progressiva entre as tentativas.

### Circuit Breaker

Interrompe temporariamente chamadas a um serviço quando uma quantidade configurada de falhas consecutivas é atingida.

Após o período de espera, o mecanismo permite novas tentativas para verificar se o serviço se recuperou.

Esses recursos ajudam a evitar chamadas repetidas a serviços indisponíveis e melhoram o comportamento da aplicação diante de falhas.

---

## 13. Observabilidade e rastreamento distribuído

O projeto utiliza OpenTelemetry para instrumentar os serviços e Jaeger para visualizar os rastreamentos distribuídos.

A instrumentação permite acompanhar a comunicação entre:

* Gateway.
* Inferência.
* Worker.

O contexto de rastreamento é propagado durante o processamento das tarefas, permitindo relacionar operações executadas em diferentes serviços.

A interface do Jaeger pode ser acessada localmente:

```text
http://localhost:16686

```

Na interface, é possível selecionar os serviços disponíveis e visualizar os traces gerados pelas requisições.

---

## 14. Segurança

Os principais recursos de segurança implementados são:

* Autenticação por JWT.
* Proteção das rotas que exigem autenticação.
* Armazenamento de credenciais em variáveis de ambiente.
* Rate Limit no Gateway.
* Comunicação HTTPS no Gateway publicado no Render.

As credenciais reais não devem ser armazenadas no código-fonte nem compartilhadas publicamente.

---

## 15. Publicação em nuvem

O API Gateway foi publicado utilizando o plano gratuito do Render.

* **URL pública:** `https://sd-2026-2-gateway.onrender.com`
* **Documentação Swagger:** `https://sd-2026-2-gateway.onrender.com/docs`
* **Verificação de saúde:** `https://sd-2026-2-gateway.onrender.com/saude`

A plataforma Render disponibiliza HTTPS para o serviço publicado.

### Limitações da implantação atual

Nesta etapa do projeto, somente o Gateway está publicado no Render.

Os serviços Redis, Qdrant, Inferência, Worker e Jaeger são executados localmente por meio do Docker Compose.

Por isso, as funcionalidades que dependem da comunicação entre o Gateway publicado e os demais serviços não estão disponíveis na implantação pública atual. O fluxo completo deve ser demonstrado no ambiente local.

O plano gratuito do Render também pode suspender o serviço após um período de inatividade, causando demora na primeira requisição posterior.

---

## 16. LGPD e tratamento de dados

A aplicação pode processar textos enviados pelos usuários, além de informações técnicas necessárias à autenticação e ao funcionamento dos serviços.

### Dados tratados

* Textos enviados para processamento.
* Representações vetoriais geradas a partir dos textos.
* Identificadores de tarefas.
* Informações técnicas de rastreamento e execução.
* Informações utilizadas na autenticação.

### Finalidade

Os dados são utilizados exclusivamente para:

* Processar solicitações de inferência.
* Armazenar e recuperar representações vetoriais.
* Executar tarefas assíncronas.
* Controlar o acesso à API.
* Monitorar o funcionamento da aplicação.

### Retenção

* Os dados vetoriais permanecem no volume persistente do Qdrant até sua remoção.
* Não foi configurada uma política automática de expiração dos dados vetoriais.
* Os dados armazenados no Redis dependem do ciclo de vida e das configurações do serviço.
* Os registros de rastreamento dependem da configuração de armazenamento do Jaeger.

> [!NOTE]
> Recomenda-se utilizar somente dados fictícios ou de teste durante as demonstrações, evitando o envio de dados pessoais reais.

---

## 17. Relatório de trade-offs

### 17.1. CAP

O teorema CAP descreve o compromisso entre consistência, disponibilidade e tolerância a partições de rede em sistemas distribuídos.

Na implementação atual, os serviços são executados em um ambiente Docker Compose local, sem cluster ou replicação distribuída configurados.

Dessa forma, a aplicação não oferece alta disponibilidade diante da falha de um componente único.

A separação em microsserviços facilita a evolução independente dos componentes, mas introduz dependências de comunicação entre eles.

Em uma implantação distribuída, seria necessário definir políticas específicas de consistência e disponibilidade para Redis, Qdrant e os demais serviços.

### 17.2. Custo

A execução local utiliza Docker e Docker Compose, evitando a contratação de infraestrutura adicional para demonstrar a arquitetura completa.

O Gateway foi publicado no plano gratuito do Render.

Essa escolha reduz o custo financeiro, mas possui limitações de processamento, memória e disponibilidade, incluindo suspensão por inatividade.

A arquitetura completa não está hospedada na nuvem nesta versão.

### 17.3. Latência

A comunicação entre os containers ocorre pela rede interna do Docker Compose, reduzindo a necessidade de comunicação externa entre os serviços locais.

O uso de processamento assíncrono permite separar a recepção das tarefas de sua execução pelo Worker.

Por outro lado, a passagem por múltiplos serviços pode aumentar o tempo total de resposta.

Os mecanismos de timeout e retry ajudam a controlar falhas, mas novas tentativas podem aumentar a latência em situações de indisponibilidade.

Na implantação pública, o tempo de resposta também pode ser afetado pela suspensão do serviço gratuito do Render.

---

## 18. Equipe e divisão de responsabilidades

O desenvolvimento e a organização do projeto são divididos entre três integrantes.

| Integrante | Frente de trabalho |
| --- | --- |
| Murilo da Silva Soares | Gateway, autenticação, segurança, integração e publicação |
| Rogelio Soares Reis Filho | Revisão e colaboração no serviço de Inferência, integração com Qdrant e testes |
| Mariana Lopes | Revisão e colaboração no Worker, Redis, mensageria e observabilidade |

A divisão representa as frentes de colaboração planejadas para a equipe. As contribuições individuais devem ser registradas no histórico do GitHub conforme forem realizadas.

---

## 19. Repositório

GitHub:

`https://github.com/muriloss08/sd-2026-2-kit-c3a2`

---

## 20. Considerações finais

O projeto demonstra a aplicação prática de conceitos de sistemas distribuídos e computação em nuvem por meio de uma arquitetura de microsserviços.

A solução reúne autenticação, comunicação assíncrona, armazenamento vetorial, mecanismos de resiliência, observabilidade e conteinerização.

O Docker Compose permite executar os componentes da arquitetura localmente por meio de um único comando, enquanto a publicação do Gateway demonstra a disponibilização de uma API pública utilizando HTTPS.

O desenvolvimento prioriza a separação de responsabilidades, a comunicação entre serviços e a execução reproduzível da aplicação.
