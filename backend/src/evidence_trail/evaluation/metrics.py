"""Evaluation metrics from the proposal's testing plan (precision / recall / F1)."""

from __future__ import annotations

from dataclasses import dataclass

from evidence_trail.agents.text_utils import text_similarity


@dataclass(frozen=True)
class Scores:
    """Precision, recall and F1 with the raw counts behind them."""

    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        total = self.true_positives + self.false_positives
        return self.true_positives / total if total else 0.0

    @property
    def recall(self) -> float:
        total = self.true_positives + self.false_negatives
        return self.true_positives / total if total else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def match_texts(predicted: list[str], truth: list[str], threshold: float = 0.4) -> Scores:
    """Greedy one-to-one fuzzy matching of predicted vs ground-truth requirement texts.

    A prediction counts as correct if its token similarity to a not-yet-used
    ground-truth item reaches ``threshold``.
    """
    unused = list(truth)
    true_positives = 0
    for prediction in predicted:
        best_index, best_score = -1, 0.0
        for index, expected in enumerate(unused):
            score = text_similarity(prediction, expected)
            if score >= threshold and score > best_score:
                best_index, best_score = index, score
        if best_index >= 0:
            true_positives += 1
            unused.pop(best_index)
    return Scores(
        true_positives=true_positives,
        false_positives=len(predicted) - true_positives,
        false_negatives=len(unused),
    )


def evidence_completeness(complete_flags: list[bool]) -> float:
    """Share of requirements whose evidence trail is complete."""
    return sum(complete_flags) / len(complete_flags) if complete_flags else 0.0
