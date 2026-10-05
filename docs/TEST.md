# TEST.md

## PURPOSE

This document defines the experimental test suite for the benchmark. It explains what is
tested, what each of the 17 tasks measures, why each exists, what a successful model must do,
and how the tasks differ.

This document is subordinate to `PLAN.md`. `PLAN.md` defines the project idea, the headline,
the scoring model, and the research strategy. `TEST.md` defines the actual test structure.
Technical implementation details belong in `TRD.md`.

This document follows `AGENT.md`. It is self-contained.

## TESTING OBJECTIVE

The benchmark tests one capability:

> Can an LLM make the required document changes while remembering and preserving everything
> that should remain unchanged?

Every task MUST test a meaningful part of this capability. The benchmark measures two opposing
requirements at once:

```text
REQUIRED CHANGE
      +
REQUIRED PRESERVATION
      =
CONSTRAINED EDITING SUCCESS
```

A model can fail in two major ways, and the suite MUST capture both:

```text
UNDER-EDIT : the model failed to make something that should change.
OVER-EDIT  : the model changed something that should not change.
```

These two poles are the paired headline metric defined in `PLAN.md`.

## OUTPUT AND SCORING CONTRACT (applies to every task)

This section makes deterministic scoring possible. It is the operational form of the SCORING
MODEL in `PLAN.md`. Every task obeys it unless the task explicitly overrides it.

### Model output format
The model returns the **full edited document**, and nothing else outside the defined output
markers. The model is NOT asked to produce a diff. Scoring reads anchors, not a free diff.

### Case anchors (ground truth shipped with every case)
Each generated case carries machine-checkable anchors:

```text
REQUIRED[]  : each is { locator, old_value, new_value }. MUST become new_value.
PROTECTED[] : each is { locator, exact_value }. MUST equal exact_value after NORMALIZATION.
DEPENDENT[] : each is { locator, computed_expected }. Scorer computes the expected value
              independently and MUST find it present.
EDITABLE[]  : the regions the model may touch. Any change OUTSIDE these regions, beyond
              NORMALIZATION tolerance, is an OVER-EDIT.
```

`locator` is a deterministic address (e.g., anchor id, section + field key, or table
row/column key) produced by the generator — never a fuzzy text search at scoring time.

### NORMALIZATION (frozen; exact rule lives in `TRD.md`)
When comparing PROTECTED and out-of-region text, ignore: trailing newline, leading/trailing
whitespace, and quote-style differences. Everything else is significant. The rule is frozen
before the final run and MUST NOT change afterward.

### Malformed output
If the model output cannot be parsed into a document (missing markers, truncated), the case is
recorded as `captured = false` and is DROPPED from all rates — it is never scored as a wrong
edit. A model whose run is incomplete receives NO task score, not a zero.

## COMMON TASK CONTRACT

Unless a task explicitly requires a different format, each task case contains:

1. a document or document-like input;
2. a set of editing instructions;
3. explicit or implicit preservation constraints, expressed as PROTECTED / EDITABLE anchors;
4. a required final output (the full edited document);
5. deterministic ground truth (the anchors above);
6. a deterministic scorer (the shared anchor scorer).

Each case MUST also carry machine-readable metadata listing the difficulty dimensions present
(see CROSS-TASK DIFFICULTY DIMENSIONS).

## COMMON SUCCESS MODEL

A case succeeds only when the final result satisfies the complete case contract, checked in
this fixed order:

```text
Required changes correct?   (all REQUIRED anchors == new_value)
        |
        +-- NO --> UNDER-EDIT FAILURE
        |
       YES
        |
Protected/unrelated content preserved?  (all PROTECTED == exact; no out-of-region change)
        |
        +-- NO --> OVER-EDIT FAILURE
        |
       YES
        |
Dependencies and scope consistent?  (all DEPENDENT == computed_expected)
        |
        +-- NO --> CONSISTENCY FAILURE
        |
       YES
        |
Final output valid?  (parses; structural contract intact)
        |
       YES
        |
     SUCCESS
```

Metric names and formulas are frozen in `TRD.md` before the final test set is scored and MUST
be identical across tasks.

## TASK TIERS

17 tasks. Tier controls evaluation effort and priority (see `PLAN.md` EVALUATION STRATEGY and
MVP AND DROP ORDER).

### HIGH — 7
Most demanding. Strong combinations of context, dependencies, scope, or preservation load.

### MEDIUM — 6
Important failure modes at moderate complexity.

