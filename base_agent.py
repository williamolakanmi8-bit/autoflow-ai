from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentResult:
    actions: list[str]
    tokens_used: int
    output: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all AutoFlow agents."""

    @abstractmethod
    async def execute(self, run_id: str, classification, data: dict) -> AgentResult:
        """Execute the agent's task and return a result."""
        ...

    def _count_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        return max(1, len(text) // 4)
