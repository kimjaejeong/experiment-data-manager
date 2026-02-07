from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from judge_models import REQUIRED_COLUMNS, available_judges, evaluate_dataframe, validate_input


st.set_page_config(page_title="Simple Judge Lab", layout="wide")
st.title("Judge 실험 비교")
st.caption("엑셀 업로드 → Judge별 평가 → 정확도 비교 → 결과 엑셀 다운로드")

uploaded = st.file_uploader("엑셀 업로드 (.xlsx)", type=["xlsx"])
judge_names = list(available_judges().keys())
selected_judges = st.multiselect("Judge 모델", judge_names, default=judge_names)

if "run_history" not in st.session_state:
    st.session_state.run_history = []

if uploaded is not None:
    df = pd.read_excel(uploaded)

    st.subheader("입력 데이터")
    st.write(f"rows: {len(df)}")
    st.write(f"columns: {list(df.columns)}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"필수 컬럼 누락: {missing}")
        st.stop()

    # 고정 4컬럼만 사용
    df = df[REQUIRED_COLUMNS].copy()
    st.dataframe(df.head(10), use_container_width=True)

    if st.button("평가 실행", type="primary"):
        try:
            validate_input(df)
            result_df, summary_df, evaluated_at = evaluate_dataframe(df, selected_judges)

            run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
            summary_df["run_id"] = run_id
            st.session_state.run_history.extend(summary_df.to_dict(orient="records"))

            st.subheader("모델별 정확도")
            st.dataframe(
                summary_df[["run_id", "judge_model", "accuracy_pct", "pass_rate_pct", "avg_score", "rows", "evaluated_at"]],
                use_container_width=True,
            )

            st.subheader("행별 결과")
            show_cols = ["question", "user_review", "evaluated_at"]
            for name in selected_judges:
                show_cols.extend([f"{name}_result", f"{name}_score", f"{name}_match"])
            st.dataframe(result_df[show_cols], use_container_width=True, height=420)

            out = BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                result_df.to_excel(writer, index=False, sheet_name="results")
                summary_df.to_excel(writer, index=False, sheet_name="summary")
            out.seek(0)

            st.download_button(
                label="결과 엑셀 다운로드",
                data=out,
                file_name=f"judge_results_{evaluated_at.replace(':', '').replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

if st.session_state.run_history:
    st.subheader("회차 비교")
    history_df = pd.DataFrame(st.session_state.run_history)
    st.dataframe(
        history_df[["run_id", "judge_model", "accuracy_pct", "pass_rate_pct", "avg_score", "rows", "evaluated_at"]],
        use_container_width=True,
    )
