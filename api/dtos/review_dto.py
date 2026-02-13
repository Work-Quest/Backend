from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal


QualityLabel = Literal[-1, 0, 1]


@dataclass(frozen=True)
class TaskFacts:
    """
    Minimal task facts for trust-score alignment checks.
    Store timestamps as floats (epoch seconds) to keep the domain independent of Django/DTZ.
    """

    priority: int
    created_at_ts: float
    completed_at_ts: Optional[float]
    deadline_ts: Optional[float]




