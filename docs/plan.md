# PLAN.md

## PURPOSE

This document is the project-level research plan for the Kaggle benchmark.

It defines the central research idea, why the benchmark exists, what it tries to prove, how
the task structure supports that goal, how deterministic scoring is made possible, and how a
limited evaluation budget is used.

The detailed definition of each test belongs in `TEST.md`.

This document follows `AGENT.md`. It is self-contained.

## PROJECT CONTEXT

The benchmark is built for the Kaggle Benchmarking Challenge (hosted on DEV).

- Submissions close: 2026-10-11, 23:59 PDT.
- Judging axes (equal weight): Insights Shared, Writing Quality, Creativity in Approach.
- To submit: build a benchmark on Kaggle Benchmarks, run it on real models, publish a DEV
  post tagged `#kagglechallenge` with the Kaggle link.

The project does NOT create many unrelated tasks. It tests ONE capability from many
controlled angles:

> When an LLM is asked to modify a document, can it perform every required edit while
> remembering the instructions, preserving the constraints, and leaving unrelated content
> unchanged?

The benchmark studies **constrained document editing reliability**.

The central concern: an LLM may produce an edit that looks correct locally while the whole
document is wrong globally. For example — a required occurrence is missed; an old value
survives elsewhere; a dependent value is not updated; a change is applied outside its scope;
protected content is altered; a secondary instruction is forgotten; structure is damaged; an
unrequested "improvement" is added; or a historical statement is wrongly modified.

## CORE IDEA

The benchmark treats document editing as a four-part contract:

```text
UNDERSTAND
    |
    v
CHANGE WHAT IS REQUIRED
    |
    v
PRESERVE WHAT MUST REMAIN
    |
    v
PRODUCE A VALID FINAL DOCUMENT
```

A model does NOT earn credit only because the requested edit appears somewhere in its output.
It must satisfy the complete change contract. The benchmark therefore separates:

1. required-change completion;
2. preservation of protected or unrelated content;
3. consistency of dependent content;
4. resistance to unauthorized changes;
5. final document validity.

## THE HEADLINE (what we will report and claim)

Two failures are measured as one pair, because they are opposite poles of the same capability:

```text
UNDER-EDIT  : the model failed to change something that must change.
OVER-EDIT   : the model changed something that must not change.
```

The headline result is the per-model position on both poles at once:

> Current LLMs both under-edit and over-edit. They cannot hold a change-and-preserve contract
> at the same time.

The headline chart is **under-edit rate vs over-edit rate, per model, with 95% intervals**.
The single most memorable finding we aim to show: **where a small deterministic rule beats
every frontier model** (see BASELINES).

## RESEARCH QUESTION

Primary:

> Can current LLMs reliably perform constrained document modifications when success requires
> both remembering what to change and remembering what not to change?

Secondary:

1. Does performance fall as the number of constraints rises?
2. Does performance fall when a change has multiple document-level consequences?
3. Are models more likely to over-edit or under-edit?
4. Can models tell current information from historical or exceptional information?
5. Can models preserve structure and formatting while changing content?
6. Do deterministic rules beat LLMs on explicit cases?
7. Does a hybrid (rule + LLM) approach improve reliability?
8. Does model size or capability predict constrained-editing reliability?

Final conclusions MUST be based on measured results.

## HYPOTHESIS

> LLMs will often perform the requested local edit correctly, but reliability will fall when
> the edit requires document-wide reasoning, preservation of unrelated information,
> interpretation of scope, or several constraints at once.

This hypothesis is testable and MAY be contradicted by the results. The project MUST NOT be
designed to force the hypothesis to be true.

## WHY THIS MATTERS

Ordinary editing evaluation asks whether the final wording looks acceptable. That is not
enough. A document can read fluently and still be wrong: a stale value remains; a historical
statement was destroyed; a protected value changed; a dependent value is now inconsistent; an
unauthorized change was added. The benchmark emphasizes **global correctness under a local
edit request**:

> Can we trust an LLM to change exactly what we asked, without forgetting the rest of the
> document contract?

## WHY THIS BEATS THE FIELD (grounded bragging material)

The Kaggle Benchmarking Challenge field (reviewed) rewards posts that separate two abilities
that look like one, and punishes weak statistics and self-measuring harnesses. This project is
positioned to win on all three judging axes. Each claim below is tied to a concrete design
choice, so it can be stated without overclaiming.

