from typing import Any

from evidence_trail.agents import (
    AmbiguityDetectionAgent,
    ConfirmationDraftAgent,
    ConfirmationInput,
    ConsolidationAgent,
    ConsolidationInput,
    RequirementExtractionAgent,
)
from evidence_trail.domain.enums import AmbiguityType, Channel, Priority, RequirementType
from evidence_trail.domain.exceptions import LLMError
from evidence_trail.domain.models import Requirement, SourceMessage, SourceReference
from evidence_trail.llm.base import LLMClient


def _msg(text: str) -> SourceMessage:
    return SourceMessage(project_id="p", channel=Channel.WHATSAPP, content=text)


class FakeLLM(LLMClient):
    def __init__(self, answer: dict[str, Any] | None = None, fail: bool = False) -> None:
        self.answer, self.fail = answer or {}, fail

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if self.fail:
            raise LLMError("boom")
        return self.answer


# ---- extraction -----------------------------------------------------------
def test_heuristic_extracts_statements_not_questions() -> None:
    reqs = RequirementExtractionAgent().run(
        _msg("Hi! We need a payment option with JazzCash. Can we meet tomorrow?")
    )
    assert len(reqs) == 1
    assert reqs[0].title.lower().startswith("a payment option")
    assert reqs[0].sources[0].snippet.startswith("We need")


def test_heuristic_classifies_priority_and_type() -> None:
    [req] = RequirementExtractionAgent().run(_msg("The site must be secure and fast ASAP."))
    assert req.type is RequirementType.NON_FUNCTIONAL
    assert req.priority is Priority.HIGH


def test_llm_output_is_used_and_validated() -> None:
    llm = FakeLLM(
        {
            "requirements": [
                {"title": "Payments", "description": "Support JazzCash", "snippet": "JazzCash"},
                {"title": "x", "description": "bad item is skipped"},
            ]
        }
    )
    reqs = RequirementExtractionAgent(llm).run(_msg("anything"))
    assert [r.title for r in reqs] == ["Payments"]


def test_llm_failure_falls_back_to_heuristics() -> None:
    reqs = RequirementExtractionAgent(FakeLLM(fail=True)).run(_msg("We need a login page."))
    assert len(reqs) == 1


# ---- ambiguity ------------------------------------------------------------
def test_vague_term_flagged() -> None:
    req = Requirement(project_id="p", title="Homepage", description="Make the homepage premium")
    findings = AmbiguityDetectionAgent().run(req)
    assert any(
        f.issue_type is AmbiguityType.VAGUE_TERM and "premium" in f.explanation for f in findings
    )
    assert all(f.clarification_question for f in findings)


def test_nfr_without_number_flagged() -> None:
    req = Requirement(
        project_id="p",
        title="Security",
        description="Keep data secure",
        type=RequirementType.NON_FUNCTIONAL,
    )
    types = {f.issue_type for f in AmbiguityDetectionAgent().run(req)}
    assert AmbiguityType.MISSING_CONSTRAINT in types


def test_conflicting_numbers_flagged() -> None:
    req = Requirement(
        project_id="p",
        title="Speed",
        description="Load fast",
        sources=[
            SourceReference(source_id="a", snippet="load within 3 seconds"),
            SourceReference(source_id="b", snippet="load within 5 seconds"),
        ],
    )
    conflicts = [
        f for f in AmbiguityDetectionAgent().run(req) if f.issue_type is AmbiguityType.CONFLICT
    ]
    assert len(conflicts) == 1 and "3" in conflicts[0].explanation


def test_clean_requirement_has_no_findings() -> None:
    req = Requirement(project_id="p", title="Reset", description="Users reset password by email")
    assert AmbiguityDetectionAgent().run(req) == []


# ---- consolidation --------------------------------------------------------
def test_similar_requirements_match_and_merge_keeps_provenance() -> None:
    a = Requirement(
        project_id="p",
        title="JazzCash payment",
        description="Add JazzCash payment",
        sources=[SourceReference(source_id="s1", snippet="a")],
    )
    b = Requirement(
        project_id="p",
        title="JazzCash payment option",
        description="We want JazzCash payment urgently",
        priority=Priority.HIGH,
        sources=[SourceReference(source_id="s2", snippet="b")],
    )
    agent = ConsolidationAgent(0.4)
    assert agent.run(ConsolidationInput(b, [a])) is a
    assert agent.merge(a, b) is True
    assert a.source_ids == ["s1", "s2"] and a.priority is Priority.HIGH


def test_unrelated_requirements_do_not_match() -> None:
    a = Requirement(project_id="p", title="Dark mode", description="Add dark mode")
    b = Requirement(project_id="p", title="Invoices", description="Export invoices as PDF")
    assert ConsolidationAgent(0.4).run(ConsolidationInput(b, [a])) is None


def test_confirmation_draft_lists_clarifications() -> None:
    req = Requirement(project_id="p", title="Homepage", description="Premium homepage")
    findings = AmbiguityDetectionAgent().run(req)
    text = ConfirmationDraftAgent().run(ConfirmationInput(req, findings))
    assert "Homepage" in text and "premium" in text.lower() and "CONFIRM" in text


def test_title_drops_label_and_never_ends_on_dangling_word() -> None:
    [req] = RequirementExtractionAgent().run(
        _msg(
            "Small change for the website: please remove card payments "
            "and add JazzCash and Bank Transfer instead."
        )
    )
    assert req.title.startswith("Remove card payments")

    [long] = RequirementExtractionAgent().run(
        _msg(
            "The homepage must show one banner with a single Shop now button instead of the slider."
        )
    )
    assert long.title.endswith("\u2026")
    assert long.title.rstrip("\u2026").split()[-1].lower() not in {"a", "with", "the", "of", "and"}