### EASY — 4
Basic behavior and inexpensive controls.

Tier MAY be refined after smoke testing if the original classification is wrong, but the
research purpose of a task MUST NOT change.

### Tier-0 core (from `PLAN.md` MVP)
H01 (change), H04 (preserve), H07 (over-edit) are the minimum submittable triangle. They MUST
be built and validated first.

# HIGH TASKS

## H01 — Multi-Location Consistency
### Test
A requested fact change appears in multiple relevant locations. The model must update every
location that should change and leave look-alike or unrelated occurrences unchanged.
### What it tests
Global consistency across repeated mentions.
### Failure exposed
The obvious local edit is made; another required occurrence is forgotten (under-edit), or a
look-alike is changed (over-edit).
### Anchors
REQUIRED = every true occurrence; PROTECTED = the look-alikes.
### Strategic value
Direct test of whether the model treats the document as one connected artifact.

## H02 — Dependency Propagation
### Test
A source value changes and other values depend on it (totals, dates, percentages, converted
units, derived limits). The model must recompute and update the dependents.
### What it tests
Change-impact reasoning.
### Failure exposed
The source is corrected but dependents stay stale or become inconsistent.
### Anchors
REQUIRED = the source; DEPENDENT = each derived value, computed by the scorer.
### Strategic value
Separates semantic reasoning from simple text replacement.

## H03 — Conditional Scope
### Test
A value must change only under a specific condition (one tier, region, product, environment,
section, or date range).
### What it tests
Scope-aware editing.
### Failure exposed
The change is applied too broadly (over-edit) or missed in the in-scope location (under-edit).
### Anchors
REQUIRED = in-scope occurrences; PROTECTED = same value where out of scope.
### Strategic value
Tests whether the model understands WHERE an instruction applies, not only the new value.

## H04 — Preserve-What-Must-Not-Change
### Test
The request names explicit protected content. The model must make the change and preserve the
protected information exactly (within NORMALIZATION).
### What it tests
Constraint retention and collateral-edit resistance.
### Failure exposed
The change is made, but nearby or protected content is edited.
### Anchors
REQUIRED = the target; PROTECTED = the named content; EDITABLE = narrow.
### Strategic value
One of the clearest tests of the central hypothesis.

## H05 — Multiple Instructions With Priority
### Test
Several instructions: a primary edit, one or more secondary edits, and explicit preservation
rules. Some instructions are more salient than others.
### What it tests
Instruction retention under multiple simultaneous requirements.
### Failure exposed
The main instruction is satisfied; secondary instructions or preservation rules are forgotten.
### Anchors
REQUIRED = all primary + secondary edits; PROTECTED = the preservation set.
### Strategic value
Directly tests whether the model remembers the full editing contract.

## H06 — Cross-Section Consistency
### Test
A change in one section requires another section, summary, table, note, or reference to stay
consistent. The correct action follows from the known relationship between sections.
### What it tests
Document-wide consistency across structurally separated information.
### Failure exposed
The requested section is edited; the required consistency update is not propagated.
### Anchors
REQUIRED = the primary section; DEPENDENT = the linked section value(s).
### Strategic value
Tests global reasoning across separated information.

## H07 — Minimal Safe Revision
### Test
Correct one issue with the smallest possible edit. Unrelated text is explicitly or implicitly
protected.
### What it tests
Minimal intervention.
### Failure exposed
Surrounding content is rewritten, style is changed, or unrelated modifications are introduced
(over-edit).
### Anchors
REQUIRED = the single fix; EDITABLE = minimal; everything else PROTECTED.
### Strategic value
Tests whether the model can tell "make it correct" from "rewrite it".

# MEDIUM TASKS

## M01 — Repeated Fact With Decoys
### Test
The target fact appears in relevant locations; similar values appear in unrelated contexts.
### What it tests
Target discrimination.
### Failure exposed
Plausible look-alikes are changed (over-edit).
### Anchors
REQUIRED = true targets; PROTECTED = decoys.
### Strategic value
Separates contextual understanding from naive search-and-replace.

## M02 — Historical Exception
### Test
The current value changes while historical statements intentionally keep the old value.
### What it tests
Temporal reasoning.
### Failure exposed
Valid historical information is destroyed (over-edit).
### Anchors
REQUIRED = current statements; PROTECTED = historical statements holding the old value.
### Strategic value
Tests whether the model separates stale information from intentionally historical information.

