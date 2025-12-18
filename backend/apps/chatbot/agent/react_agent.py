# -*- coding: utf-8 -*-
from collections.abc import Callable
from typing import Annotated, AsyncIterator, Generic, Iterator, Literal, Sequence, Type, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool, BaseToolkit
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.managed import IsLastStep, RemainingSteps
from langgraph.prebuilt import ToolNode
from loguru import logger

from .types import StateT


class ReActState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    """Message list"""

    is_last_step: IsLastStep
    """Flag indicating if the last step has been reached"""

    remaining_steps: RemainingSteps
    """Number of remaining steps before reaching the steps limit"""


class ReActAgent(Generic[StateT]):
    """A LangGraph ReAct Agent."""

    agent_node = "agent"
    tools_node = "tools"
    start_hook_node = "start_hook"

    def __init__(
        self,
        model: BaseChatModel,
        tools: Sequence[BaseTool] | BaseToolkit,
        state_schema: Type[StateT] = ReActState,
        start_hook: Callable[[StateT], dict] | None = None,
        prompt: SystemMessage | str | None = None,
        checkpointer: PostgresSaver | AsyncPostgresSaver | bool | None = None,
    ):
        if isinstance(tools, BaseToolkit):
            self.tools = tools.get_tools()
        else:
            self.tools = tools

        if isinstance(prompt, str):
            self.system_message = SystemMessage(prompt)
        else:
            self.system_message = prompt

        self.model = model.bind_tools(self.tools)

        if self.system_message:
            self.model_runnable = (lambda messages: [self.system_message] + messages) | self.model
        else:
            self.model_runnable = self.model

        self.checkpointer = checkpointer

        self.graph = self._compile(state_schema, start_hook)

    def _call_model(self, state: StateT, config: RunnableConfig) -> dict[str, list[BaseMessage]]:
        """Calls the LLM on a message list.

        Args:
            state (StateT): The graph state.
            config (RunnableConfig): A config to use when calling the LLM.

        Returns:
            dict[str, list[BaseMessage]]: The updated message list.
        """
        messages = state["messages"]
        is_last_step = state["is_last_step"]
        remaining_steps = state["remaining_steps"]

        response: AIMessage = self.model_runnable.invoke(messages, config)

        if not response.content and not response.tool_calls:
            logger.warning("[CHATBOT] Empty model response, skipping message list update")
            return {"messages": []}

        if is_last_step and response.tool_calls or remaining_steps < 2 and response.tool_calls:
            return {
                "messages": [
                    AIMessage(
                        id=response.id,
                        content=(
                            "Desculpe, não consegui encontrar uma resposta para a sua pergunta. "
                            "Por favor, tente reformulá-la ou pergunte algo diferente."
                        ),
                    )
                ]
            }

        return {"messages": [response]}

    async def _acall_model(
        self, state: StateT, config: RunnableConfig
    ) -> dict[str, list[BaseMessage]]:
        """Asynchronously calls the LLM on a message list.

        Args:
            state (StateT): The graph state.
            config (RunnableConfig): A config to use when calling the LLM.

        Returns:
            dict[str, list[BaseMessage]]: The updated message list.
        """
        messages = state["messages"]
        is_last_step = state["is_last_step"]
        remaining_steps = state["remaining_steps"]

        response: AIMessage = await self.model_runnable.ainvoke(messages, config)

        if not response.content and not response.tool_calls:
            logger.warning("[CHATBOT] Empty model response, skipping message list update")
            return {"messages": []}

        if is_last_step and response.tool_calls or remaining_steps < 2 and response.tool_calls:
            return {
                "messages": [
                    AIMessage(
                        id=response.id,
                        content=(
                            "Desculpe, não consegui encontrar uma resposta para a sua pergunta. "
                            "Por favor, tente reformulá-la ou pergunte algo diferente."
                        ),
                    )
                ]
            }

        return {"messages": [response]}

    def _compile(
        self, state_schema: Type[StateT], start_hook: Callable[[StateT], dict] | None
    ) -> CompiledStateGraph:
        """Compiles the state graph into a LangChain Runnable.

        Args:
            state_schema (Type[StateT]): The state graph schema.
            start_hook (Callable[[StateT], dict] | None): An optional node to add before the agent node.
            Useful for managing long message histories (e.g., message trimming, summarization, etc.).
            Must be a callable or a runnable that takes in current graph state and returns a state update.

        Returns:
            CompiledStateGraph: The compiled state graph.
        """  # noqa: E501
        graph = StateGraph(state_schema)

        graph.add_node(self.agent_node, RunnableLambda(self._call_model, self._acall_model))
        graph.add_node(self.tools_node, ToolNode(self.tools))

        if start_hook is not None:
            graph.add_node("start_hook", start_hook)
            graph.add_edge("start_hook", self.agent_node)
            entrypoint = "start_hook"
        else:
            entrypoint = self.agent_node

        graph.set_entry_point(entrypoint)
        graph.add_edge(self.tools_node, self.agent_node)
        graph.add_conditional_edges(self.agent_node, _should_continue)

        # The checkpointer is ignored by default when the graph is used as a subgraph
        # For more information, visit https://langchain-ai.github.io/langgraph/how-tos/subgraph-persistence
        # If you want to persist the subgraph state between runs, you must use checkpointer=True
        # For more information, visit https://github.com/langchain-ai/langgraph/issues/3020
        return graph.compile(self.checkpointer)

    def invoke(self, message: str, config: RunnableConfig | None = None) -> StateT:
        """Runs the compiled graph.

        Args:
            message (str): The input message.
            config (RunnableConfig | None, optional): The configuration. Defaults to `None`.

        Returns:
            StateT: The last output of the graph run.
        """
        message = HumanMessage(content=message.strip())

        response = self.graph.invoke(
            input={"messages": [message]},
            config=config,
        )

        return response

    async def ainvoke(self, message: str, config: RunnableConfig | None = None) -> StateT:
        """Asynchronously runs the compiled graph.

        Args:
            message (str): The input message.
            config (RunnableConfig | None, optional): The configuration. Defaults to `None`.

        Returns:
            StateT: The last output of the graph run.
        """
        message = HumanMessage(content=message.strip())

        response = await self.graph.ainvoke(
            input={"messages": [message]},
            config=config,
        )

        return response

    def stream(
        self,
        message: str,
        config: RunnableConfig | None = None,
        stream_mode: list[str] | None = None,
    ) -> Iterator[dict | tuple]:
        """Stream graph steps.

        Args:
            message (str): The input message.
            config (RunnableConfig | None, optional): Optional configuration for the agent execution. Defaults to `None`.
            stream_mode (list[str] | None, optional): The mode to stream output. See the LangGraph streaming guide in
                https://langchain-ai.github.io/langgraph/how-tos/streaming for more details. Defaults to `None`.

        Yields:
            dict|tuple: The output for each step in the graph. Its type, shape and content depends on the `stream_mode` arg.
        """  # noqa: E501
        message = message.strip()

        message = HumanMessage(content=message)

        for chunk in self.graph.stream(
            input={"messages": [message]},
            config=config,
            stream_mode=stream_mode,
        ):
            yield chunk

    async def astream(
        self,
        message: str,
        config: RunnableConfig | None = None,
        stream_mode: list[str] | None = None,
    ) -> AsyncIterator[dict | tuple]:
        """Asynchronously stream graph steps.

        Args:
            message (str): The input message.
            config (RunnableConfig | None, optional): Optional configuration for the agent execution. Defaults to `None`.
            stream_mode (list[str] | None, optional): The mode to stream output. See the LangGraph streaming guide in
                https://langchain-ai.github.io/langgraph/how-tos/streaming for more details. Defaults to `None`.

        Yields:
            dict|tuple: The output for each step in the graph. Its type, shape and content depends on the `stream_mode` arg.
        """  # noqa: E501
        message = message.strip()

        message = HumanMessage(content=message)

        async for chunk in self.graph.astream(
            input={"messages": [message]},
            config=config,
            stream_mode=stream_mode,
        ):
            yield chunk

    # Unfortunately, there is no clean way to delete an agent's memory
    # except by deleting its checkpoints, as noted in this github discussion:
    # https://github.com/langchain-ai/langgraph/discussions/912
    def clear_thread(self, thread_id: str):
        """Deletes all checkpoints for a given thread.

        Args:
            thread_id (str): The thread unique identifier.
        """
        if self.checkpointer is not None:
            self.checkpointer.delete_thread(thread_id)

    async def aclear_thread(self, thread_id: str):
        """Asynchronously deletes all checkpoints for a given thread.

        Args:
            thread_id (str): The thread unique identifier.
        """
        if self.checkpointer is not None:
            await self.checkpointer.adelete_thread(thread_id)


def _should_continue(state: StateT) -> Literal["tools", "__end__"]:
    """Routes to the tools node if the last message has any tool calls.
    Otherwise, routes to the message pruning node.

    Args:
        state (StateT): The graph state.

    Returns:
        str: The next node to route to.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tools"
    return "__end__"
