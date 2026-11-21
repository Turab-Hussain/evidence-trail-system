"""Specialised agents, one responsibility each."""

from evidence_trail.agents.ambiguity import AmbiguityDetectionAgent
from evidence_trail.agents.changelog import ChangeLogAgent, ChangeLogInput
from evidence_trail.agents.confirmation import ConfirmationDraftAgent, ConfirmationInput
from evidence_trail.agents.consolidation import ConsolidationAgent, ConsolidationInput
from evidence_trail.agents.extraction import RequirementExtractionAgent

__all__ = [
    "AmbiguityDetectionAgent",
    "ChangeLogAgent",
    "ChangeLogInput",
    "ConfirmationDraftAgent",
    "ConfirmationInput",
    "ConsolidationAgent",
    "ConsolidationInput",
    "RequirementExtractionAgent",
]
