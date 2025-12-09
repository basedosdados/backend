<div align="center">
    <a href="https://basedosdados.org">
        <img src="https://storage.googleapis.com/basedosdados-website/logos/bd_minilogo.png" width="240" alt="Base dos Dados">
    </a>
</div>

# Base dos Dados

Backend da [Base dos Dados](https://basedosdados.org), a maior plataforma pública de dados do Brasil.

## Tecnologias Utilizadas

#### Core
- [Django](https://www.djangoproject.com/) como framework web
- [PostgreSQL](https://www.postgresql.org/) como banco de dados relacional
- [huey](https://huey.readthedocs.io/en/latest/) + [Redis](https://redis.io/) para agendamento de tarefas
- [Elasticsearch](https://www.elastic.co/) como motor de busca

#### API de Dados
- [GraphQL](https://graphql.org/) (via [Graphene-Django](https://docs.graphene-python.org/projects/django/en/latest/)) para a API de dados
- [Google Cloud Storage](https://cloud.google.com/storage) para armazenamento de mídia e acesso aos dados brutos
- [Google BigQuery](https://cloud.google.com/bigquery) para acesso aos dados tratados

#### Chatbot
- [Django REST Framework](https://www.django-rest-framework.org/) para a API do chatbot
- [LangChain](https://docs.langchain.com/oss/python/langchain/overview) / [LangGraph](https://langchain-ai.github.io/langgraph/) para desenvolvimento de agentes de IA
- [Google BigQuery](https://cloud.google.com/bigquery) para acesso aos dados tratados
- [Vertex AI](https://cloud.google.com/vertex-ai) para acesso a LLMs

#### Pagamentos
- [Stripe](https://stripe.com/) / [dj-stripe](https://dj-stripe.dev/) para o processamento de pagamentos

#### Ferramentas de Desenvolvimento
- [Poetry](https://python-poetry.org/) para gerenciamento de dependências
- [Docker](https://www.docker.com/) para conteinerização
- [Pre-commit](https://pre-commit.com/) para gerenciamento de hooks de pre-commit
- [Ruff](https://docs.astral.sh/ruff/) para formatação

## Configuração do Ambiente de Desenvolvimento
Para começar a desenvolver, configure o ambiente de desenvolvimento seguindo as instruções abaixo:

1\. Clone o repositório e abra-o no seu editor de texto
```bash
git clone https://github.com/basedosdados/backend.git
```

2\. Crie um ambiente virtual de desenvolvimento com o [Poetry](https://python-poetry.org/docs).
```bash
poetry install
```

3\. Instale os hooks de pre-commit
```
pre-commit install
```

4\. Copie o arquivo `.env.example` e ajuste as variáveis conforme necessário
```bash
cp .env.example .env
```
> [!NOTE]
> As variáveis de ambiente no arquivo `.env.example` já estão configuradas para execução com o Docker.
> 
> Caso vá utilizar a funcionalidade do chatbot, a conta de serviço deve ser armazenada localmente em `~/.basedosdados/credentials`.

## Execução do Backend
Utilize o [Docker](https://docs.docker.com/engine/install/) para executar o backend localmente:

```bash
docker compose up
```

> [!TIP]
> Você também pode utilizar a flag `-d --detach` e acompanhar os logs utilizando o comando `docker logs` com a flag `-f --follow`
> ```bash
> docker compose up -d
> docker compose logs api -f
> ```
> Para parar o serviço:
> ```
> docker compose down
> ```
