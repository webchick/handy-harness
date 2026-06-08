"""The harness itself: a tool or two, a dispatcher, and the agentic loop.

Run it:  python3 agent.py
"""

from model_types import Message, Role, ToolResult
from stub_provider import StubProvider


# --- Tools -----------------------------------------------------------------
# A "tool" is just a normal Python function plus a schema describing it. The
# schema is what we show the model so it knows the tool exists and how to call
# it; the function is what actually runs when the model asks for it.

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
    """Run one tool the model asked for. We catch errors on purpose: a tool
    that blows up should hand the model a readable error to react to, not crash
    the whole loop. This is the seed of a real 'guardrails' layer."""
    entry = TOOLS.get(name)
    if entry is None:
        return ToolResult(call_id="", content=f"Unknown tool: {name}", is_error=True)
    try:
        output = entry["fn"](**arguments)
        return ToolResult(call_id="", content=str(output))
    except Exception as e:
        return ToolResult(call_id="", content=f"Tool error: {e}", is_error=True)


# --- The loop --------------------------------------------------------------

def run(provider, user_input, system="", max_iters=10):
    # The conversation history is the agent's whole memory. It starts with just
    # the user's question; everything else gets appended as we go.
    history = [Message(role=Role.USER, content=user_input)]
    tool_schemas = [t["schema"] for t in TOOLS.values()]

    # Each pass through this loop is one call to the model. We cap the number of
    # passes so a confused agent can't loop forever (stopping condition #1).
    for _ in range(max_iters):
        # Hand the model the ENTIRE history plus the tool menu, every time.
        assistant_msg = provider.complete(history, tool_schemas, system)
        history.append(assistant_msg)

        # No tool calls means the model gave a final answer — we're done
        # (stopping condition #2).
        if not assistant_msg.tool_calls:
            return assistant_msg.content

        # Otherwise the model asked for one or more tools. Run each one and
        # append its result to the history, then loop back so the model can
        # see what happened and decide what's next.
        for call in assistant_msg.tool_calls:
            result = dispatch(call.name, call.arguments)
            result.call_id = call.id  # tie the result back to the request
            history.append(Message(role=Role.TOOL, tool_result=result))

    return "Stopped: hit max iterations without a final answer."


if __name__ == "__main__":
    answer = run(
        provider=StubProvider(),  # swap this line for a real provider later
        user_input="What is the meaning of life?",
        system="You are a helpful assistant.",
    )
    print(answer)
