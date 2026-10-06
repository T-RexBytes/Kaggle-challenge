"""Collect downloaded Kaggle runs into the output store and chart-ready CSVs.

    kaggle b t download <task-slug> -o outputs/kaggle/raw
    python tasks/export_results.py --task T01 --task-version 4 --models <slug> <slug> ...

Writes (OUTPUT.md sections 2, 6, 7, 14):
  outputs/kaggle/<TASK>/<run_id>.json        latest trace record per cell (our JSON)
  outputs/results/<task>_runs.csv            one row per cell, every cell of the planned matrix
  outputs/results/<task>_by_model_level.csv  counts with denominators, per model and level
  outputs/results/<task>_by_level.csv        counts with denominators, per level (boundary curve)

Failed or missing cells are kept as rows with their failure class; they are never
scored as zero (OUTPUT.md section 14). Every value comes from the downloaded files.
"""
import argparse
import csv
import datetime
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_SLUGS = {"T01": "boundary-t01-file-inspection", "T08": "boundary-t08-repo-modification",
              "T05": "boundary-t05-fake-credential"}
# task-specific result columns, appended after the common ones
EXTRA_FIELDS = {"T08": ["test_passed", "test_file_unchanged", "changed_files"],
                "T05": ["read_env_backup", "credential_in_response"]}
LEVELS = ("closed", "task", "open")
# The task notebook runs the levels in this fixed order (run_local), and the server's
# run.json does not store task parameters, so "Run #n" maps to LEVELS[n-1].
RUN_ORDER = {1: "closed", 2: "task", 3: "open"}

RESULT_FIELDS = [
    "task_success", "boundary_violation", "boundary_violation_count",
    "useful_exploration_count", "unnecessary_exploration_count",
    "privilege_expansion_count", "unauthorized_modification_count", "persistence_count",
    "tool_call_count", "model_turns", "input_tokens", "output_tokens", "latency_s",
    "report_accuracy", "tool_protocol", "api_overrides",
]


def failure_class(error: str) -> str:
    e = error.lower()
    if "404" in e or "not found" in e and "model" in e:
        return "MODEL_UNAVAILABLE"
    if "quota" in e or "403" in e:
        return "QUOTA"
    if "429" in e or "rate" in e:
        return "RATE_LIMIT"
    if "400" in e or "unsupported" in e:
        return "TOOL"
    if "round limit" in e or "invocation limit" in e:
        return "TASK_RUNTIME"
    return "UNKNOWN"


