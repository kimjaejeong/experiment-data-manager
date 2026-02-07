from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class JudgeOutput:
    evaluation_result: bool
    score: float
    details: dict[str, Any]


class JudgeModel(ABC):
    name: str

    @abstractmethod
    def evaluate(self, question: str, llm_answer: str, retrieved_contexts: str) -> JudgeOutput:
        raise NotImplementedError
