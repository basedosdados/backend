# -*- coding: utf-8 -*-
from typing import Any, Literal, Optional

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel


class ToolCall(BaseModel):
    id: str
    name: str
    args: dict[str, Any]


class ToolOutput(BaseModel):
    status: Literal["error", "success"]
    tool_call_id: str
    tool_name: str
    output: str


EventType = Literal[
    "tool_call",
    "tool_result",
    "final_answer",
    "error",
]


class EventData(BaseModel):
    message: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_outputs: Optional[list[ToolOutput]] = None
    error_details: Optional[dict[str, Any]] = None


class StreamEvent(BaseModel):
    type: EventType
    data: EventData

    def to_sse(self) -> str:
        return self.model_dump_json() + "\n\n"


def process_chunk(chunk: dict[str, Any]) -> StreamEvent:
    """Process a streaming chunk from an agent workflow into a standardized StreamEvent.

    Converts LangChain agent and tool execution chunks into structured events for
    consistent handling in streaming applications.

    Args:
        chunk (dict[str, Any]): Raw chunk dictionary containing either:
            - "agent" key with AIMessage for tool calls or final answers
            - "tools" key with ToolMessage list for tool execution results

    Returns:
        StreamEvent with appropriate type:
            - "tool_call" for agent messages with tool invocations
            - "final_answer" for agent messages without tool calls
            - "tool_result" for tool execution outputs
    """
    if "agent" in chunk:
        message: AIMessage = chunk["agent"]["messages"][0]

        if message.tool_calls:
            tool_calls = [
                ToolCall(id=tool_call["id"], name=tool_call["name"], args=tool_call["args"])
                for tool_call in message.tool_calls
            ]
            event_type = "tool_call"
            event_data = EventData(message=message.content, tool_calls=tool_calls)
        else:
            event_type = "final_answer"
            event_data = EventData(message=message.content)

        return StreamEvent(type=event_type, data=event_data)
    elif "tools" in chunk:
        messages: list[ToolMessage] = chunk["tools"]["messages"]

        tool_outputs = [
            ToolOutput(
                status=message.status,
                tool_call_id=message.tool_call_id,
                tool_name=message.name,
                output=message.content,
            )
            for message in messages
        ]

        return StreamEvent(type="tool_result", data=EventData(tool_outputs=tool_outputs))
