import json
import unittest
from unittest.mock import patch

from chat_completions_provider import ChatCompletionsProvider
from model_types import Message, Role, ToolCall, ToolResult


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


class ChatCompletionsProviderTest(unittest.TestCase):
    def test_sends_normalized_messages_and_tools(self):
        body = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "done",
                }
            }]
        }
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(body)

        provider = ChatCompletionsProvider(
            model="test-model",
            base_url="http://example.test/v1/",
            api_key="secret",
            timeout=7,
        )
        messages = [
            Message(role=Role.USER, content="hi"),
            Message(
                role=Role.ASSISTANT,
                content="using tool",
                tool_calls=[ToolCall(
                    id="call_1",
                    name="echo",
                    arguments={"query": "hi"},
                )],
            ),
            Message(
                role=Role.TOOL,
                tool_result=ToolResult(call_id="call_1", content="hello"),
            ),
        ]
        tools = [{
            "name": "echo",
            "description": "Echoes.",
            "parameters": {"type": "object"},
        }]

        with patch("urllib.request.urlopen", fake_urlopen):
            response = provider.complete(messages, tools, system="Be useful.")

        request = captured["request"]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual("http://example.test/v1/chat/completions", request.full_url)
        self.assertEqual("Bearer secret", request.headers["Authorization"])
        self.assertEqual(7, captured["timeout"])
        self.assertEqual("test-model", payload["model"])
        self.assertEqual({"role": "system", "content": "Be useful."},
                         payload["messages"][0])
        self.assertEqual("tool", payload["messages"][3]["role"])
        self.assertEqual("call_1", payload["messages"][3]["tool_call_id"])
        self.assertEqual("function", payload["tools"][0]["type"])
        self.assertEqual(tools[0], payload["tools"][0]["function"])
        self.assertEqual("done", response.content)
        self.assertEqual([], response.tool_calls)

    def test_parses_tool_calls_to_normalized_messages(self):
        provider = ChatCompletionsProvider(model="test-model")
        response = provider._from_provider_message({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_abc",
                        "type": "function",
                        "function": {
                            "name": "echo",
                            "arguments": "{\"query\": \"hi\"}",
                        },
                    }],
                }
            }]
        })

        self.assertEqual(Role.ASSISTANT, response.role)
        self.assertEqual("", response.content)
        self.assertEqual(1, len(response.tool_calls))
        self.assertEqual("call_abc", response.tool_calls[0].id)
        self.assertEqual("echo", response.tool_calls[0].name)
        self.assertEqual({"query": "hi"}, response.tool_calls[0].arguments)

    def test_rejects_invalid_tool_argument_json(self):
        provider = ChatCompletionsProvider(model="test-model")

        with self.assertRaisesRegex(RuntimeError, "invalid JSON tool arguments"):
            provider._from_provider_message({
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "echo",
                                "arguments": "{not json",
                            },
                        }],
                    }
                }]
            })


if __name__ == "__main__":
    unittest.main()
