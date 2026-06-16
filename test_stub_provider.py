import unittest

from model_types import Message, Role, ToolResult
from stub_provider import StubProvider


class StubProviderTest(unittest.TestCase):
    def test_first_call_requests_first_tool(self):
        provider = StubProvider()
        message = provider.complete(
            messages=[Message(role=Role.USER, content="hello")],
            tools=[{"name": "echo"}],
        )

        self.assertEqual(Role.ASSISTANT, message.role)
        self.assertEqual("I'll use a tool to answer that.", message.content)
        self.assertEqual(1, len(message.tool_calls))
        self.assertEqual("call_1", message.tool_calls[0].id)
        self.assertEqual("echo", message.tool_calls[0].name)
        self.assertEqual({"query": "hello"}, message.tool_calls[0].arguments)

    def test_second_call_uses_tool_result_for_final_answer(self):
        provider = StubProvider()
        message = provider.complete(
            messages=[
                Message(role=Role.USER, content="hello"),
                Message(
                    role=Role.TOOL,
                    tool_result=ToolResult(call_id="call_1", content="tool says hi"),
                ),
            ],
            tools=[{"name": "echo"}],
        )

        self.assertEqual(Role.ASSISTANT, message.role)
        self.assertEqual(
            "Based on the tool output, the answer is: tool says hi",
            message.content,
        )
        self.assertEqual([], message.tool_calls)


if __name__ == "__main__":
    unittest.main()
