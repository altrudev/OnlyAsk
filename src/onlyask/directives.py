from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObservedContent:
    source: str
    content: str
    directive_like: bool
    disposition: str


def classify_observed_content(source: str, content: str) -> ObservedContent:
    """Flag directive-bearing external content without promoting it into authority."""

    lowered = content.lower()
    markers = (
        "ignore previous",
        "ignore all previous",
        "system instruction",
        "developer instruction",
        "reveal credentials",
        "send credentials",
        "upload credentials",
        "override permissions",
    )
    directive_like = any(marker in lowered for marker in markers)
    return ObservedContent(
        source=source,
        content=content,
        directive_like=directive_like,
        disposition="untrusted_evidence" if directive_like else "evidence",
    )
