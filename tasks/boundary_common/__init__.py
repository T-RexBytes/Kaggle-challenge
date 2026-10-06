"""Shared harness for BOUNDARY tasks: trace, sandbox, run records."""

from .record import (
    EVALUATOR_VERSION,
    ENVIRONMENT_VERSION,
    BOUNDARY_LEVELS,
    build_run_id,
    output_dir,
    save_latest,
    model_id_of,
)
from .models import ROSTER, failure_class, run_local
from .sandbox import AUTHORIZED, OUT_OF_SCOPE, Sandbox
from .trace import Tracer
from .transport import prompt_with_tools, run_with_fallbacks
from .usage import meter_usage

__all__ = [
    "AUTHORIZED",
    "BOUNDARY_LEVELS",
    "ENVIRONMENT_VERSION",
    "EVALUATOR_VERSION",
    "OUT_OF_SCOPE",
    "ROSTER",
    "Sandbox",
    "Tracer",
    "build_run_id",
    "failure_class",
    "meter_usage",
    "model_id_of",
    "output_dir",
    "prompt_with_tools",
    "run_local",
    "run_with_fallbacks",
    "save_latest",
]
