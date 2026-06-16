"""A real-model adapter for OpenAI-compatible Chat Completions APIs.

This speaks the widely implemented /v1/chat/completions shape used by OpenAI
and many local or hosted runtimes. Everything provider-specific stays here:
the agent loop still only sees our normalized Message and ToolCall types.
"""

import json
import urllib.error
import urllib.request

from model_types import Message, Role, ToolCall
from provider import ModelProvider


class ChatCompletionsProvider(ModelProvider):
    def __init__(self, model, base_url="https://api.openai.com/v1", api_key=None,
                 timeout=60):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages, tools, system=""):
        payload = {
            "model": self.model,
            "messages": self._to_provider_messages(messages, system),
        }
        if tools:
            payload["tools"] = [
                {"type": "function", "function": tool}
                for tool in tools
            ]
            payload["tool_choice"] = "auto"

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Chat Completions request failed: {e.code} {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Chat Completions request failed: {e.reason}") from e

        return self._from_provider_message(json.loads(raw))

    def _to_provider_messages(self, messages, system):
        provider_messages = []
        if system:
            provider_messages.append({"role": "system", "content": system})

        for message in messages:
            if message.role == Role.TOOL:
                provider_messages.append({
                    "role": "tool",
                    "tool_call_id": message.tool_result.call_id,
                    "content": message.tool_result.content,
                })
                continue

            provider_message = {
                "role": message.role.value,
                "content": message.content or "",
            }
            if message.tool_calls:
                provider_message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call in message.tool_calls
                ]
            provider_messages.append(provider_message)

        return provider_messages

    def _from_provider_message(self, response):
        try:
            provider_message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected Chat Completions response: {response}") from e

        tool_calls = []
        for raw_call in provider_message.get("tool_calls") or []:
            function = raw_call.get("function", {})
            raw_arguments = function.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Model returned invalid JSON tool arguments: {raw_arguments}"
                ) from e
            if not isinstance(arguments, dict):
                raise RuntimeError(
                    f"Model returned non-object tool arguments: {raw_arguments}"
                )
            tool_calls.append(ToolCall(
                id=raw_call.get("id", ""),
                name=function.get("name", ""),
                arguments=arguments,
            ))

        return Message(
            role=Role.ASSISTANT,
            content=provider_message.get("content") or "",
            tool_calls=tool_calls,
        )
