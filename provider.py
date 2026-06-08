"""The seam the whole design hinges on.

Every provider — OpenAI, Anthropic, a local model, our fake stub — implements
this one method. The loop talks ONLY to this interface, so swapping providers
is swapping one implementation for another and the loop never changes.
"""

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    @abstractmethod
    def complete(self, messages, tools, system=""):
        """Take the conversation so far (a list of our Messages) plus the tools
        the model is allowed to use, and return the model's next turn as a
        single Message. That Message will either have content (a final answer),
        tool_calls (it wants to act), or both."""
        ...
