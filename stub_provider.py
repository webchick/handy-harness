from model_types import Message, Role, ToolCall
from provider import ModelProvider


class StubProvider(ModelProvider):
    def complete(self, messages, tools, system=""):
        tool_has_run = any(m.role == Role.TOOL for m in messages)
        if not tool_has_run and tools:
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
        last_result = next(
            (m.tool_result.content for m in reversed(messages) if m.role == Role.TOOL),
            "(no result)",
        )
        return Message(role=Role.ASSISTANT,
                       content=f"Based on the tool output, the answer is: {last_result}")
