import unittest
from contextlib import redirect_stderr, redirect_stdout
import io
from unittest.mock import patch

import agent
from model_types import Message, Role


class FakeProvider:
    def complete(self, messages, tools, system=""):
        return Message(role=Role.ASSISTANT, content="fake answer")


class AgentCliTest(unittest.TestCase):
    def test_missing_chat_model_prints_helpful_error_without_traceback(self):
        env = {"HANDY_PROVIDER": "chat"}
        stderr = io.StringIO()

        with patch.dict("os.environ", env, clear=True):
            with redirect_stderr(stderr):
                exit_code = agent.main()

        output = stderr.getvalue()
        self.assertEqual(1, exit_code)
        self.assertIn("HANDY_MODEL is required", output)
        self.assertIn("HANDY_PROVIDER can be 'stub' or 'chat'", output)
        self.assertIn("ollama serve", output)
        self.assertNotIn("Traceback", output)

    def test_chat_provider_prints_progress_to_stderr(self):
        env = {"HANDY_PROVIDER": "chat"}
        stderr = io.StringIO()
        stdout = io.StringIO()

        with patch.dict("os.environ", env, clear=True):
            with patch.object(agent, "provider_from_env", return_value=FakeProvider()):
                with redirect_stderr(stderr), redirect_stdout(stdout):
                    exit_code = agent.main()

        self.assertEqual(0, exit_code)
        self.assertEqual("fake answer\n", stdout.getvalue())
        self.assertIn("Thinking... calling the model", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
