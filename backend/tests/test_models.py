import pytest

from evidence_trail.domain.enums import Channel, RequirementStatus
from evidence_trail.domain.exceptions import InvalidStateTransitionError
from evidence_trail.domain.models import Requirement, SourceMessage


def _req() -> Requirement:
    return Requirement(project_id="p", title="Login", description="Users can log in")


def test_valid_transition_chain() -> None:
    req = _req()
    req.transition_to(RequirementStatus.APPROVED)
    req.transition_to(RequirementStatus.CONFIRMED)
    assert req.status is RequirementStatus.CONFIRMED


def test_rejected_is_terminal() -> None:
    req = _req()
    req.transition_to(RequirementStatus.REJECTED)
    with pytest.raises(InvalidStateTransitionError):
        req.transition_to(RequirementStatus.APPROVED)


def test_cannot_confirm_unapproved() -> None:
    with pytest.raises(InvalidStateTransitionError):
        _req().transition_to(RequirementStatus.CONFIRMED)


def test_source_gets_evidence_uri() -> None:
    msg = SourceMessage(project_id="p", channel=Channel.EMAIL, content="hi")
    assert msg.evidence_uri == f"evidence://p/{msg.source_id}"


def test_load_dotenv_reads_file_without_overriding_env(tmp_path, monkeypatch):
    from evidence_trail.config import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text('# comment\nFOO_TEST_KEY="abc"\nBAR_TEST_KEY=1\n', encoding="utf-8")
    monkeypatch.delenv("FOO_TEST_KEY", raising=False)
    monkeypatch.setenv("BAR_TEST_KEY", "keep")
    load_dotenv(env_file)
    import os

    assert os.environ["FOO_TEST_KEY"] == "abc"
    assert os.environ["BAR_TEST_KEY"] == "keep"
    monkeypatch.delenv("FOO_TEST_KEY", raising=False)
