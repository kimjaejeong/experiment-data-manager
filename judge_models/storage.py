from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

RUNS_DIR = Path("run_results")


def ensure_runs_dir() -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR


def save_run(
    run_id: str,
    run_name: str,
    source_filename: str,
    judges: list[str],
    evaluated_at: str,
    input_df: pd.DataFrame,
    result_df: pd.DataFrame,
    summary_df: pd.DataFrame,
) -> dict[str, Any]:
    ensure_runs_dir()
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    result_excel_path = run_dir / "result.xlsx"
    summary_csv_path = run_dir / "summary.csv"
    input_csv_path = run_dir / "input.csv"

    with pd.ExcelWriter(result_excel_path, engine="openpyxl") as writer:
        result_df.to_excel(writer, index=False, sheet_name="results")
        summary_df.to_excel(writer, index=False, sheet_name="summary")

    summary_df.to_csv(summary_csv_path, index=False)
    input_df.to_csv(input_csv_path, index=False)

    metadata = {
        "run_id": run_id,
        "run_name": run_name,
        "source_filename": source_filename,
        "judges": judges,
        "rows": int(len(result_df)),
        "evaluated_at": evaluated_at,
        "result_excel_path": str(result_excel_path),
        "summary_csv_path": str(summary_csv_path),
        "input_csv_path": str(input_csv_path),
    }

    (run_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def list_runs() -> list[dict[str, Any]]:
    ensure_runs_dir()
    items: list[dict[str, Any]] = []
    for metadata_path in sorted(RUNS_DIR.glob("*/metadata.json"), reverse=True):
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            items.append(data)
        except Exception:  # noqa: BLE001
            continue
    return items


def load_run(run_id: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    run_dir = RUNS_DIR / run_id
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    result_excel_path = run_dir / "result.xlsx"

    result_df = pd.read_excel(result_excel_path, sheet_name="results")
    summary_df = pd.read_excel(result_excel_path, sheet_name="summary")
    return metadata, result_df, summary_df


def delete_run(run_id: str) -> None:
    run_dir = RUNS_DIR / run_id
    if run_dir.exists() and run_dir.is_dir():
        shutil.rmtree(run_dir)
