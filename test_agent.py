import unittest

from agent import dispatch, run
from stub_provider import StubProvider


class AgentTest(unittest.TestCase):
    def test_run_with_stub_provider_reaches_final_answer(self):
        answer = run(
            provider=StubProvider(),
            user_input="What is the meaning of life?",
            system="You are a helpful assistant.",
        )

        self.assertEqual(
            "Based on the tool output, the answer is: You said "
            "'What is the meaning of life?', and it is 42 characters of wisdom.",
            answer,
        )

    def test_dispatch_runs_known_tool(self):
        result = dispatch("echo", {"query": "hello"})

        self.assertFalse(result.is_error)
        self.assertEqual(
            "You said 'hello', and it is 42 characters of wisdom.",
            result.content,
        )

    def test_dispatch_reports_unknown_tool_as_error(self):
        result = dispatch("missing", {})

        self.assertTrue(result.is_error)
        self.assertEqual("Unknown tool: missing", result.content)


if __name__ == "__main__":
    unittest.main()
