# handy-harness

A small, model-agnostic **agent harness** built from scratch in plain Python — then progressively upgraded to use emerging industry standards (MCP, OpenTelemetry, A2A) so you can see exactly what each standard buys you.

The goal is to start with the simplest thing that exercises a real agentic loop, with zero dependencies, then layer in the standards one at a time.

## Workshop stages

This repo is built **workshop-style**: each stage is a branch, so you can check one out and run it, then `git diff` against the next to see exactly what changed and why.

```bash
git checkout stage-0-concepts   # you are here: the agentic loop, with a fake model
git checkout stage-1-real-model # swap the fake model for a real one (Chat Completions shape)
git checkout stage-2-mcp        # tools via MCP (Model Context Protocol)
git checkout stage-3-otel       # observability via OpenTelemetry
git checkout stage-4-a2a        # (optional capstone) expose the agent over A2A
```

| Stage | Branch | Adds | Status |
|-------|--------|------|--------|
| 0 | `stage-0-concepts` | The agentic loop + normalized types + a stub (fake) model. Zero dependencies. | Done |
| 1 | `stage-1-real-model` | A real Chat-Completions-shaped adapter (OpenAI / Ollama / vLLM / etc.) | Next |
| 2 | `stage-2-mcp` | Tools via **MCP** (Model Context Protocol) | Planned |
| 3 | `stage-3-otel` | Observability via **OpenTelemetry** | Planned |
| 4 | `stage-4-a2a` | Expose the agent over **A2A** (Agent2Agent) | Optional |

> **New here? Start on `stage-0-concepts`.** It's the whole idea in its simplest form — a real agentic loop driving a deliberately fake "model," so nothing distracts from the structure.

---

# Stage 0: the concept

This branch is the agentic loop in its purest form. There's no real AI model, no API key, no network, no dependencies — just the scaffolding, driven by a scripted stub that stands in for a model. The point is to see the *shape* of a harness with nothing else in the way.

## What's an agent harness?

A harness is the scaffolding around a language model that turns it from something that just *answers* into something that *does* — it can take a task, use tools to work on it, look at what happened, and keep going until it's done.

Worth knowing: the model itself doesn't remember anything from one message to the next — it starts fresh every time. The harness is what gives it:

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

## Running it

No dependencies, no setup:

```bash
python3 agent.py
```

You'll see the agent's final answer:

```
Based on the tool output, the answer is: You said 'What is the meaning of life?', and it is 42 characters of wisdom.
```

That one line is the end of a two-step conversation the harness had with the (fake) model on your behalf. Here's what happened to produce it.

## Running the tests

Stage 0 also has a small test suite, using only Python's built-in `unittest`
module:

```bash
python3 -m unittest
```

You should see output like:

```text
.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK
```

These tests are deliberately small. They are not trying to prove that an AI
model is smart; there is no real model in stage 0. They prove that the harness
contract works:

- `test_agent.py` checks the outside behavior of the harness: the full loop can
  reach a final answer with `StubProvider`, the `echo` tool can run, and unknown
  tools become readable errors instead of crashing the process.
- `test_stub_provider.py` checks the fake model's two scripted decisions: first
  it asks for a tool, then after a tool result appears in history, it returns a
  final answer.

That gives later stages a baseline. When stage 1 swaps in a real model adapter,
or stage 2 swaps the plain tool registry for MCP, these tests keep the basic
loop behavior anchored.

## How it works

Each trip through the loop is **one call to the model**. This run takes two trips:

**Trip 1 — the model decides to act.** The harness hands the model the conversation so far (just your question) plus the list of tools it's allowed to use. The model replies: *"I want to use the `echo` tool."* Important: the model didn't *run* anything — it can't. It only produced text: a structured request asking the harness to run a tool on its behalf.

**The harness runs the tool.** Back in the loop, we see a tool request, so we actually call the `echo` function, capture its output, and add that result to the conversation. Then we loop back around.

