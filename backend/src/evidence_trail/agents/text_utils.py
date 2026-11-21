"""Small, dependency-free text helpers shared by several agents."""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+")

# Very small stop-word list; enough for short informal requirement sentences.
STOP_WORDS = frozenset(
    "a an the and or but to of in on for with at by from is are be we i you it "
    "this that our my your please can could would should will need needs want "
    "wants must have has should also just so as".split()
)


def stem(word: str) -> str:
    """Crude suffix stripper (good enough for similarity, not linguistics)."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> set[str]:
    """Lower-case, stop-word-filtered, stemmed token set."""
    return {stem(w) for w in _WORD.findall(text.lower()) if w not in STOP_WORDS}


def jaccard(left: set[str], right: set[str]) -> float:
    """Jaccard similarity of two sets (``0.0`` when both are empty)."""
    if not left and not right:
        return 0.0
    return len(left & right) / len(left | right)


def text_similarity(left: str, right: str) -> float:
    """Token-based similarity between two strings, in ``[0, 1]``."""
    return jaccard(tokenize(left), tokenize(right))