- FIRST to score the change-and-preserve contract **jointly**, with under-edit and over-edit as
  one paired metric. Most posts score a single side.
- Statistics the field lacks: cases are **generated programmatically**, so sample sizes are
  large by construction, and every rate carries a **95% Wilson interval** over **>= 3 runs**.
  The sharpest criticism aimed at the most popular posts was tiny samples and single runs.
- **Anchor-based deterministic scoring** (see SCORING MODEL) means the number is about the
  model, not the harness. Several top posts shipped a wrong number first because their plumbing
  failed. Ours cannot fuzzy-match its way to a false result.
- **Rule and hybrid baselines** answer a question no top post answers: where is an LLM actually
  necessary, and where does a 20-line deterministic rule win? This is the decision rule judges
  reward.
- **No model-as-judge** anywhere in the primary metric.

## SCORING MODEL (the design decision everything depends on)

Free-form whole-document diffing is rejected: it produces false over-edit flags on harmless
reflow, whitespace, or quote style. Instead, scoring is **anchor-based**. Each generated case
ships machine-checkable anchors, and the scorer inspects ONLY those anchors:

```text
REQUIRED   : exact old -> new spans that MUST change.
PROTECTED  : spans that MUST match byte-for-byte after FROZEN NORMALIZATION.
DEPENDENT  : values the scorer computes independently and MUST find updated.
EDITABLE   : the regions the model is allowed to touch; any change OUTSIDE these,
             beyond normalization tolerance, is an over-edit.
```

FROZEN NORMALIZATION (defined once, frozen before scoring): trailing newline, surrounding
whitespace, and quote-style differences are ignored; everything else is significant. The exact
rule is specified in `TRD.md` and MUST NOT change after the final run.

This converts "preserve everything else" from an impossible fuzzy judgement into a finite,
deterministic check. Required-change completion, preservation, dependency, scope, and validity
all reduce to anchor checks. See `TEST.md` COMMON SUCCESS MODEL.

## BENCHMARK DESIGN PRINCIPLE

One underlying capability, many controlled tests. Each test varies one or more difficulty
dimensions while the central editing problem stays intact. The 17 tests are grouped:

- 7 HIGH; 6 MEDIUM; 4 EASY.

Tier controls execution priority and evaluation depth. EASY tasks are controls, not
scientifically unimportant.

## SINGLE-ENGINE REQUIREMENT (what makes 17 tasks feasible)

The 17 tasks MUST NOT be 17 bespoke code paths. They MUST be configurations over:

- ONE case generator (deterministic, seeded, template-driven);
- ONE scorer library (the anchor checks above, shared by every task).

Difficulty dimensions D1–D14 (see `TEST.md`) are generator parameters. Adding or changing a
task is a config change, not new scoring code. This keeps metrics identical across tasks
(CONSISTENCY RULE) and makes 17 tasks achievable in the available time. A new scorer is written
only when a task introduces a genuinely new, distinct failure check.

## WHY 17 TASKS

Seventeen tasks give enough variation across: local vs global editing; explicit vs implicit
dependencies; single vs multiple constraints; prose vs structured representations; current vs
historical information; direct targets vs decoys; content vs structural preservation. The suite
should reveal whether a model has a general constrained-editing weakness or only fails on
specific dimensions. Exact task definitions and scoring rules are in `TEST.md`.

## EVALUATION STRATEGY

The execution budget is limited, so evaluation MUST be staged.

### Stage 1 — Smoke Test
Run a small number of cases for all 17 tasks. Confirm each task is valid, the prompt is
understandable, and the scorer behaves. Detect trivial or impossible tasks.

### Stage 2 — Screening
Run a small model sample across all 17 tasks. Identify tasks with useful discrimination, detect
redundancy, estimate token and execution cost, verify feasibility. A task MUST NOT be removed
only because one model does well on it.

### Stage 3 — Main Evaluation
Prioritize the 7 HIGH tasks, then the 6 MEDIUM tasks. Use the 4 EASY tasks as controls and
low-cost baselines.

### Stage 4 — Deep Evaluation
Use remaining budget for more cases, repeated runs (to tighten intervals), strongest-model
comparisons, tasks with large model disagreement, and the most informative failure modes.
Maximize **information gained per model call**, not raw case count.

## STATISTICS

