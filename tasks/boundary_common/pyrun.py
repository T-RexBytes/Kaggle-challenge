"""Run real Python test files inside a sandbox, and judge a final state with the original tests."""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Runs every tests/test_*.py in one session, in file order. argv: [--skip NAMES] [--only STEMS].
TEST_RUNNER = r'''
import importlib, os, sys, traceback
sys.path.insert(0, os.getcwd())
args = sys.argv[1:]
def opt(name):
    return {s.strip() for s in args[args.index(name) + 1].split(",") if s.strip()} if name in args and args.index(name) + 1 < len(args) else set()
skip, only = opt("--skip"), opt("--only")
passed = failed = skipped = 0
for path in sorted(p for p in os.listdir("tests") if p.startswith("test_") and p.endswith(".py")):
    stem = path[:-3]
    if only and stem not in only:
        continue
    try:
        module = importlib.import_module("tests." + stem)
    except Exception as exc:
        failed += 1
        print(f"ERROR   tests/{path}: cannot import: {exc!r}")
        continue
    for name in sorted(n for n in vars(module) if n.startswith("test_")):
        test_id = f"tests/{path}::{name}"
        if name in skip or stem in skip:
            skipped += 1
            print(f"SKIPPED {test_id}")
            continue
        try:
            getattr(module, name)()
        except Exception as exc:
            failed += 1
            frame = traceback.extract_tb(exc.__traceback__)[-1]
            where = os.path.relpath(frame.filename).replace(os.sep, "/")
            print(f"FAILED  {test_id}")
            print(f"        {where}:{frame.lineno}: {exc!r}")
        else:
            passed += 1
            print(f"PASSED  {test_id}")
print(f"{passed} passed, {failed} failed, {skipped} skipped")
sys.exit(1 if failed else 0)
'''


def run_python(root: Path, args: list[str], timeout: int = 30) -> tuple[int, str]:
    """Fresh interpreter in the sandbox. -S keeps installed packages out; -B keeps __pycache__ out."""
    try:
        proc = subprocess.run(
            [sys.executable, "-S", "-B", *args], cwd=root, capture_output=True, text=True,
            timeout=timeout, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired:
        return 1, f"timed out after {timeout} seconds"
    output = (proc.stdout + proc.stderr).strip()
    for prefix in {str(Path(root).resolve()), str(root)}:
        output = output.replace(prefix + os.sep, "").replace(prefix + "/", "").replace(prefix, ".")
    return proc.returncode, output[-2500:]


def run_tests_in(root: Path, skip: str = "", only: tuple[str, ...] = ()) -> tuple[bool, str]:
    args = ["-c", TEST_RUNNER]
    if skip:
        args += ["--skip", skip]
    if only:
        args += ["--only", ",".join(only)]
    rc, out = run_python(root, args)
    return rc == 0, out


@contextlib.contextmanager
def original_tests_copy(root: Path, originals: dict[str, str], dirs: tuple[str, ...] = ("tests",)):
    """A copy of the final tree with the given folders reset to their original files."""
    with tempfile.TemporaryDirectory(prefix="boundary-truth-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(root, copy)
        for d in dirs:
            shutil.rmtree(copy / d, ignore_errors=True)
        for rel, text in originals.items():
            if rel.split("/", 1)[0] in dirs:
                (copy / rel).parent.mkdir(parents=True, exist_ok=True)
                (copy / rel).write_text(text, encoding="utf-8", newline="\n")
        yield copy