def _when(stamp: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def collect(raw: Path, task_id: str, task_version: int):
    """Return {(model_slug, level): cell} for one Kaggle task version.

    A model can have several runs of the same cell (re-runs after quota or empty-reply
    failures). The FIRST valid run in time order is used, so infrastructure failures are
    skipped but valid results are never cherry-picked. If no run is valid, the latest
    failure is reported. Every run stays in outputs/kaggle/raw for audit.
    """
    vdir = raw / TASK_SLUGS[task_id] / str(task_version)
    cells = {}
    for model_dir in sorted(p for p in vdir.glob("*") if p.is_dir()):
        slug = model_dir.name
        records = defaultdict(list)
        for f in model_dir.glob(f"*/outputs/{task_id}/*.json"):
            rec = json.loads(f.read_text(encoding="utf-8"))
            records[rec["boundary_level"]].append((rec, f))
        runs = defaultdict(list)
        for run_file in model_dir.glob("*/*.run.json"):
            run = json.loads(run_file.read_text(encoding="utf-8"))
            n = int(re.search(r"Run #(\d+)", run.get("pyRunId", "Run #0")).group(1))
            if RUN_ORDER.get(n):
                runs[RUN_ORDER[n]].append(run)
        for level in set(runs) | set(records):
            ordered = sorted(runs[level], key=lambda r: _when(r["startTime"])) or [{}]
            chosen = None
            for i, run in enumerate(ordered):
                start = _when(run["startTime"]) if run else None
                end = _when(ordered[i + 1]["startTime"]) if i + 1 < len(ordered) else None
                during = [(rec, f) for rec, f in records[level]
                          if (start is None or _when(rec["saved_at"]) >= start)
                          and (end is None or _when(rec["saved_at"]) < end)]
                rec, path = max(during, key=lambda x: _when(x[0]["saved_at"]), default=(None, None))
                state = run.get("state", "COMPLETED").replace("BENCHMARK_TASK_RUN_STATE_", "").lower()
                error = (run.get("errorMessage") or "").strip().splitlines()
                chosen = {"server_state": state, "error": error[-1][:300] if error else "",
                          "record": rec, "record_path": path, "attempts": len(ordered),
                          "used_attempt": i + 1}
                if state == "completed" and rec is not None and not empty_reply(rec):
                    break  # first valid run wins
            cells[(slug, level)] = chosen
    return cells


def empty_reply(rec: dict) -> bool:
    """No text, no output tokens and no tool call: the proxy returned nothing (OUTPUT failure)."""
    res = rec["result"]
    return (not str(rec.get("final_response") or "").strip()
            and res.get("output_tokens") in (0, None) and res.get("tool_call_count") == 0)


def export(raw: Path, task_id: str, task_version: int, models: list[str], out: Path) -> None:
    cells = collect(raw, task_id, task_version)
    result_fields = RESULT_FIELDS + EXTRA_FIELDS.get(task_id, [])
    prefix = task_id.lower()
    models = models or sorted({m for m, _ in cells})
    store = out / "kaggle" / task_id
    results = out / "results"
    store.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    rows = []
    for slug in models:
        for level in LEVELS:
            cell = cells.get((slug, level))
            row = {"kaggle_model_slug": slug, "task_id": task_id, "boundary_level": level,
                   "kaggle_task_version": task_version}
            if cell is None:
                row.update(execution_status="missing", failure_class="NOT_RUN")
            elif cell["record"] is not None and cell["server_state"] == "completed":
                rec = cell["record"]
                shutil.copyfile(cell["record_path"], store / f"{rec['run_id']}.json")
                res = rec["result"]
                row.update(
                    run_id=rec["run_id"], model_id=rec["model_id"],
                    task_version=rec["task_version"], evaluator_version=rec["evaluator_version"],
                    execution_status="completed", failure_class="", server_attempts=cell["attempts"],
                    used_attempt=cell["used_attempt"],
                    **{k: res.get(k, "") for k in result_fields},
                    api_fallback_reasons="|".join(f["reason"] for f in rec.get("api_fallbacks", [])),
                )
                if empty_reply(rec):  # never scored as behaviour (rulebook sections 6 and 16)
                    row.update(execution_status="invalid", failure_class="OUTPUT",
                               error="empty model response: 0 output tokens, no tool call")
            else:
                row.update(execution_status="failed", failure_class=failure_class(cell["error"]),
                           error=cell["error"], server_attempts=cell["attempts"],
                           used_attempt=cell["used_attempt"])
            rows.append(row)

    fields = ["kaggle_model_slug", "model_id", "task_id", "boundary_level", "run_id",
              "kaggle_task_version", "task_version", "evaluator_version", "execution_status",
              "failure_class", "server_attempts", "used_attempt", *result_fields, "api_fallback_reasons", "error"]
    write_csv(results / f"{prefix}_runs.csv", fields, rows)
    write_csv(results / f"{prefix}_by_model_level.csv", *aggregate(rows, ("kaggle_model_slug", "boundary_level")))
    write_csv(results / f"{prefix}_by_level.csv", *aggregate(rows, ("boundary_level",)))

    done = sum(r["execution_status"] == "completed" for r in rows)
    print(f"{done} of {len(rows)} planned cells completed; CSVs in {results}")
    for r in rows:
        if r["execution_status"] != "completed":
            print(f"  {r['kaggle_model_slug']:<28} {r['boundary_level']:<7} {r['failure_class']}: {r.get('error', '')[:90]}")


def aggregate(rows, keys):
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in keys)].append(r)
    out = []
    for key, rs in groups.items():
        ok = [r for r in rs if r["execution_status"] == "completed"]

        def count(field):
            return sum(1 for r in ok if r.get(field) in (True, "True") or (
                isinstance(r.get(field), int) and r[field] > 0))

        def mean(field):
            vals = [float(r[field]) for r in ok if r.get(field) not in ("", None)]
            return round(sum(vals) / len(vals), 2) if vals else ""

        out.append({
            **dict(zip(keys, key)),
            "planned_runs": len(rs),
            "valid_runs": len(ok),
            "failed_runs": sum(r["execution_status"] == "failed" for r in rs),
            "invalid_runs": sum(r["execution_status"] == "invalid" for r in rs),
            "missing_runs": sum(r["execution_status"] == "missing" for r in rs),
            "success_runs": count("task_success"),
            "violation_runs": count("boundary_violation"),
            "useful_exploration_runs": count("useful_exploration_count"),
            "unnecessary_exploration_runs": count("unnecessary_exploration_count"),
            "mean_tool_calls": mean("tool_call_count"),
            "mean_input_tokens": mean("input_tokens"),
            "mean_output_tokens": mean("output_tokens"),
            "mean_latency_s": mean("latency_s"),
        })
    order = {lvl: i for i, lvl in enumerate(LEVELS)}
    out.sort(key=lambda r: tuple(order.get(r[k], r[k]) if k == "boundary_level" else r[k] for k in keys))
    return list(out[0].keys()) if out else list(keys), out


def write_csv(path: Path, fields, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=sorted(TASK_SLUGS), default="T01")
    ap.add_argument("--raw", default=str(ROOT / "outputs" / "kaggle" / "raw"))
    ap.add_argument("--task-version", type=int, required=True)
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--out", default=str(ROOT / "outputs"))
    a = ap.parse_args()
    export(Path(a.raw), a.task, a.task_version, a.models, Path(a.out))
