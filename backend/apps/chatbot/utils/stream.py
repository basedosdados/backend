# -*- coding: utf-8 -*-
from typing import Any, Literal, Optional

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import UUID4, BaseModel


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
    "tool_output",
    "final_answer",
    "error",
    "complete",
]


class EventData(BaseModel):
    run_id: Optional[UUID4] = None
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_outputs: Optional[list[ToolOutput]] = None
    error_details: Optional[dict[str, Any]] = None


class StreamEvent(BaseModel):
    type: EventType
    data: EventData

    def to_sse(self) -> str:
        return self.model_dump_json() + "\n\n"


def process_chunk(chunk: dict[str, Any]) -> StreamEvent | None:
    """Process a streaming chunk from a react agent workflow into a standardized StreamEvent.

    Args:
        chunk (dict[str, Any]): Raw chunk from agent workflow.
            Only processes "agent" and "tools" nodes.

    Returns:
        StreamEvent | None: Structured event or None if the chunk is ignored:
            - "tool_call" for agent messages with tool calls
            - "tool_output" for tool execution results
            - "final_answer" for agent messages without tool calls
            - None for ignored chunks
    """
    if "agent" in chunk:
        message: AIMessage = chunk["agent"]["messages"][0]

        if message.tool_calls:
            tool_calls = [
                ToolCall(id=tool_call["id"], name=tool_call["name"], args=tool_call["args"])
                for tool_call in message.tool_calls
            ]
            event_type = "tool_call"
            event_data = EventData(content=message.content, tool_calls=tool_calls)
        else:
            event_type = "final_answer"
            event_data = EventData(content=message.content)

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

        return StreamEvent(type="tool_output", data=EventData(tool_outputs=tool_outputs))
    return None
