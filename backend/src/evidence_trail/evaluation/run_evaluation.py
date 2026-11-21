"""Tiny evaluation harness: ``python -m evidence_trail.evaluation.run_evaluation``.

Runs the pipeline on a labelled dataset (``data/sample_dataset.json``) and
prints extraction precision/recall/F1 plus evidence completeness.  It compares
nothing to a baseline yet - that is Phase 9 work in the proposal.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from evidence_trail.config import Settings
from evidence_trail.container import build_container
from evidence_trail.domain.enums import Channel
from evidence_trail.evaluation.metrics import evidence_completeness, match_texts


def _wrap_raw(channel: Channel, content: str) -> object:
    """Dataset rows hold plain text; WhatsApp needs the Cloud API webhook shape."""
    if channel is Channel.WHATSAPP:
        message = {"type": "text", "text": {"body": content}}
        return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}
    return content


def evaluate(dataset_path: Path) -> dict[str, float]:
    """Run the dataset through the pipeline and return the metrics."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    container = build_container(Settings(db_path=":memory:"))
    project = container.projects.create("Evaluation", "Benchmark")

    for item in dataset["messages"]:
        channel = Channel(item["channel"])
        container.pipeline.ingest(
            project.project_id,
            channel,
            _wrap_raw(channel, item["content"]),
            sender=item.get("sender"),
        )

    requirements = container.repository.list_requirements(project.project_id)
    predicted = [f"{r.title} {r.description}" for r in requirements]
    scores = match_texts(predicted, dataset["ground_truth"])
    completeness = evidence_completeness(
        [container.evidence.get_trail(r.requirement_id).complete for r in requirements]
    )
    return {
        "predicted": float(len(predicted)),
        "ground_truth": float(len(dataset["ground_truth"])),
        "precision": round(scores.precision, 3),
        "recall": round(scores.recall, 3),
        "f1": round(scores.f1, 3),
        "evidence_completeness": round(completeness, 3),
    }


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/sample_dataset.json")
    for name, value in evaluate(path).items():
        print(f"{name:>22}: {value}")
