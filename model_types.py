"""The 'normalized format' — the one simple language our loop speaks.

Every AI provider shapes its requests and responses a little differently.
Rather than let those differences leak into the loop, we define our own four
tiny types here. Each provider adapter's job is to translate to and from these.
The loop only ever sees these — never a provider's raw format.
"""

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    # Who's "speaking" in a given message. Same four roles every provider uses.
    SYSTEM = "system"        # the standing instructions
    USER = "user"            # the human
    ASSISTANT = "assistant"  # the model
    TOOL = "tool"            # the output of a tool we ran


@dataclass
class ToolCall:
    """The model asking us to run a tool. Note it's a *request*, not an action —
    the model can't run anything itself, it can only ask."""
    id: str          # so we can match this request up with its result later
    name: str        # which tool it wants
    arguments: dict  # the args, already parsed into a dict for us by the adapter


@dataclass
class ToolResult:
    """What we got back after actually running the tool. Goes back into the
    conversation so the model can see what happened."""
    call_id: str            # matches the ToolCall.id above
    content: str            # the tool's output, as text the model can read
    is_error: bool = False  # did the tool blow up? the model can react if so


@dataclass
class Message:
    """One turn in the conversation. The whole history is just a list of these,
    and that list IS the agent's memory — the model remembers nothing on its
    own, so we hand it the full list every single time we call it."""
    role: Role
    content: str = ""
    # Only set on assistant turns where the model wants to use tools:
    tool_calls: list = field(default_factory=list)
    # Only set on tool turns, carrying a tool's output back to the model:
    tool_result: object = None
