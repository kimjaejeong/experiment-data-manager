# Simple Judge Lab

고정 컬럼 엑셀(`question`, `llm_answer`, `retrieved_contexts`, `user_review`)을 업로드해서
여러 Judge 모델의 행별 평가 결과(True/False)와 정확도(대비: `user_review`)를 비교하는 심플한 Streamlit 앱입니다.

## 구조

```text
judge_models/
  base.py
  models.py
  runner.py
streamlit_app/
  app.py
scripts/
  generate_sample_excel.py
sample_data/
  supply_chain_judge_sample.xlsx
```

## 1) 샘플 엑셀 생성

```bash
python scripts/generate_sample_excel.py
```

생성 파일: `sample_data/supply_chain_judge_sample.xlsx`

- 컬럼은 정확히 4개만 사용
- `question`
- `llm_answer`
- `retrieved_contexts`
- `user_review`

## 2) 앱 실행

```bash
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

## 3) 사용 방법

1. 엑셀 업로드
2. Judge 모델 선택(복수 선택 가능)
3. `평가 실행` 클릭
4. 모델별 정확도 확인 후 자동 저장
5. `결과 확인` 탭에서 회차별 조회/비교/다운로드/삭제

다운로드 엑셀에는 다음이 포함됩니다.
- 원본 4컬럼
- `evaluated_at` (평가 시각)
- 모델별 `*_result`, `*_score`, `*_match`
- `summary` 시트(모델별 accuracy/pass rate)

저장 위치:
- `run_results/<run_id>/result.xlsx`
- `run_results/<run_id>/metadata.json`

## Judge 모델 (샘플 3개)

- `strict_rule_judge`: 질문별 핵심 키워드/금지 키워드 기반
- `ragas_style_judge`: faithfulness + answer_relevancy 유사 지표 기반
- `lenient_prompt_judge`: 완화된 점수 기준(문맥 지지 + 과장표현 패널티)
- `openai_gpt_judge`: OpenAI GPT 호출 기반 판정(옵션)

Judge 모델은 `judge_models/models.py`에서 쉽게 추가할 수 있습니다.

## OpenAI GPT Judge 사용

1. 앱 실행
2. 좌측 사이드바에서 `OpenAI GPT Judge 사용` 체크
3. `OPENAI_API_KEY` 입력
4. 모델명 입력(예: `gpt-4o-mini`)
5. 평가 실행 시 `openai_gpt_judge` 선택

주의:
- OpenAI Judge는 네트워크와 API 키가 필요합니다.
- 호출 실패 시 해당 실험 실행에서 오류 메시지가 표시됩니다.