**Trip 2 — the model answers.** The harness calls the model again, handing it the now-longer conversation (which includes the tool's result). This time the model replies with plain text and *no* tool request. An empty tool-request list is the harness's signal that the model is done — so the loop stops and returns that final answer.

The thing worth burning into memory: **the model never did anything itself.** It only ever produced text — either a final answer, or a request to use a tool. Every real action (running the tool, catching errors, updating the conversation, deciding whether to loop again) was the harness's job. The stub model here is deliberately dumb — its entire "intelligence" is checking whether a tool has run yet — and *it still behaves like an agent*. That tells you the agent-like behavior comes from the **loop**, not from the model's smarts. The model supplies the decisions; the harness supplies everything else.

## Design: the adapter pattern

Different AI companies (and open-source models) all speak slightly different dialects — the requests and responses are shaped a bit differently for each one. The trick is to keep all that messiness in one small, walled-off corner of the code. The main loop speaks just *one* simple language of its own, and for each AI provider there's a translator that converts between that one language and whatever dialect the provider wants. So the main loop never has to care who it's talking to — swapping OpenAI for a local model is just swapping one translator for another.

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
|(stage 0)|   |  shape  |   |   (native)   |
+---------+   +---------+   +--------------+
```

In stage 0 the only translator that exists is the **Stub** — a fake model. The real ones arrive in later stages. Because the [OpenAI **Chat Completions** request shape](https://platform.openai.com/docs/api-reference/chat/create) has become the de-facto lingua franca that most local runtimes (Ollama, vLLM, LM Studio, llama.cpp, Together, Groq, ...) also expose, a single Chat-Completions-shaped adapter with a configurable `base_url` covers a large swath of models — including fully open ones — with no vendor-specific code.

## Files

| File | Role |
|------|------|
| `model_types.py` | The normalized format — the *one simple language* the loop speaks: `Role`, `Message`, `ToolCall`, `ToolResult`. The entire contract between the loop and any provider. |
| `provider.py` | The `ModelProvider` abstract base class — one method, `complete()`. The seam the whole design hinges on. |
| `stub_provider.py` | A scripted fake "model" that makes the only two decisions a real model makes in a loop (call a tool / give a final answer). Lets the whole loop run offline. |
| `agent.py` | The harness itself: a tiny tool registry, the tool dispatcher, and the core `run()` loop. Runnable entry point. |
| `test_agent.py` | Tests the harness loop and tool dispatcher from the outside. |
| `test_stub_provider.py` | Tests the stub provider's two-step scripted behavior. |

> Note: the types file is `model_types.py` rather than `types.py` to avoid colliding with Python's standard-library `types` module.

## The normalized format

Four tiny types are the whole contract between the loop and any provider:

- **`Message`** — one turn: a `role`, optional `content`, optional `tool_calls` (on assistant turns), optional `tool_result` (on tool turns). The full list of these *is* the agent's memory.
- **`ToolCall`** — the model's request to act: an `id`, a `name`, and `arguments` as an already-parsed `dict`. (A request, not an action — the model can only ask.)
- **`ToolResult`** — the outcome of a tool run: a `call_id` (tying it back to the request), `content`, and an `is_error` flag.
- **`Role`** — `system` / `user` / `assistant` / `tool`.

The key invariant: `arguments` is *always* a parsed `dict` and `tool_calls` is *always* a list. Real providers differ here (OpenAI hands back a JSON *string*; Anthropic hands back an object) — that difference will die inside each adapter and never reach the loop.

## What's deliberately not here yet

So the edges are clear:

- **No real model** — a stub stands in for one. Real providers arrive in stage 1.
- **No real context-window management** — history just grows. Truncation / summarization comes later.
- **No parallel tool execution** — tool calls run sequentially.
- **No streaming** — responses are returned whole.
- **Plain-dict tool registry** — fine for now; gets replaced by an MCP client in stage 2.

None of these change the *shape* of the loop, which is the point.

## What's already working that matters

- The core loop neither knows nor cares that it's talking to a stub — swapping in a real provider (stage 1) won't change `run()` by a character.
- Two explicit stopping conditions: a max-iterations cap and final-answer detection.
- Tool execution is wrapped so a crashing tool becomes a readable `ToolResult(is_error=True)` the model can react to, rather than killing the loop — the seed of a guardrails layer.

## Background / further reading

- [**MCP (Model Context Protocol)**](https://github.com/modelcontextprotocol) — agent <-> tools. The de-facto standard for connecting models to external tools and data. (Arrives in stage 2.)
- [**A2A (Agent2Agent)**](https://github.com/a2aproject/A2A) — agent <-> *another* agent, across a trust boundary. Complementary to MCP, not competing. (Optional stage 4.)
- [**OpenTelemetry**](https://github.com/open-telemetry) — standard tracing; eval data and production runtime data are fundamentally the same shape (which model, what input/output, how long, what cost). (Arrives in stage 3.)

## License

MIT
