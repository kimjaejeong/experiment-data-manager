from __future__ import annotations

import ast
import re
from dataclasses import asdict

from .base import JudgeModel, JudgeOutput


def _parse_context(raw: str) -> str:
    text = str(raw or "")
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return " ".join(str(x) for x in parsed)
    except Exception:  # noqa: BLE001
        pass
    return text


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").lower())


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[가-힣a-zA-Z0-9]+", (s or "").lower()))


QUESTION_RULES = {
    "공급망금융이란 무엇인가요?": {"must": ["거래", "자금", "지원"], "avoid": ["개인대출"]},
    "공급망금융은 누가 이용하나요?": {"must": ["중소기업", "협력사"], "avoid": ["스타트업만"]},
    "공급망금융과 일반 기업대출의 차이는?": {"must": ["매출채권", "재무"], "avoid": ["완전히동일"]},
    "공급망금융은 담보가 필요한가요?": {"must": ["매출채권", "추가담보"], "avoid": ["부동산담보필수"]},
    "KB국민은행의 공급망금융 상품에는 어떤 것이 있나요?": {"must": ["kb셀러론", "kb메가셀러론"], "avoid": ["주택담보대출"]},
    "KB셀러론이란 무엇인가요?": {"must": ["중소기업", "매출채권"], "avoid": ["개인고객"]},
    "KB메가셀러론과 KB셀러론의 차이는?": {"must": ["대기업", "중소기업"], "avoid": ["차이없음"]},
    "공급망금융 대출한도는 어떻게 되나요?": {"must": ["신용도", "매출채권"], "avoid": ["고정"]},
    "공급망금융 대출금리는 어떻게 산정되나요?": {"must": ["신용도", "거래", "리스크"], "avoid": ["항상고정"]},
    "공급망금융 대출 기간은?": {"must": ["단기", "1년"], "avoid": ["최대5년고정"]},
}


class StrictRuleJudge(JudgeModel):
    name = "strict_rule_judge"

    def evaluate(self, question: str, llm_answer: str, retrieved_contexts: str) -> JudgeOutput:
        answer = _norm(llm_answer)
        rule = QUESTION_RULES.get(question, {"must": [], "avoid": []})
        must_hits = sum(1 for k in rule["must"] if _norm(k) in answer)
        avoid_hits = sum(1 for k in rule["avoid"] if _norm(k) in answer)

        must_score = must_hits / max(1, len(rule["must"]))
        penalty = min(1.0, avoid_hits * 0.6)
        score = max(0.0, min(1.0, must_score - penalty))

        return JudgeOutput(
            evaluation_result=score >= 0.5,
            score=round(score, 4),
            details={"must_hits": must_hits, "avoid_hits": avoid_hits},
        )


class RagasStyleJudge(JudgeModel):
    name = "ragas_style_judge"

    def evaluate(self, question: str, llm_answer: str, retrieved_contexts: str) -> JudgeOutput:
        context_text = _parse_context(retrieved_contexts)
        answer_tokens = _tokens(llm_answer)
        context_tokens = _tokens(context_text)
        question_tokens = _tokens(question)

        if not answer_tokens:
            faithfulness = 0.0
            answer_relevancy = 0.0
        else:
            faithfulness = len(answer_tokens & context_tokens) / len(answer_tokens)
            answer_relevancy = len(answer_tokens & question_tokens) / len(answer_tokens)

        score = (faithfulness * 0.65) + (answer_relevancy * 0.35)

        return JudgeOutput(
            evaluation_result=score >= 0.35,
            score=round(score, 4),
            details={
                "faithfulness": round(faithfulness, 4),
                "answer_relevancy": round(answer_relevancy, 4),
            },
        )


class LenientPromptJudge(JudgeModel):
    name = "lenient_prompt_judge"

    def evaluate(self, question: str, llm_answer: str, retrieved_contexts: str) -> JudgeOutput:
        context_text = _parse_context(retrieved_contexts)
        answer_n = _norm(llm_answer)
        context_n = _norm(context_text)

        support_ratio = 0.0
        if answer_n:
            overlap_chars = sum(1 for ch in set(answer_n) if ch in set(context_n))
            support_ratio = overlap_chars / max(1, len(set(answer_n)))

        contradiction_keywords = ["항상", "반드시", "무조건", "동일"]
        contradiction = any(k in answer_n for k in contradiction_keywords)
        score = (support_ratio * 0.8) + (0.2 if not contradiction else 0.0)

        return JudgeOutput(
            evaluation_result=score >= 0.45,
            score=round(score, 4),
            details={"support_ratio": round(support_ratio, 4), "contradiction_flag": contradiction},
        )


def available_judges() -> dict[str, JudgeModel]:
    judges = [StrictRuleJudge(), RagasStyleJudge(), LenientPromptJudge()]
    return {j.name: j for j in judges}


def output_to_dict(out: JudgeOutput) -> dict:
    return asdict(out)
