"""End-to-end service tests: ingest -> review -> confirm -> trail."""

import pytest

from evidence_trail.config import Settings
from evidence_trail.container import Container, build_container
from evidence_trail.domain.enums import (
    Channel,
    ClientResponse,
    RequirementStatus,
    ReviewDecision,
)
from evidence_trail.domain.exceptions import (
    EvidenceTrailError,
    InvalidStateTransitionError,
    NotFoundError,
)


def test_ingest_creates_requirements_and_evidence(container: Container, project_id: str) -> None:
    result = container.pipeline.ingest(
        project_id,
        Channel.DOCUMENT,
        "We need a login page with email and password.",
    )
    assert len(result.created) == 1 and not result.failed_sources
    req = container.repository.get_requirement(result.created[0])
    assert req.status is RequirementStatus.PENDING_APPROVAL
    assert req.version == 1
    assert container.repository.list_versions(req.requirement_id)


def test_cross_channel_consolidation_bumps_version(container: Container, project_id: str) -> None:
    first = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "We need JazzCash payment option."
    )
    second = container.pipeline.ingest(
        project_id,
        Channel.EMAIL,
        "Subject: pay\n\nWe also want the JazzCash payment option urgently.",
    )
    req_id = first.created[0]
    assert second.updated == [req_id] and not second.created
    req = container.repository.get_requirement(req_id)
    assert req.version == 2 and len(req.source_ids) == 2


def test_merge_into_approved_requires_rereview(container: Container, project_id: str) -> None:
    req_id = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "We need JazzCash payment option."
    ).created[0]
    container.review.review(req_id, actor="pm", decision=ReviewDecision.APPROVE)
    container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "JazzCash payment option must support refunds."
    )
    assert container.repository.get_requirement(req_id).status is RequirementStatus.PENDING_APPROVAL


def test_full_lifecycle_has_complete_trail(container: Container, project_id: str) -> None:
    req_id = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "Users should reset their password by email."
    ).created[0]
    container.review.review(req_id, actor="pm", decision=ReviewDecision.APPROVE, note="ok")
    assert "Users should reset" in container.confirmation.draft(req_id)
    container.confirmation.record_response(req_id, ClientResponse.CONFIRMED)

    trail = container.evidence.get_trail(req_id)
    kinds = {e.kind for e in trail.entries}
    assert (
        trail.complete
        and {"source", "ai_step", "pm_decision", "client_confirmation", "version"} <= kinds
    )
    assert container.repository.get_requirement(req_id).status is RequirementStatus.CONFIRMED


def test_edit_creates_new_version(container: Container, project_id: str) -> None:
    req_id = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "We need a premium homepage."
    ).created[0]
    updated = container.review.review(
        req_id,
        actor="pm",
        decision=ReviewDecision.EDIT,
        edited_description="Homepage loads in 2 seconds",
    )
    assert updated.version == 2 and updated.status is RequirementStatus.APPROVED
    assert len(container.repository.list_versions(req_id)) == 2


def test_edit_without_content_rejected(container: Container, project_id: str) -> None:
    req_id = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "We need a login page."
    ).created[0]
    with pytest.raises(EvidenceTrailError):
        container.review.review(req_id, actor="pm", decision=ReviewDecision.EDIT)


def test_cannot_draft_or_confirm_before_approval(container: Container, project_id: str) -> None:
    req_id = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "We need a login page."
    ).created[0]
    with pytest.raises(InvalidStateTransitionError):
        container.confirmation.draft(req_id)
    with pytest.raises(InvalidStateTransitionError):
        container.confirmation.record_response(req_id, ClientResponse.CONFIRMED)


def test_rejected_requirement_does_not_absorb_new_evidence(
    container: Container, project_id: str
) -> None:
    first = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "We need JazzCash payment option."
    ).created[0]
    container.review.review(first, actor="pm", decision=ReviewDecision.REJECT)
    second = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "We need JazzCash payment option."
    )
    assert len(second.created) == 1 and second.created[0] != first


def test_unknown_project_and_requirement(container: Container) -> None:
    with pytest.raises(NotFoundError):
        container.pipeline.ingest("nope", Channel.DOCUMENT, "x")
    with pytest.raises(NotFoundError):
        container.review.review("nope", actor="pm", decision=ReviewDecision.APPROVE)


def test_dashboard_counts(container: Container, project_id: str) -> None:
    container.pipeline.ingest(project_id, Channel.DOCUMENT, "Make the homepage premium.")
    board = container.projects.dashboard(project_id)
    assert board["total_requirements"] == 1
    assert board["open_ambiguities"]["vague_term"] >= 1  # type: ignore[index]


def test_trail_is_chronological_after_later_events(container: Container, project_id: str) -> None:
    """Findings must stay next to the check that made them, not jump after approval."""
    req_id = container.pipeline.ingest(
        project_id, Channel.DOCUMENT, "Make the homepage premium."
    ).created[0]
    container.review.review(req_id, actor="pm", decision=ReviewDecision.APPROVE)
    kinds = [e.kind for e in container.evidence.get_trail(req_id).entries]
    assert kinds.index("ambiguity") < kinds.index("pm_decision")
    steps = [e.summary.split(":")[0] for e in container.evidence.get_trail(req_id).entries]
    assert steps.index("requirement_created") < steps.index("ambiguity_checked")


def test_trail_source_shows_supporting_text_not_message_prefix(
    container: Container, project_id: str
) -> None:
    body = "Intro text that is not a requirement. " * 8 + "\n\nWe need an order tracking page."
    req_id = container.pipeline.ingest(project_id, Channel.DOCUMENT, body).created[0]
    source = next(e for e in container.evidence.get_trail(req_id).entries if e.kind == "source")
    assert "order tracking page" in source.summary


def test_default_settings_merge_same_request_across_channels() -> None:
    """Regression: Settings and the agent must share one default threshold."""
    container = build_container(Settings(db_path=":memory:"))
    pid = container.projects.create("p", "c").project_id
    first = container.pipeline.ingest(
        pid,
        Channel.DOCUMENT,
        "Please remove card payments and add JazzCash and Bank Transfer instead.",
    )
    second = container.pipeline.ingest(
        pid,
        Channel.EMAIL,
        "Subject: x\n\nPlease add JazzCash and Bank Transfer as payment options.",
    )
    assert second.updated == first.created and not second.created
