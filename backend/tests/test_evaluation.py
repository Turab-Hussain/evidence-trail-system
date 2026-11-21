from pathlib import Path

from evidence_trail.evaluation.metrics import Scores, evidence_completeness, match_texts
from evidence_trail.evaluation.run_evaluation import evaluate


def test_scores_math() -> None:
    s = Scores(true_positives=2, false_positives=2, false_negatives=0)
    assert s.precision == 0.5 and s.recall == 1.0 and round(s.f1, 3) == 0.667


def test_match_texts_one_to_one() -> None:
    scores = match_texts(["add bank transfer payment"], ["add Bank Transfer payment", "dark mode"])
    assert (scores.true_positives, scores.false_positives, scores.false_negatives) == (1, 0, 1)


def test_completeness_empty() -> None:
    assert evidence_completeness([]) == 0.0


def test_sample_dataset_runs() -> None:
    metrics = evaluate(Path(__file__).parent.parent / "data" / "sample_dataset.json")
    assert 0.0 <= metrics["f1"] <= 1.0 and metrics["predicted"] > 0
