from model_types import Message, Role, ToolResult
from provider import ModelProvider


def echo_tool(query: str) -> str:
    return f"You said '{query}', and it is 42 characters of wisdom."


TOOLS = {
    "echo": {
        "schema": {
            "name": "echo",
            "description": "Echoes the query back with a flourish.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        "fn": echo_tool,
    }
}


def dispatch(name, arguments):
    entry = TOOLS.get(name)
    if entry is None:
        return ToolResult(call_id="", content=f"Unknown tool: {name}", is_error=True)
    try:
        output = entry["fn"](**arguments)
        return ToolResult(call_id="", content=str(output))
    except Exception as e:
        return ToolResult(call_id="", content=f"Tool error: {e}", is_error=True)


def run(provider, user_input, system="", max_iters=10):
    history = [Message(role=Role.USER, content=user_input)]
    tool_schemas = [t["schema"] for t in TOOLS.values()]
    for i in range(max_iters):
        assistant_msg = provider.complete(history, tool_schemas, system)
        history.append(assistant_msg)
        print(f"  [iter {i}] assistant: content={assistant_msg.content!r} "
              f"tool_calls={[c.name for c in assistant_msg.tool_calls]}")
        if not assistant_msg.tool_calls:
            return assistant_msg.content
        for call in assistant_msg.tool_calls:
            result = dispatch(call.name, call.arguments)
            result.call_id = call.id
            print(f"  [iter {i}] tool {call.name}({call.arguments}) -> {result.content!r}")
            history.append(Message(role=Role.TOOL, tool_result=result))
    return "Stopped: hit max iterations without a final answer."


if __name__ == "__main__":
    from stub_provider import StubProvider
    print("--- running loop ---")
    answer = run(StubProvider(), "What is the meaning of life?",
                 system="You are a helpful assistant.")
    print("FINAL ANSWER:", answer)
