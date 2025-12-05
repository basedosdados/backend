# -*- coding: utf-8 -*-
import json
import os
import time
from functools import wraps
from typing import Any, Iterator

from backend.apps.chatbot.models import MessagePair, Thread
from backend.apps.chatbot.utils.stream import (
    EventData,
    StreamEvent,
    ToolCall,
    ToolOutput,
    _truncate_json,
)

from .mock_data import (
    RAIS_DATASET_DETAILS,
    RAIS_DATASET_SEARCH,
    RAIS_DECODE_SEXO,
    RAIS_DECODE_VINCULO_ATIVO,
    RAIS_FINAL_RESPONSE,
)


def allow_agent_mock(func):
    """Decorator to replace agent execution with mock streaming when MOCK_AGENT=true."""

    @wraps(func)
    def wrapper(message: str, config: dict, thread: Thread) -> Iterator[str]:
        mock = os.getenv("MOCK_AGENT", "false").lower() == "true"

        if mock:
            return _mock_agent(message, config, thread)

        return func(message, config, thread)

    return wrapper


def _mock_agent(message: str, config: dict, thread: Thread) -> Iterator[str]:
    """Generate mock streaming events that simulate real agent behavior.

    Args:
        message (str): User's input message.
        config (ConfigDict): Configuration for agent execution.
        thread (Thread): Conversation thread.

    Yields:
        Iterator[str]: SSE-formatted event.
    """
    events = []

    _mock_thinking(2)

    # ========== STEP 1: Search for datasets ==========
    search_call_event = StreamEvent(
        type="tool_call",
        data=EventData(
            content=(
                "Estou buscando dados sobre a proporção de mulheres no mercado de "
                "trabalho formal. Acredito que o dataset da RAIS (Relação Anual de "
                "Informações Sociais) seja a fonte mais adequada para essa informação, "
                "pois ele contém dados detalhados sobre o emprego formal no Brasil.\n\n"
                'Vou começar pesquisando por "rais" para encontrar os datasets disponíveis.'
            ),
            tool_calls=[
                ToolCall(
                    id="call_search_datasets",
                    name="search_datasets",
                    args={"query": "rais"},
                )
            ],
        ),
    )

    events.append(search_call_event.model_dump())
    yield search_call_event.to_sse()

    # Simulates calling the /search/ endpoint
    _mock_tool_call(1)

    search_output_event = _mock_tool_output_event(
        tool_call_id="call_search_datasets",
        tool_name="search_datasets",
        data=RAIS_DATASET_SEARCH,
    )

    events.append(search_output_event.model_dump())
    yield search_output_event.to_sse()

    _mock_thinking(2)

    # ========== STEP 2: Get dataset details ==========
    dataset_details_call_event = StreamEvent(
        type="tool_call",
        data=EventData(
            content=(
                "Estou buscando dados sobre a proporção de mulheres no mercado de "
                'trabalho formal. A busca por "rais" retornou o dataset "Relação Anual '
                'de Informações Sociais (RAIS)", que é o esperado. Agora, preciso obter '
                "os detalhes desse dataset para entender sua estrutura e quais tabelas "
                "contêm as informações necessárias sobre gênero e mercado de trabalho formal."
            ),
            tool_calls=[
                ToolCall(
                    id="call_get_dataset_details",
                    name="get_dataset_details",
                    args={"dataset_id": "3e7c4d58-96ba-448e-b053-d385a829ef00"},
                )
            ],
        ),
    )

    events.append(dataset_details_call_event.model_dump())
    yield dataset_details_call_event.to_sse()

    # Simulates GraphQL query + usage guide fetching
    _mock_tool_call(2)

    dataset_details_output_event = _mock_tool_output_event(
        tool_call_id="call_get_dataset_details",
        tool_name="get_dataset_details",
        data=RAIS_DATASET_DETAILS,
    )

    events.append(dataset_details_output_event.model_dump())
    yield dataset_details_output_event.to_sse()

    _mock_thinking(2)

    # ========== STEP 3: Decode "sexo" column ==========
    decode_sexo_call_event = StreamEvent(
        type="tool_call",
        data=EventData(
            content=(
                "Estou analisando o dataset da RAIS para determinar a proporção de "
                "mulheres no mercado de trabalho formal. A tabela `microdados_vinculos` "
                "é a mais adequada para esta análise, pois contém a coluna `sexo`.\n\n"
                "Antes de prosseguir com a consulta, vou decodificar os valores da coluna "
                "`sexo` para entender como o gênero é representado nos dados."
            ),
            tool_calls=[
                ToolCall(
                    id="call_decode_table_values_1",
                    name="decode_table_values",
                    args={
                        "table_gcp_id": "basedosdados.br_me_rais.microdados_estabelecimentos",
                        "column_name": "sexo",
                    },
                )
            ],
        ),
    )

    events.append(decode_sexo_call_event.model_dump())
    yield decode_sexo_call_event.to_sse()

    # Simulates querying the dictionary table on BigQuery
    _mock_tool_call(1)

    decoded_sexo_output_event = _mock_tool_output_event(
        tool_call_id="call_decode_table_values_1",
        tool_name="decode_table_values",
        data=RAIS_DECODE_SEXO,
    )

    events.append(decoded_sexo_output_event.model_dump())
    yield decoded_sexo_output_event.to_sse()

    _mock_thinking(2)

    # ========== STEP 4: Decode "vinculo_ativo_3112" column ==========
    decode_vinculo_ativo_call_event = StreamEvent(
        type="tool_call",
        data=EventData(
            content=(
                "Para calcular a proporção de mulheres no mercado de trabalho formal, "
                "utilizarei a tabela `microdados_vinculos` do dataset da RAIS. Esta "
                "tabela contém informações detalhadas sobre os vínculos empregatícios, "
                "incluindo o sexo dos trabalhadores e se o vínculo estava ativo em 31/12.\n\n"
                "Antes de construir a consulta final, vou decodificar os valores da coluna "
                "`vinculo_ativo_3112` para garantir que estou filtrando corretamente os "
                "vínculos ativos."
            ),
            tool_calls=[
                ToolCall(
                    id="call_decode_table_values_2",
                    name="decode_table_values",
                    args={
                        "table_gcp_id": "basedosdados.br_me_rais.microdados_estabelecimentos",
                        "column_name": "vinculo_ativo_3112",
                    },
                )
            ],
        ),
    )

    events.append(decode_vinculo_ativo_call_event.model_dump())
    yield decode_vinculo_ativo_call_event.to_sse()

    # Simulates querying the dictionary table on BigQuery
    _mock_tool_call(1)

    decoded_vinculo_ativo_output_event = _mock_tool_output_event(
        tool_call_id="call_decode_table_values_2",
        tool_name="decode_table_values",
        data=RAIS_DECODE_VINCULO_ATIVO,
    )

    events.append(decoded_vinculo_ativo_output_event.model_dump())
    yield decoded_vinculo_ativo_output_event.to_sse()

    # The agent usually takes longer to generate the final response
    _mock_thinking(5)

    # ========== STEP 5: Send final response ==========
    final_answer_event = StreamEvent(
        type="final_answer", data=EventData(content=RAIS_FINAL_RESPONSE)
    )

    events.append(final_answer_event.model_dump())
    yield final_answer_event.to_sse()

    # ========== STEP 6: Save message and complete ==========
    message_pair = MessagePair.objects.create(
        id=config["run_id"],
        thread=thread,
        model_uri="SIMULATED_MODEL",
        user_message=message,
        assistant_message=RAIS_FINAL_RESPONSE,
        error_message=None,
        events=events,
    )

    complete_event = StreamEvent(type="complete", data=EventData(run_id=message_pair.id))

    yield complete_event.to_sse()


# ===============================
# Helper Methods
# ===============================
def _mock_thinking(t: float):
    time.sleep(t)


def _mock_tool_call(t: float):
    time.sleep(t)


def _mock_tool_output_event(tool_call_id: str, tool_name: str, data: dict[str, Any]) -> StreamEvent:
    """Create a mock tool output event from data.

    Args:
        tool_call_id: Unique identifier for the tool call.
        tool_name: Name of the tool being mocked.
        data: Data dictionary to serialize.

    Returns:
        StreamEvent containing the tool output.
    """
    tool_output = ToolOutput(
        status="success",
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        output=_truncate_json(json.dumps(data, ensure_ascii=False, indent=2)),
    )

    return StreamEvent(type="tool_output", data=EventData(tool_outputs=[tool_output]))
