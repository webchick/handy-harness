# handy-harness

A small, model-agnostic **agent harness** built from scratch in plain Python — then progressively upgraded to use emerging industry standards (MCP, OpenTelemetry, A2A) so you can see exactly what each standard buys you.

The goal is to start with the simplest thing that exercises a real agentic loop, with zero dependencies, then layer in the standards one at a time.

## What's an agent harness?

A harness is the scaffolding around a language model that turns it from something that just _answers_ into something that _does_—it can take a task, use tools to work on it, look at what happened, and keep going until it's done.

Worth knowing: the model itself doesn't remember anything from one message to the next—it starts fresh every time. The harness is what gives it:

- **memory** — by handing it the whole conversation again on every turn
- **hands** — tools it can actually use, like searching the web, reading a file, or running code, instead of just talking about doing those things
- **a way to keep going** — the loop that lets it take a step, see how it went, and decide what to do next, over and over until the job's done

The heart of it is the **agentic loop**:

```
1. Build a prompt (system + history + available tools)
2. Call the model
3. Is the response a final answer, or a tool call?
4. If tool call -> run the tool, capture the result
5. Append call + result to history
6. Go to 2
7. If final answer -> stop and return it
```

## Project status

**Stage 1 — raw Python, no dependencies. ✅ Done.**

A complete agentic loop running against a stubbed "model," proving the architecture end to end without needing an API key or network.

Planned stages:

| Stage | Adds | Status |
|-------|------|--------|
| 1 | Raw-Python loop + normalized types + stub provider | ✅ Done |
| 2 | Real Chat-Completions-shaped adapter (OpenAI / Ollama / vLLM / etc.) | ⬜ Next |
| 3 | Tools via **MCP** (Model Context Protocol) | ⬜ Planned |
| 4 | Observability via **OpenTelemetry** | ⬜ Planned |
| 5 | Expose the agent over **A2A** (Agent2Agent) | ⬜ Optional |

## Design: the adapter pattern

Different AI companies (and open-source models) all speak slightly different dialects—the requests and responses are shaped a bit differently for each one. The trick is to keep all that messiness in one small, walled-off corner of the code. The main loop speaks just _one_ simple language of its own, and for each AI provider there's a translator that converts between that one language and whatever dialect the provider wants. So the main loop never has to care who it's talking to—swapping OpenAI for a local model is just swapping one translator for another.

```
        +---------------------------------+
        |        Agent loop (core)        |
        |  history, dispatch, stopping    |
        +----------------+----------------+
                         |  speaks ONE internal format
        +----------------+----------------+
        |       ModelProvider (ABC)       |
        |   .complete(messages, tools)    |
        |        -> normalized Message    |
        +--+-------------+-------------+---+
           |             |             |
      +----+----+   +----+----+   +----+---------+
      |  Stub   |   | OpenAI- |   |  Anthropic   |
      |(stage 1)|   |  shape  |   |   (native)   |
      +---------+   +---------+   +--------------+
```

Because the [OpenAI **Chat Completions** request shape](https://platform.openai.com/docs/api-reference/chat/create) has become the de-facto lingua franca that most local runtimes (Ollama, vLLM, LM Studio, llama.cpp, Together, Groq, ...) also expose, a single Chat-Completions-shaped adapter with a configurable `base_url` covers a large swath of models — including fully open ones — with no vendor-specific code.

## Files

| File | Role |
|------|------|
| `model_types.py` | The normalized internal format: `Role`, `Message`, `ToolCall`, `ToolResult`. The entire contract between the loop and the adapters. |
| `provider.py` | The `ModelProvider` abstract base class — one method, `complete()`. The seam the design hinges on. |
| `stub_provider.py` | A scripted fake "model" that makes the two decisions a real model makes (call a tool / give a final answer). Enough to exercise the whole loop offline. |
| `agent.py` | The harness itself: a tiny tool registry, the tool dispatcher, and the core `run()` loop. Runnable entry point. |

> Note: the types file is `model_types.py` rather than `types.py` to avoid colliding with Python's standard-library `types` module.

## Running it

No dependencies, no setup:

```bash
python3 agent.py
```

Expected output — the loop turning over once to call a tool, then again to answer:

```
--- running loop ---
  [iter 0] assistant: content="I'll use a tool to answer that." tool_calls=['echo']
  [iter 0] tool echo({'query': 'What is the meaning of life?'}) -> "You said '...', and it is 42 characters of wisdom."
  [iter 1] assistant: content="Based on the tool output, the answer is: ..." tool_calls=[]
FINAL ANSWER: Based on the tool output, the answer is: ...
```

## The normalized format

Four types are the whole contract:

- **`Message`** — one turn: a `role`, optional `content`, optional `tool_calls` (on assistant turns), optional `tool_result` (on tool turns).
- **`ToolCall`** — a model's request to act: an `id`, a `name`, and `arguments` as an already-parsed `dict`.
- **`ToolResult`** — the outcome of a tool run: a `call_id` (correlating back to the call), `content`, and an `is_error` flag.
- **`Role`** — `system` / `user` / `assistant` / `tool`.

The key invariant: `arguments` is *always* a parsed `dict` and `tool_calls` is *always* a list. Providers differ here (OpenAI hands back a JSON *string*; Anthropic hands back an object) — that difference dies inside the adapter and never reaches the loop.

## What's deliberately not here yet

So the edges are clear:

- **No real context-window management** — history just grows. Truncation / summarization comes later.
- **No parallel tool execution** — tool calls run sequentially.
- **No streaming** — responses are returned whole.
- **Plain-dict tool registry** — fine for now; gets replaced by an MCP client in stage 3.

None of these change the *shape* of the loop, which is the point.

## What's already working that matters

- The core loop neither knows nor cares that it's talking to a stub — swapping in a real provider won't change `run()` by a character.
- Two explicit stopping conditions: a max-iterations cap and final-answer detection.
- Tool execution is wrapped so a crashing tool becomes a readable `ToolResult(is_error=True)` the model can react to, rather than killing the loop — the seed of a guardrails layer.

## Background / further reading

- [**MCP (Model Context Protocol)**](https://github.com/modelcontextprotocol) — agent ↔ tools. The de-facto standard for connecting models to external tools and data.
- [**A2A (Agent2Agent)**](https://github.com/a2aproject/A2A) — agent ↔ *another* agent, across a trust boundary. Complementary to MCP, not competing.
- [**OpenTelemetry**](https://github.com/open-telemetry) — standard tracing; eval data and production runtime data are fundamentally the same shape (which model, what input/output, how long, what cost).

## License
MIT
