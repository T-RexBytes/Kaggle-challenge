"""Run identity and the "latest working JSON" store.

Only a run that finished (execution_status == "completed") is saved. Each cell
(model + task + boundary level + run number) has exactly one file, replaced
atomically, so a failed re-run never destroys the last good record.
"""

import datetime
import json
import os
import re
from pathlib import Path

ENVIRONMENT_VERSION = "1"
EVALUATOR_VERSION = "1"
BOUNDARY_LEVELS = ("closed", "task", "open")


def output_dir() -> Path:
    """Where latest JSONs go.

    BOUNDARY_OUTPUT_DIR wins (tests set it). On Kaggle it is /kaggle/working/outputs.
    Locally it is ./outputs, so run from the repo root.
    """
    if os.environ.get("BOUNDARY_OUTPUT_DIR"):
        return Path(os.environ["BOUNDARY_OUTPUT_DIR"])
    if Path("/kaggle/working").is_dir():
        return Path("/kaggle/working/outputs")
    return Path.cwd() / "outputs"


def model_id_of(llm) -> str:
    return str(getattr(llm, "model", None) or getattr(llm, "name", None) or "unknown")


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", text).strip("-")


def build_run_id(model_id: str, task_id: str, boundary: str, run_number: int = 1) -> str:
    """MODEL-TASK-BOUNDARY-RUN, e.g. gemini-3-flash-preview-T01-TASK-R01."""
    short_model = _slug(model_id.split("/")[-1])
    return f"{short_model}-{task_id}-{boundary.upper()}-R{run_number:02d}"


def save_latest(task_id: str, run_id: str, record: dict) -> Path:
    """Write outputs/<task_id>/<run_id>.json, replacing the previous one."""
    folder = output_dir() / task_id
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / f"{run_id}.json"
    record = {**record, "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    tmp = final.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, final)
    return final
