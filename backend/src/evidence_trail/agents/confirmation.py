"""Confirmation Draft Agent: writes the message sent to the client."""

from __future__ import annotations

from dataclasses import dataclass

from evidence_trail.agents.base import Agent
from evidence_trail.domain.models import AmbiguityFinding, Requirement


@dataclass(frozen=True)
class ConfirmationInput:
    """What the drafter needs to know."""

    requirement: Requirement
    findings: list[AmbiguityFinding]


class ConfirmationDraftAgent(Agent[ConfirmationInput, str]):
    """Template-based drafter (deterministic, so it never invents content)."""

    name = "confirmation_draft_agent"

    def run(self, payload: ConfirmationInput) -> str:
        req = payload.requirement
        lines = [
            "Hello,",
            "",
            "Please confirm that we have understood the following requirement correctly:",
            "",
            f"  Title:       {req.title}",
            f"  Details:     {req.description}",
            f"  Priority:    {req.priority.value}",
            f"  Version:     {req.version}",
            f"  Based on:    {len(req.source_ids)} message(s) from you",
        ]
        if payload.findings:
            lines += ["", "We also need a few clarifications:"]
            lines += [f"  - {finding.clarification_question}" for finding in payload.findings]
        lines += [
            "",
            "Reply CONFIRM if this is correct, or tell us what should change.",
            "",
            "Thank you.",
        ]
        return "\n".join(lines)