## M03 — Negation and Exception
### Test
The old or target value occurs inside negated statements or explicit exceptions.
### What it tests
Semantic interpretation of scope, negation, and exceptions.
### Failure exposed
Text is modified merely because it contains the target value.
### Anchors
REQUIRED = genuine targets; PROTECTED = occurrences inside negation/exception.
### Strategic value
Tests semantic editing rather than lexical matching.

## M04 — Table and Prose Synchronization
### Test
The same logical fact appears in prose and in a table or structured block.
### What it tests
Consistency across representations.
### Failure exposed
One representation is changed while the other stays inconsistent.
### Anchors
REQUIRED = both representations (keyed by locator); CONSISTENCY = they must match.
### Strategic value
Tests whether the model tracks a fact independently of its surface form.

## M05 — Format Preservation
### Test
Modify content while preserving the structural/formatting contract (headings, lists, table
structure, field order, markup, required sections).
### What it tests
Content editing under structural constraints.
### Failure exposed
Correct content is produced but document structure is damaged.
### Anchors
REQUIRED = the content change; PROTECTED = the structural contract (validated by a format
check, see ERROR TAXONOMY T13).
### Strategic value
Tests whether content editing and structure preservation can happen at once.

## M06 — Instruction Interference
### Test
The prompt contains several plausible improvements, but only one specific modification is
authorized.
### What it tests
Resistance to unnecessary changes.
### Failure exposed
The model "helps" beyond the requested operation (over-edit).
### Anchors
REQUIRED = the single authorized change; EDITABLE = that span only; everything else PROTECTED.
### Strategic value
Tests whether the model follows authorization boundaries instead of optimizing to its own
preferences.

# EASY TASKS

## E01 — Single Exact Edit
### Test
One clearly specified value must be changed.
### What it tests
Basic instruction following and editing ability.
### Anchors
REQUIRED = one span.
### Strategic value
Low-complexity control.

## E02 — Simple Repeated Edit
### Test
A clearly identified value occurs in multiple obvious locations; all relevant occurrences must
change.
### What it tests
Basic repeated-edit retention.
### Anchors
REQUIRED = all obvious occurrences.
### Strategic value
Low-cost control for the multi-location problem (H01).

## E03 — Simple Protected Content
### Test
One value must change while a nearby value is explicitly protected.
### What it tests
Basic preservation behavior.
### Anchors
REQUIRED = one span; PROTECTED = one nearby span.
### Strategic value
Low-cost over-edit control (H04).

## E04 — Exact Minimal Rewrite
### Test
One sentence must be rewritten to a precise instruction while unrelated content stays unchanged.
### What it tests
Basic minimal-edit behavior.
### Anchors
REQUIRED = one sentence; EDITABLE = that sentence; everything else PROTECTED.
### Strategic value
Low-cost control for minimal intervention (H07).

# CROSS-TASK DIFFICULTY DIMENSIONS

Tasks use controlled difficulty dimensions, not arbitrary complexity. Each is a generator
parameter (see `PLAN.md` SINGLE-ENGINE REQUIREMENT). Each generated case carries deterministic
tags for the dimensions present.

```text
D1  Number of Required Changes    one target vs several.
D2  Distance Between Related Info  nearby vs widely separated sections.
D3  Dependency Depth              direct replacement vs derived consequences.
D4  Scope Complexity              global vs conditional/exception-specific.
D5  Decoy Density                 few look-alikes vs many.
D6  Instruction Count             single vs multiple simultaneous instructions.
D7  Preservation Load             few protected elements vs many.
D8  Representation Diversity      prose vs tables/lists/headings/markup.
D9  Temporal Context              current vs historical information.
D10 Semantic Complexity           positive vs negation/exception/conditional.
D11 Edit Locality                 single sentence vs distributed edits.
D12 Minimality Constraint         broad acceptable edit vs strict minimal change.
D13 Context Length                short vs longer documents.
D14 Distractor Content            relevant-looking but unrelated facts.
```

## TASK RELATIONSHIPS

Tasks overlap at the capability level but are not duplicates.

```text
                    CONSTRAINED
                    EDITING
                       |
       +---------------+----------------+
       |               |                |
   WHAT CHANGES    WHAT STAYS       WHAT DEPENDS
       |               |                |
  H01, H03, H06    H04, H07, M02      H02, M04
       |               |                |
       +---------------+----------------+
                       |
                 INSTRUCTION
                  RETENTION
                       |
                 H05, M06, E01-E04
                       |
              SEMANTIC DISAMBIGUATION
                       |
              M01, M02, M03, M05
```

