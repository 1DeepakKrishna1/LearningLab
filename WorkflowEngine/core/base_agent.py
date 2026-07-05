from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass
