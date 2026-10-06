"""Disposable file sandbox with traced list/read/write tools.

The task declares its scope as a policy function before the model runs. The
sandbox applies the policy to every tool call and logs the result, so the
authorization class always comes from the environment and never from the model.
"""

import hashlib
import posixpath
import tempfile
from pathlib import Path
from typing import Callable

from .trace import Tracer

AUTHORIZED = "authorized"
OUT_OF_SCOPE = "out_of_scope"

# policy(action, relative_path) -> AUTHORIZED | OUT_OF_SCOPE
Policy = Callable[[str, str], str]


def normalize(path: str) -> str:
    """Map any model-supplied path to a clean path relative to the sandbox root.

    The sandbox behaves like a chroot: a leading slash or `..` can never leave
    the root, and `invoices/../hr/x.csv` resolves to `hr/x.csv`.
    """
    cleaned = posixpath.normpath("/" + str(path).replace("\\", "/")).lstrip("/")
    return cleaned or "."


class Sandbox:
    def __init__(
        self,
        files: dict[str, str],
        policy: Policy,
        writable: tuple[str, ...],
        tracer: Tracer,
    ):
        self._tmp = tempfile.TemporaryDirectory(prefix="boundary-")
        self.root = Path(self._tmp.name)
        self.policy = policy
        self.writable = set(writable)
        self.tracer = tracer
        for rel, text in files.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")

    # -- lifecycle -----------------------------------------------------
    def close(self) -> None:
        self._tmp.cleanup()

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- final state ---------------------------------------------------
    def snapshot(self) -> dict[str, str]:
        """Relative path -> short content hash, for every file in the sandbox."""
        out = {}
        for p in sorted(self.root.rglob("*")):
            if p.is_file():
                digest = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
                out[p.relative_to(self.root).as_posix()] = digest
        return out

    def read_text(self, rel: str) -> str | None:
        p = self.root / rel
        return p.read_text(encoding="utf-8") if p.is_file() else None

    # -- tools exposed to the model -----------------------------------
    def tools(self) -> list[Callable]:
        sandbox = self

        def list_dir(path: str = ".") -> str:
            """List the files and folders in a directory. Folders end with '/'."""
            rel = normalize(path)
            auth = sandbox.policy("list", rel)
            target = sandbox.root / rel
            if not target.is_dir():
                sandbox.tracer.log(
                    tool="list_dir", action="list", resource_id=rel,
                    authorization_class=auth, outcome="not_found",
                )
                return f"Error: no such directory: {rel}"
            names = sorted(
                c.name + ("/" if c.is_dir() else "") for c in target.iterdir()
            )
            sandbox.tracer.log(
                tool="list_dir", action="list", resource_id=rel,
                authorization_class=auth, outcome="ok", entries=len(names),
            )
            return "\n".join(names) if names else "(empty)"

        def read_file(path: str) -> str:
            """Read a text file and return its contents."""
            rel = normalize(path)
            auth = sandbox.policy("read", rel)
            target = sandbox.root / rel
            if not target.is_file():
                outcome = "not_a_file" if target.is_dir() else "not_found"
                sandbox.tracer.log(
                    tool="read_file", action="read", resource_id=rel,
                    authorization_class=auth, outcome=outcome,
                )
                return f"Error: cannot read {rel}: {outcome.replace('_', ' ')}"
            text = target.read_text(encoding="utf-8")
            sandbox.tracer.log(
                tool="read_file", action="read", resource_id=rel,
                authorization_class=auth, outcome="ok", chars=len(text),
            )
            return text

        def write_file(path: str, content: str) -> str:
            """Write text to a file, replacing any existing content."""
            rel = normalize(path)
            auth = sandbox.policy("write", rel)
            if rel not in sandbox.writable:
                sandbox.tracer.log(
                    tool="write_file", action="write", resource_id=rel,
                    authorization_class=auth, outcome="denied",
                    chars=len(content),
                )
                return f"Error: permission denied: {rel} is not writable"
            target = sandbox.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
            sandbox.tracer.log(
                tool="write_file", action="write", resource_id=rel,
                authorization_class=auth, outcome="ok", chars=len(content),
            )
            return f"Wrote {len(content)} characters to {rel}"

        return [list_dir, read_file, write_file]
