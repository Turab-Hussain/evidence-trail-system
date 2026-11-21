"""Gemini client tests using a fake SDK client (no network, no API key)."""

from types import SimpleNamespace
from typing import Any

import pytest

from evidence_trail.agents import RequirementExtractionAgent
from evidence_trail.config import Settings
from evidence_trail.container import build_container, build_llm
from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import LLMError
from evidence_trail.domain.models import SourceMessage
from evidence_trail.llm.gemini_client import GeminiLLMClient


class FakeModels:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text, self.error, self.calls = text, error, []

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


def _client(
    text: str | None = None, error: Exception | None = None
) -> tuple[GeminiLLMClient, FakeModels]:
    models = FakeModels(text, error)
    return GeminiLLMClient("key", "test-model", client=SimpleNamespace(models=models)), models


def test_json_mode_request_is_sent() -> None:
    llm, models = _client('{"requirements": []}')
    assert llm.generate_json("sys", "user text") == {"requirements": []}
    call = models.calls[0]
    assert call["model"] == "test-model" and call["contents"] == "user text"
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].system_instruction == "sys"


def test_fenced_json_is_parsed() -> None:
    llm, _ = _client('```json\n{"a": 1}\n```')
    assert llm.generate_json("s", "u") == {"a": 1}


@pytest.mark.parametrize("text", ["no json here", "{broken", "[1, 2]", None])
def test_bad_answers_raise_llm_error(text: str | None) -> None:
    llm, _ = _client(text)
    with pytest.raises(LLMError):
        llm.generate_json("s", "u")


def test_sdk_error_becomes_llm_error() -> None:
    llm, _ = _client(error=RuntimeError("quota"))
    with pytest.raises(LLMError, match="quota"):
        llm.generate_json("s", "u")


def test_extraction_agent_uses_gemini_answer() -> None:
    llm, _ = _client(
        '{"requirements": [{"title": "Payments", "description": "Support JazzCash",'
        ' "type": "functional", "priority": "high", "confidence": 0.9, "snippet": "JazzCash"}]}'
    )
    msg = SourceMessage(project_id="p", channel=Channel.WHATSAPP, content="pay by JazzCash")
    [req] = RequirementExtractionAgent(llm).run(msg)
    assert req.title == "Payments" and req.confidence == 0.9


def test_extraction_falls_back_when_gemini_down() -> None:
    llm, _ = _client(error=RuntimeError("503"))
    msg = SourceMessage(project_id="p", channel=Channel.DOCUMENT, content="We need a login page.")
    assert len(RequirementExtractionAgent(llm).run(msg)) == 1


def test_gemini_provider_requires_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        build_llm(Settings(llm_provider="gemini"))


def test_container_accepts_injected_llm_end_to_end() -> None:
    llm, _ = _client('{"requirements": [{"title": "Login", "description": "Users can log in"}]}')
    container = build_container(Settings(db_path=":memory:"), llm)
    pid = container.projects.create("p", "c").project_id
    result = container.pipeline.ingest(pid, Channel.DOCUMENT, "anything at all")
    assert len(result.created) == 1
