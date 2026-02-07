from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from judge_models import (
    REQUIRED_COLUMNS,
    available_judges,
    delete_run,
    evaluate_dataframe,
    list_runs,
    load_run,
    save_run,
    validate_input,
)


st.set_page_config(page_title="Simple Judge Lab", layout="wide")
st.title("Judge 실험 비교")
st.caption("업로드 → 평가 실행 → 결과 저장 → 결과 확인")

tab_eval, tab_result = st.tabs(["평가 실행", "결과 확인"])

with tab_eval:
    uploaded = st.file_uploader("엑셀 업로드 (.xlsx)", type=["xlsx"])
    judge_names = list(available_judges().keys())
    selected_judges = st.multiselect("Judge 모델", judge_names, default=judge_names)
    run_name = st.text_input("실험 이름", value=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    if uploaded is not None:
        raw_df = pd.read_excel(uploaded)
        missing = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]

        st.write(f"rows: {len(raw_df)}")
        st.write(f"columns: {list(raw_df.columns)}")

        if missing:
            st.error(f"필수 컬럼 누락: {missing}")
        else:
            input_df = raw_df[REQUIRED_COLUMNS].copy()
            st.dataframe(input_df.head(10), use_container_width=True)

            if st.button("평가 실행 및 저장", type="primary"):
                try:
                    validate_input(input_df)
                    result_df, summary_df, evaluated_at = evaluate_dataframe(input_df, selected_judges)

                    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
                    summary_df["run_id"] = run_id

                    metadata = save_run(
                        run_id=run_id,
                        run_name=run_name,
                        source_filename=uploaded.name,
                        judges=selected_judges,
                        evaluated_at=evaluated_at,
                        input_df=input_df,
                        result_df=result_df,
                        summary_df=summary_df,
                    )

                    st.success(f"저장 완료: {metadata['run_id']}")
                    st.subheader("모델별 정확도")
                    st.dataframe(
                        summary_df[["run_id", "judge_model", "accuracy_pct", "pass_rate_pct", "avg_score", "rows", "evaluated_at"]],
                        use_container_width=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

with tab_result:
    st.subheader("저장된 결과")
    runs = list_runs()

    if not runs:
        st.info("저장된 실험 결과가 없습니다.")
    else:
        runs_df = pd.DataFrame(runs)

        c1, c2 = st.columns([3, 2])
        run_options = [f"{r['run_id']} | {r['run_name']} | {r['evaluated_at']}" for r in runs]
        selected_label = c1.selectbox("실험 선택", run_options)
        selected_run_id = selected_label.split(" | ")[0]

        judge_filter = c2.selectbox("Judge 필터", ["all"] + list(available_judges().keys()))

        st.dataframe(runs_df[["run_id", "run_name", "source_filename", "rows", "evaluated_at"]], use_container_width=True)

        metadata, result_df, summary_df = load_run(selected_run_id)

        if judge_filter != "all":
            summary_df = summary_df[summary_df["judge_model"] == judge_filter]
            keep_cols = ["question", "llm_answer", "retrieved_contexts", "user_review", "evaluated_at"]
            keep_cols += [f"{judge_filter}_result", f"{judge_filter}_score", f"{judge_filter}_match"]
            existing_cols = [c for c in keep_cols if c in result_df.columns]
            result_df = result_df[existing_cols]

        st.subheader("요약")
        st.dataframe(summary_df, use_container_width=True)

        st.subheader("행별 결과")
        st.dataframe(result_df, use_container_width=True, height=420)

        with open(metadata["result_excel_path"], "rb") as f:
            st.download_button(
                "저장된 결과 엑셀 다운로드",
                data=f.read(),
                file_name=f"{selected_run_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        if st.button("선택 실험 삭제", type="secondary"):
            delete_run(selected_run_id)
            st.success(f"삭제 완료: {selected_run_id}")
            st.rerun()
