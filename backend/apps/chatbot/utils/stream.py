# -*- coding: utf-8 -*-
import json
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from loguru import logger
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
    metadata: dict[str, Any] | None = None


EventType = Literal[
    "tool_call",
    "tool_output",
    "final_answer",
    "error",
    "complete",
]


class EventData(BaseModel):
    run_id: UUID4 | None = None
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_outputs: list[ToolOutput] | None = None
    error_details: dict[str, Any] | None = None


class StreamEvent(BaseModel):
    type: EventType
    data: EventData

    def to_sse(self) -> str:
        return self.model_dump_json() + "\n\n"


def _truncate_json(json_string: str, max_list_len: int = 10, max_str_len: int = 300) -> str:
    """Iteratively truncates a serialized JSON object by shortening lists and strings
    and adding human-readable placeholders.

    Note:
        This function only processes JSON objects (dictionaries). If the serialized JSON
        represents any other type, the original JSON string will be returned unchanged.

    Args:
        json_string (str): The serialized JSON to process.
        max_list_len (int, optional): The max number of items to keep in a list. Defaults to 10.
        max_str_len (int, optional): The max length for any single string. Defaults to 300.

    Returns:
        str: The truncated, formatted, and serialized JSON object.
    """
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError:
        return json_string

    if not isinstance(data, dict):
        return json_string

    stack = [data]

    while stack:
        current_node = stack.pop()

        if isinstance(current_node, dict):
            items_to_process = current_node.items()
        else:
            items_to_process = enumerate(current_node)

        for key_or_idx, item in items_to_process:
            if isinstance(item, str):
                if len(item) > max_str_len:
                    truncated_str = (
                        item[:max_str_len] + f"... ({len(item) - max_str_len} more characters)"
                    )
                    current_node[key_or_idx] = truncated_str

            elif isinstance(item, list):
                if len(item) > max_list_len:
                    original_len = len(item)
                    del item[max_list_len:]
                    item.append(f"... ({original_len - max_list_len} more items)")
                stack.append(item)

            elif isinstance(item, dict):
                stack.append(item)

    return json.dumps(data, ensure_ascii=False, indent=2)


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
        ai_messages: list[AIMessage] = chunk["agent"]["messages"]

        # If no messages are returned, the model returned an empty response
        # with no tool calls. This also counts as a final (but empty) answer.
        if not ai_messages:
            return StreamEvent(type="final_answer", data=EventData(content=""))

        message = ai_messages[0]

        if message.tool_calls:
            event_type = "tool_call"
            tool_calls = [
                ToolCall(id=tool_call["id"], name=tool_call["name"], args=tool_call["args"])
                for tool_call in message.tool_calls
            ]
        else:
            event_type = "final_answer"
            tool_calls = None

        # The content of an AIMessage can sometimes be a list, which is not the expected behavior.
        # In that case, we just log a warning and cast it to string to keep processing consistent.
        if isinstance(message.content, list):
            logger.warning("[CHATBOT] Message content is of type 'list', casting to string")
            content = "".join(str(part) for part in message.content)
        else:
            content = message.content

        event_data = EventData(content=content, tool_calls=tool_calls)

        return StreamEvent(type=event_type, data=event_data)
    elif "tools" in chunk:
        tool_messages: list[ToolMessage] = chunk["tools"]["messages"]

        tool_outputs = [
            ToolOutput(
                status=message.status,
                tool_call_id=message.tool_call_id,
                tool_name=message.name,
                output=_truncate_json(message.content),
            )
            for message in tool_messages
        ]

        return StreamEvent(type="tool_output", data=EventData(tool_outputs=tool_outputs))
    return None
