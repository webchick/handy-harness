"""A fake model, so stage 0 runs with no API key, no network, no cost.

It's deliberately dumb: it makes the only two kinds of decision a real model
makes in a loop — "use a tool" or "give an answer" — based on one simple check.
That's the whole point: if even something this dumb produces agent-like
behavior, then it's the LOOP creating that behavior, not the model's smarts.
"""

from model_types import Message, Role, ToolCall
from provider import ModelProvider


class StubProvider(ModelProvider):
    def complete(self, messages, tools, system=""):
        # Our entire "intelligence": have we run a tool yet? We check by looking
        # for a tool-role message in the history.
        tool_has_run = any(m.role == Role.TOOL for m in messages)

        if not tool_has_run and tools:
            # First pass: pretend the model decided it needs a tool, and ask to
            # run the first available one. (A real model would actually reason
            # about which tool and what arguments; we just grab the question.)
            tool = tools[0]
            user_text = next(
                (m.content for m in reversed(messages) if m.role == Role.USER), ""
            )
            return Message(
                role=Role.ASSISTANT,
                content="I'll use a tool to answer that.",
                tool_calls=[ToolCall(id="call_1", name=tool["name"],
                                     arguments={"query": user_text})],
            )

        # Second pass: a tool has run, so its result is now in the history.
        # Read it back out and produce a final answer (no tool_calls = "I'm done").
        last_result = next(
            (m.tool_result.content for m in reversed(messages) if m.role == Role.TOOL),
            "(no result)",
        )
        return Message(role=Role.ASSISTANT,
                       content=f"Based on the tool output, the answer is: {last_result}")