- Every reported rate MUST carry a 95% Wilson interval.
- Every model MUST be run >= 3 times per task; the report MUST show the run spread.
- Small gaps inside the run spread MUST be treated as ties, not rankings.
- Report under-edit and over-edit separately, and the joint (both-correct) case success.

## BASELINES

Compare LLM editing against simple deterministic strategies where the task permits:

- no-change baseline;
- exact replacement baseline;
- structured rule baseline;
- stronger rule / normalization baseline;
- hybrid rule + LLM baseline.

The purpose is not to make rules artificially strong. It is to find where LLM reasoning is
actually necessary, and to produce a model-selection decision rule for the write-up.

## MVP AND DROP ORDER (deadline protection)

A valid, field-beating entry does NOT require all 17 tasks. Build in this order; drop from the
bottom under time pressure; never drop Tier 0.

```text
TIER 0 (MUST, = a valid submittable entry):
  - the single engine (generator + anchor scorer) working;
  - THREE tasks covering the triangle: H01 (change), H04 (preserve), H07 (over-edit);
  - >= 100 cases per task, >= 3 runs, Wilson intervals, scorer validated;
  - one Kaggle benchmark + one DEV post with tag and link.

TIER 1 (SHOULD, = the winning entry):
  - remaining HIGH tasks, then MEDIUM tasks;
  - rule + hybrid baselines;
  - the under-edit vs over-edit headline chart;
  - the model-selection decision rule.

TIER 2 (MAY, = polish):
  - the 4 EASY controls; full error taxonomy breakdown; extra deep repeats.

drop first  -> Tier 2
then        -> MEDIUM, then non-core HIGH tasks
never drop  -> Tier 0
```

## CONSTRAINTS

### MUST
- Keep all tasks connected to constrained document editing.
- Use reproducible, seeded cases.
- Use anchor-based deterministic scoring (SCORING MODEL).
- Keep model conditions equivalent.
- Report task-level failures, and under-edit vs over-edit separately.
- Carry a 95% Wilson interval on every reported rate.
- Validate scorers before large evaluation.
- Freeze normalization, task definitions, and the generator before the final run.

### MUST NOT
- Create unrelated tasks merely to reach 17.
- Treat fluent output as proof of correctness.
- Use whole-document fuzzy diffing as the scorer.
- Use model-as-judge as the primary scorer.
- Claim real-world accuracy from synthetic performance.
- Spend most of the budget before task validity is established.
- Change the research question after seeing convenient results.

### SHOULD
- Use fictional or controlled documents where exact ground truth is practical.
- Use disjoint development and test cases.
- Track required changes and forbidden changes separately.
- Report both under-editing and over-editing.

## DEPENDENCIES

```text
PLAN.md          -> research direction (this document).
TEST.md          -> the complete 17-task experimental specification.
TRD.md           -> technical implementation (engine, anchor scorer, Kaggle build, commands).
MVP.md           -> minimum implementation for submission (mirrors MVP AND DROP ORDER above).
PROCESS_FLOW.md  -> execution order.
prompt.md        -> instructions for the implementation agent.
```

NOTE: any project document that still describes a different benchmark MUST be rewritten to this
plan before the agent runs, or it violates the CONSISTENCY RULE in `AGENT.md`.

## CURRENT STATE

- Core idea: DECIDED (constrained document editing reliability).
- Headline + scoring model: DECIDED (paired under/over-edit; anchor-based scoring).
- 17-task structure: DECIDED.
- Single-engine requirement: DECIDED.
- Task details: DEFINED in `TEST.md`.
- Exact scorer implementation: TO BUILD from SCORING MODEL (no longer unresolved in principle).
- Frozen normalization rule: TO FREEZE in `TRD.md`.
- Exact model lineup: UNKNOWN until Kaggle availability and quotas are verified.
- Exact case counts: UNRESOLVED until smoke-test cost is measured.

## NEXT ACTIONS

1. Freeze `TEST.md`.
2. Build the single engine: seeded generator + shared anchor scorer.
3. Define and freeze the normalization rule in `TRD.md`.
4. Convert the 17 task definitions into generator configs.
5. Build the smallest valid smoke-test suite; validate the scorer against known-good and
   known-bad outputs.
6. Measure execution cost; record the real model lineup.
7. Run staged model evaluation (Tier 0 first).
8. Analyze failure patterns.
9. Update final benchmark documentation only after measured results exist.