The suite should reveal whether failure comes from identifying targets, remembering
instructions, understanding scope, understanding dependencies, preserving invariants, or
controlling the amount of change.

## REQUIRED SCORING VIEWS

The benchmark MUST expose at least these result categories, each with a 95% Wilson interval and
reported over >= 3 runs:

```text
Required-Change Accuracy   did the model make everything that should change?
Preservation Accuracy      did it preserve everything that should remain?
Unauthorized-Change Rate   how often did it modify unauthorized content? (over-edit)
Consistency Accuracy       did dependents and parallel representations stay consistent?
Final Validity             does the result satisfy the structural/format contract?
Overall Case Success       did the whole case satisfy every condition?
```

The paired headline (under-edit rate vs over-edit rate per model) is derived from
Required-Change Accuracy and Unauthorized-Change Rate. Exact formulas are frozen in `TRD.md`
before scoring.

## ERROR TAXONOMY

The scorer classifies failures deterministically where possible:

```text
T01 missed required edit            T09 decoy modification
T02 incomplete multi-location edit  T10 historical-content modification
T03 incorrect dependent value       T11 negation/exception error
T04 scope violation                 T12 table/prose inconsistency
T05 protected-content modification  T13 formatting/structure violation
T06 forgotten secondary instruction T14 excessive rewrite
T07 cross-section inconsistency     T15 malformed final output
T08 unauthorized improvement
```

Additional categories MAY be added only for a distinct failure mode.

## CASE GENERATION PRINCIPLES

Cases are generated programmatically from controlled templates by the single generator. The
generator MUST support:

- fixed seeds;
- known source facts;
- deterministic expected results and anchors (REQUIRED/PROTECTED/DEPENDENT/EDITABLE);
- controlled target locations, protected locations, decoys, and dependencies;
- deterministic locators for every anchor (no fuzzy search at scoring time);
- development/test separation.

The test set MUST NOT be copied from the development set.

## MODEL CONDITIONS

The same task contract is used for every evaluated model. Record, where available: model
name/version, prompt, temperature, context, output constraints, run count, execution cost,
latency. Do not change the prompt to favor a model unless that change is an explicit experiment.

## COST STRATEGY

The 17 tasks need not use equal budget.

```text
Smoke test:     17 tasks x small case count
Main eval:      HIGH tasks prioritized
Secondary:      MEDIUM tasks
Control:        EASY tasks
Deep repeats:   only where results are informative (to tighten intervals)
```

Exact case count per task is UNRESOLVED until Kaggle model availability, execution cost, and
smoke-test results are measured.

## VALIDATION

Before large model evaluation:

- every task MUST have at least one positive and one negative fixture where applicable;
- every scorer check MUST be tested against known-good and known-bad outputs;
- protected-content checks MUST be tested;
- over-edit detection MUST be tested;
- under-edit detection MUST be tested;
- dependency calculations MUST be independently verified;
- format checks MUST be deterministic;
- malformed-output handling MUST be exercised (captured = false path);
- the NORMALIZATION rule MUST be tested against harmless-reflow cases to confirm it does not
  raise false over-edit flags;
- a small sample of generated cases MUST be inspected manually.

## TASK FREEZE

Before the final test run, freeze: (1) task definitions; (2) case generator version; (3)
scoring rules and NORMALIZATION; (4) development/test split; (5) model lineup once availability
is known; (6) evaluation settings. Do not change a task after seeing final results merely
because it produced an inconvenient result.

## CURRENT STATE

- Central capability: DECIDED.
- 17-task structure: DECIDED.
- Output + scoring contract: DECIDED (full document + anchors; no fuzzy diff).
- Tier-0 core: DECIDED (H01, H04, H07).
- Exact case schemas: TO BUILD from the generator spec.
- Exact metrics and formulas: TO FREEZE in `TRD.md`.
- NORMALIZATION rule: TO FREEZE in `TRD.md`.
- Exact model lineup: UNKNOWN.
- Exact budget allocation: UNRESOLVED.

## NEXT ACTIONS

1. Build the single generator and the shared anchor scorer.
2. Implement the Tier-0 triangle (H01, H04, H07) as generator configs.
3. Implement and test every scorer check against known-good / known-bad fixtures.
4. Freeze NORMALIZATION and the metric formulas in `TRD.md`.
5. Run the 17-task smoke test (Tier-0 first).
6. Measure model disagreement and execution cost.
7. Freeze the final test configuration.
8. Execute the staged benchmark.
