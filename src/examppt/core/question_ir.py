from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class QuestionAnchor:
    number: int
    page: int
    x0: float
    top: float
    bottom: float
    text: str
    confidence: float = 1.0


@dataclass(frozen=True)
class PageSegment:
    page: int
    x0: float
    top: float
    x1: float
    bottom: float


@dataclass
class QuestionRegion:
    number: int
    anchor: QuestionAnchor
    segments: list[PageSegment]
    image: str | None = None
    cross_page: bool = False
    confidence: float = 1.0


@dataclass(frozen=True)
class Section:
    title: str
    start_question: int
    page: int
    top: float


@dataclass
class ScanResult:
    source_pdf: str
    name: str
    pages: list[dict[str, Any]]
    questions: list[QuestionRegion]
    sections: list[Section] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = "PASS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
