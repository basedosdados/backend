# -*- coding: utf-8 -*-
import json
from typing import Any, Literal, Optional

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import UUID4, BaseModel

# 100KB limit for tool outputs
MAX_BYTES = 100 * 1024


class ToolCall(BaseModel):
    id: str
    name: str
    args: dict[str, Any]


class ToolOutput(BaseModel):
    status: Literal["error", "success"]
    tool_call_id: str
    tool_name: str
    output: str
    metadata: dict[str, Any] | None = None


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


def _truncate_content(json_string: str, max_bytes: int) -> tuple[str, bool]:
    """Truncate a JSON string to fit within the byte limit while preserving structure.

    Args:
        json_string (str): JSON string to truncate.
        max_bytes (int): Maximum allowed size in bytes.

    Returns:
        tuple[str, bool]: Processed JSON string and a flag indicating if it was truncated.
    """
    if len(json_string.encode("utf-8")) <= max_bytes:
        return json_string, False

    data = json.loads(json_string)

    results = data["results"]

    if isinstance(results, dict):
        results = _truncate_dict(results, max_bytes)
    else:
        results = _truncate_list(results, max_bytes)

    data["results"] = results

    return json.dumps(data, ensure_ascii=False, indent=2), True


def _truncate_dict(data: dict, max_bytes: int) -> dict:
    """Reduce dictionary size by removing key-value pairs until it fits the byte limit.

    Args:
        data (dict): Dictionary to truncate.
        max_bytes (int): Maximum allowed size in bytes when serialized to JSON.

    Returns:
        dict: Truncated dictionary that fits within the byte limit.
    """
    items = data.items()

    left, right = 0, len(items)
    best_size = 0

    while left <= right:
        mid = (left + right) // 2
        test_dict = dict(items[:mid])
        size = len(json.dumps(test_dict, ensure_ascii=False, indent=2).encode("utf-8"))

        if size <= max_bytes:
            best_size = mid
            left = mid + 1
        else:
            right = mid - 1

    return dict(items[:best_size])


def _truncate_list(data: list, max_bytes: int) -> list:
    """Reduce list size by removing elements until it fits the byte limit.

    Args:
        data (list): List to truncate.
        max_bytes (int): Maximum allowed size in bytes when serialized to JSON.

    Returns:
        list: Truncated list that fits within the byte limit.
    """
    left, right = 0, len(data)
    best_size = 0

    while left <= right:
        mid = (left + right) // 2
        test_list = data[:mid]
        size = len(json.dumps(test_list, ensure_ascii=False, indent=2).encode("utf-8"))

        if size <= max_bytes:
            best_size = mid
            left = mid + 1
        else:
            right = mid - 1

    return data[:best_size]


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

        tool_outputs = []

        for msg in messages:
            content, truncated = _truncate_content(msg.content, MAX_BYTES)

            if truncated:
                metadata = {"truncated": True}
            else:
                metadata = None

            tool_outputs.append(
                ToolOutput(
                    status=msg.status,
                    tool_call_id=msg.tool_call_id,
                    tool_name=msg.name,
                    output=content,
                    metadata=metadata,
                )
            )

        return StreamEvent(type="tool_output", data=EventData(tool_outputs=tool_outputs))
    return None
