from __future__ import annotations

from datetime import datetime

import pandas as pd

from .models import available_judges

REQUIRED_COLUMNS = ["question", "llm_answer", "retrieved_contexts", "user_review"]


def validate_input(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def evaluate_dataframe(df: pd.DataFrame, judge_names: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    validate_input(df)
    judges = available_judges()

    selected = [name for name in judge_names if name in judges]
    if not selected:
        raise ValueError("No valid judge model selected")

    base = df[REQUIRED_COLUMNS].copy()
    base["user_review"] = base["user_review"].astype(bool)

    evaluated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result_df = base.copy()
    result_df["evaluated_at"] = evaluated_at

    summary_rows = []
    for name in selected:
        judge = judges[name]
        eval_results = []
        scores = []

        for _, row in base.iterrows():
            out = judge.evaluate(row["question"], row["llm_answer"], row["retrieved_contexts"])
            eval_results.append(bool(out.evaluation_result))
            scores.append(float(out.score))

        result_df[f"{name}_result"] = eval_results
        result_df[f"{name}_score"] = scores
        result_df[f"{name}_match"] = result_df[f"{name}_result"] == result_df["user_review"]

        accuracy = result_df[f"{name}_match"].mean() * 100
        pass_rate = result_df[f"{name}_result"].mean() * 100
        summary_rows.append(
            {
                "judge_model": name,
                "accuracy_pct": round(float(accuracy), 2),
                "pass_rate_pct": round(float(pass_rate), 2),
                "avg_score": round(float(sum(scores) / len(scores)), 4),
                "rows": len(result_df),
                "evaluated_at": evaluated_at,
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    return result_df, summary_df, evaluated_at
