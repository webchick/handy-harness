from abc import ABC, abstractmethod
from model_types import Message


class ModelProvider(ABC):
    @abstractmethod
    def complete(self, messages, tools, system=""):
        ...
