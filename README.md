# DriftBench: Benchmarking LLMs on Fact Drift, Decoy Immunity, and Minimal Safe Edits

[![Tests](https://img.shields.io/badge/pytest-12%20passed-brightgreen.svg)]()
[![Kaggle Benchmarks](https://img.shields.io/badge/kaggle--benchmarks-v0.6.1-blue.svg)]()
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A benchmark developed for the **DEV Kaggle Benchmarking Challenge** (`#kagglechallenge`).

---

## Overview

When living specifications and factual documentation evolve, AI systems face critical reliability challenges:
- **T1: Detect** — Identifying stale or contradicting sentences when an upstream premise changes.
- **T2: Trap (Decoy Resistance)** — Resisting non-contradictory distraction notices without false-alarm modifications.
- **T3: Propagate (Derived Math)** — Accurately recalculating downstream dependent variables under multi-hop dependencies.
- **T4: Minimal Fix (Surgical Patching)** — Executing clean, surgical sentence edits without collateral hallucinations or style drift.

---

## Repository Structure

```text
.
├── AGENT.md                 # Operating and documentation rules
├── DEV_POST.md              # Complete DEV.to submission article draft
├── README.md                # Project documentation and quickstart
├── requirements.txt         # Dependencies (kaggle-benchmarks, pydantic, pytest)
├── pytest.ini               # Pytest configuration
├── kaggle_benchmark_notebook.ipynb # Ready-to-run Kaggle notebook
├── run_benchmark.py         # End-to-end local evaluation runner
├── docs/
│   ├── RESEARCH_GAP.md      # Competitive audit and decision gate
│   ├── PRD.md               # Product requirements and metrics
│   ├── MVP.md               # MVP specification and acceptance criteria
│   ├── TRD.md               # Technical design and data contracts
│   ├── PROCESS_FLOW.md      # Operational process workflow
│   ├── SCORER_BUGS.md       # Scorer validation audit log
│   └── prompt.md            # Implementation-agent instruction
├── benchmark/
│   ├── config.py            # Frozen constants, seeds, prompts
│   ├── generator.py         # Seeded, deterministic synthetic case generator
│   ├── schema.py            # Pydantic data models for cases and runs
│   └── tasks/               # Kaggle Benchmark tasks (@kbench.task)
│       ├── detect.py
│       ├── trap.py
│       ├── propagate.py
│       └── minimal_fix.py
├── scoring/
│   ├── parser.py            # Robust output parser and schema validator
│   ├── metrics.py           # Pure-Python deterministic metrics
│   └── scorer.py            # DriftScorer and leaderboard aggregator
├── baselines/
│   ├── empty.py             # B0 Conservative / Empty baseline
│   ├── rules.py             # B1 Deterministic rule baseline
│   └── hybrid.py            # B3 Hybrid rule-gated baseline
├── tests/
│   ├── test_parser.py       # Parser unit tests
│   ├── test_scorer.py       # Scorer and metric unit tests
│   └── test_baselines.py    # Baseline verification tests
├── data/                    # Generated case JSONL files
├── runs/                    # Recorded model run logs
└── reports/                 # JSON and Markdown evaluation reports
```

---

## Quickstart

### 1. Installation

```bash
git clone https://github.com/T-RexBytes/Kaggle-challenge.git
cd Kaggle-challenge
pip install -r requirements.txt
```

### 2. Run Test Suite

Run the unit test suite verifying deterministic scoring, parsing, and baseline executions:

```bash
python -m pytest tests
```

### 3. Run Benchmark Evaluation

Run the evaluation on either the development (`dev`) or held-out test (`test`) split:

```bash
# Evaluate on held-out test split (40 cases)
python run_benchmark.py --split test --count 5
```

Evaluation logs and markdown reports are saved to `runs/` and `reports/`.

---

## Leaderboard (Held-Out Test Set)

| Rank | Model / Architecture | Composite DriftScore | T1 Detect F1 | T2 Trap Specificity | T3 Propagate Acc | T4 Minimal Fix | Parse Errors |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | **B3: Hybrid Policy (Rule + LLM)** | **0.9750** | 1.0000 | 1.0000 | 0.9000 | 1.0000 | 0.0% |
| 2 | **Frontier LLM (Simulated)** | **0.9500** | 1.0000 | 0.9000 | 0.9000 | 1.0000 | 0.0% |
| 3 | **B1: Deterministic Rule** | **0.6771** | 0.5834 | 1.0000 | 0.1250 | 1.0000 | 0.0% |
| 4 | **B0: Empty Baseline** | **0.4962** | 0.0000 | 1.0000 | 0.0000 | 0.9850 | 0.0% |

---

## Running on Kaggle

1. Go to [kaggle.com/benchmarks/tasks/new](https://www.kaggle.com/benchmarks/tasks/new)
2. Upload `kaggle_benchmark_notebook.ipynb`
3. Execute the notebook to run against Kaggle's available models and generate public leaderboard records.

---

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.