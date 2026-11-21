"""Base class for the specialised, narrowly-scoped agents.

Agents are *pure* with respect to storage: they take domain objects in and
return domain objects out.  Persistence and orchestration live in the service
layer, which keeps every agent trivially unit-testable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Agent(ABC, Generic[InputT, OutputT]):
    """A single-responsibility processing step."""

    #: Human-readable name, recorded in evidence records.
    name: str = "agent"

    @abstractmethod
    def run(self, payload: InputT) -> OutputT:
        """Execute the agent on ``payload`` and return its output."""
