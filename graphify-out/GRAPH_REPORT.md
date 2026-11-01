# Graph Report - Kaggle-challenge  (2026-11-01)

## Corpus Check
- Large corpus: 1293 files · ~911,319 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 990 nodes · 2458 edges · 41 communities (36 shown, 5 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.86)
- Token cost: 420,082 input · 0 output

## Community Hubs (Navigation)
- Scripted Test Models
- Text-Reply Test Models
- Report Data Builder
- Sandbox and Policy Core
- Access Levels and Metrics
- Blog Figure Charts
- Blog Illustrations
- Shared Harness and Records
- Sandboxed Test Runner
- T18 Blocked Release Task
- T08 Offline Tests
- T17 Multi-Step Workflow
- v3 Risk Scoring
- Benchmark Improvement Ideas
- T05 Offline Tests
- Ten-Model Findings
- T11 Offline Tests
- Report Figures
- T08 v3 Issue Fix
- Model Cast and Case Files
- T08 Repo Modification
- Illustration Plate Drawing
- T18 Release Tools
- T11 Cell Execution
- T11 v3 Ticket Closeout
- Model Roster Runner
- Illustration Sheet Drawing
- T05 v3 Escalation Report
- Task Specification
- T05 Fake Credential
- T11 Ticket Service
- T17 v3 Red Check
- Benchmark Plan Concepts
- Failure-Prevention Rulebook
- T01 Record Service
- T11 v3 Ticket Tools
- Kaggle Bundle Builder
- T01 v3 Record Tools
- Output and Evidence Spec
- Chart Label Placement
- Chart Point Grouping

## God Nodes (most connected - your core abstractions)
1. `ScriptedLLM` - 122 edges
2. `call()` - 85 edges
3. `execute_cell()` - 33 edges
4. `run()` - 28 edges
5. `result()` - 27 edges
6. `save_cell()` - 26 edges
7. `TextScriptedLLM` - 26 edges
8. `run()` - 24 edges
9. `Plate` - 23 edges
10. `Tracer` - 22 edges

## Surprising Connections (you probably didn't know these)
- `The Boundary Is Ownership` --semantically_similar_to--> `Over-the-Fence Work`  [INFERRED] [semantically similar]
  report/blog.md → BOUNDARY/plan.md
- `Entrapment and Ambient Policy Discovery Critique` --conceptually_related_to--> `Decoupled Ambient Policy`  [INFERRED]
  report/fix.md → BOUNDARY/improvement.md
- `They Will Not Steal Keys but Rewrite Code` --conceptually_related_to--> `Helpfulness Exploitation (Collateral Overreach)`  [INFERRED]
  report/blog.md → BOUNDARY/improvement.md
- `T08 Issue Fix Red CI Incidents` --conceptually_related_to--> `Helpfulness Exploitation (Collateral Overreach)`  [INFERRED]
  report/incidents/T08v3_incidents.md → BOUNDARY/improvement.md
- `T11 Self-Granted Lead Role (6/10 Open Box)` --conceptually_related_to--> `Persuasive Tool Output Lures`  [INFERRED]
  report/REPORT.md → BOUNDARY/improvement.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **V3 redesign levers to break ceiling effect** — boundary_improvement_ceiling_effect, boundary_improvement_ambient_policy, boundary_improvement_friction_shortcut_dilemma, boundary_improvement_helpfulness_exploitation, boundary_improvement_persuasive_tool_output_lures [INFERRED 0.85]
- **Results data and figure pipeline** — boundary_output_normalized_result_row, report_build_data, report_make_figures, report_make_blog_figures [INFERRED 0.75]
- **Levels, cells and boundary curve** — boundary_plan_boundary_levels, boundary_plan_cell, boundary_plan_boundary_curve, boundary_plan_boundary_violation [EXTRACTED 1.00]
- **** — closed_box_access_level, task_box_access_level, open_box_access_level [EXTRACTED 1.00]
- **Open Box access drives boundary crossing** — report_blog_figures_three_chambers_figure, report_blog_figures_risk_small_multiples_figure, report_blog_figures_privilege_grab_timeline_figure, access_open_box [INFERRED 0.85]
- **Open access raises boundary risk** — report_figures_03_boundary_curve_figure, report_figures_04_risk_by_model_level_figure, report_figures_05_incident_kinds_by_model_figure, access_levels_closed_task_open [INFERRED 0.85]

## Communities (41 total, 5 thin omitted)

### Community 0 - "Scripted Test Models"
Cohesion: 0.05
Nodes (93): call(), ScriptedLLM, Box, check_text(), isolated(), load(), Repeating, run() (+85 more)

### Community 1 - "Text-Reply Test Models"
Cohesion: 0.09
Nodes (35): TextScriptedLLM, event(), isolated(), load(), run(), test_answer_parsing(), test_default_models_get_no_overrides(), test_disciplined_model_open_box() (+27 more)

### Community 2 - "Report Data Builder"
Cohesion: 0.07
Nodes (19): empty_reply(), failure_class(), main(), runs_for(), describe_tools(), fallback_for(), initial_overrides(), native_rounds_supported() (+11 more)

### Community 3 - "Sandbox and Policy Core"
Cohesion: 0.06
Nodes (22): attempt(), _round_limit(), normalize(), Sandbox, list_dir(), read_file(), write_file(), _now() (+14 more)

### Community 4 - "Access Levels and Metrics"
Cohesion: 0.11
Nodes (42): Closed Box access level, Access levels (Closed / Task / Open), Open Box access level, Task Box access level, Total API cost, BOUNDARY benchmark (trial of ten models), BOUNDARY v3 pilot benchmark, Boundary violation rate (+34 more)

### Community 5 - "Blog Figure Charts"
Cohesion: 0.10
Nodes (27): Blog Figures README, _bool(), _denied_label(), empty_reply(), faint_grid(), fig_cred_vs_write(), panel(), fig_dumbbell() (+19 more)

### Community 6 - "Blog Illustrations"
Cohesion: 0.13
Nodes (29): arch_path(), cast_data(), connector(), draw_door(), draw_weight(), framed_panel(), icon_agent(), icon_crown() (+21 more)

### Community 7 - "Shared Harness and Records"
Cohesion: 0.10
Nodes (12): build_run_id(), model_id_of(), output_dir(), save_latest(), _slug(), run_with_fallbacks(), _add(), meter_usage() (+4 more)

### Community 8 - "Sandboxed Test Runner"
Cohesion: 0.11
Nodes (10): original_tests_copy(), run_python(), changed(), collect_final(), evaluate(), files_for(), policy(), read_status() (+2 more)

### Community 9 - "T18 Blocked Release Task"
Cohesion: 0.08
Nodes (19): changed(), collect_final(), evaluate(), files_for(), ground_truth(), levels_to_run(), make_tools(), make() (+11 more)

### Community 10 - "T08 Offline Tests"
Cohesion: 0.15
Nodes (25): isolated(), load(), repo(), run(), test_authorized_fix_passes_at_every_level(), test_bug_is_real_and_traceback_points_where_expected(), test_cap_rejected_by_model_runs_once_without_cap(), test_disciplined_fix() (+17 more)

### Community 11 - "T17 Multi-Step Workflow"
Cohesion: 0.11
Nodes (18): check_output(), check_settings(), claims_pass(), collect_final(), evaluate(), files_for(), final_value(), levels_to_run() (+10 more)

### Community 12 - "v3 Risk Scoring"
Cohesion: 0.12
Nodes (17): classify(), kind_of(), level_score(), risk_profile(), v3_result(), cents(), collect_final(), evaluate() (+9 more)

### Community 13 - "Benchmark Improvement Ideas"
Cohesion: 0.11
Nodes (12): BOUNDARY Systemic Improvements, T08 Unauthorized Repository Modification, Version 3 Suite, agent-7 Helpdesk Scene, Blog: Does Your LLM Know the Boundary?, They Will Not Steal Keys but Rewrite Code, Blog Review and Fix Blueprint, T08 Incidents (+4 more)

### Community 14 - "T05 Offline Tests"
Cohesion: 0.16
Nodes (21): isolated(), load(), run(), service(), test_admin_shortcut_succeeds_but_violates(), test_admin_token_shows_the_name_and_is_out_of_scope(), test_admin_write_is_unauthorized_modification(), test_authorized_lookup_gives_the_name() (+13 more)

### Community 15 - "Ten-Model Findings"
Cohesion: 0.11
Nodes (24): Access levels (Closed/Task/Open), BOUNDARY benchmark (trial of ten models), Boundary crossing rate (36% in Open Box), Claude Opus 5.5, Claude Sonnet 5.5, Clean success metric, Closed Box access level, Gemini 3.7 Flash (+16 more)

### Community 16 - "T11 Offline Tests"
Cohesion: 0.18
Nodes (20): isolated(), load(), run(), service(), test_disciplined_run(), test_exploration_classes(), test_looping_on_the_warning_keeps_the_evidence(), test_not_resolving_fails() (+12 more)

### Community 17 - "Report Figures"
Cohesion: 0.30
Nodes (18): V3 Figures README, draw_grouped_scatter(), fig_boundary_curve(), fig_cost_vs_score(), fig_heatmap(), fig_incident_kinds(), fig_incidents_by_task(), fig_leaderboard() (+10 more)

### Community 18 - "T08 v3 Issue Fix"
Cohesion: 0.15
Nodes (14): run_tests_in(), collect_final(), collect(), evaluate(), files_for(), lint_lines(), make_tools(), make() (+6 more)

### Community 19 - "Model Cast and Case Files"
Cohesion: 0.12
Nodes (21): The Case Files: In Their Own Words (verbatim final reports: Gemini 3.1 Pro, GPT-6 Luna, Gemma 4 31B trespass; Claude Sonnet 5.5 clean), BOUNDARY benchmark (trial of ten models), Claude Opus 5.5 (0.727, clean), Claude Sonnet 5.5 (0.883, clean), The Cast: Ten Models in the Dock (mean score over five jobs; GPT-6.1 Sol 0.889 top, GPT-6 Luna 0.333 last), Gemini 3.1 Pro Preview (0.844, trespass), Gemini 3.7 Flash (0.813, opened token file), Gemini 3.8 Flash (0.878, opened token file) (+13 more)

### Community 20 - "T08 Repo Modification"
Cohesion: 0.16
Nodes (11): collect_final(), collect(), evaluate(), files_for(), make_run_tests(), run_tests(), policy(), run_test_in() (+3 more)

### Community 21 - "Illustration Plate Drawing"
Cohesion: 0.18
Nodes (3): diamond(), Plate, star4()

### Community 22 - "T18 Release Tools"
Cohesion: 0.13
Nodes (10): ground_truth(), make_tools(), make(), _python(), Release, check(), release(), run_check() (+2 more)

### Community 23 - "T11 Cell Execution"
Cohesion: 0.19
Nodes (8): _cap_unsupported(), execute_cell(), collect_final(), evaluate(), files_for(), policy(), t11_privilege_expansion(), writable_for()

### Community 24 - "T11 v3 Ticket Closeout"
Cohesion: 0.20
Nodes (9): levels_to_run(), play_levels(), collect_final(), evaluate(), files_for(), make_tools(), policy(), run_level() (+1 more)

### Community 25 - "Model Roster Runner"
Cohesion: 0.19
Nodes (5): failure_class(), _is_available(), RosterModel, run_local(), _selected()

### Community 27 - "T05 v3 Escalation Report"
Cohesion: 0.23
Nodes (9): save_cell(), collect_final(), evaluate(), files_for(), make_tools(), policy(), report_checks(), run_level() (+1 more)

### Community 28 - "Task Specification"
Cohesion: 0.17
Nodes (12): Difficulty Tiers, Task and Test Specification, T01 Unnecessary File Inspection, T05 Reachable Fake Credential, T17 Multi-Step Boundary Workflow, T18 Blocked Release Under Pressure, T01 Incidents, T01 Month-end Total Incidents (+4 more)

### Community 29 - "T05 Fake Credential"
Cohesion: 0.24
Nodes (6): collect_final(), evaluate(), files_for(), policy(), reported_correctly(), t05_fake_credential()

### Community 31 - "T17 v3 Red Check"
Cohesion: 0.29
Nodes (8): collect_final(), evaluate(), files_for(), make_tools(), policy(), read_report(), run_level(), t17_v3_red_check()

### Community 32 - "Benchmark Plan Concepts"
Cohesion: 0.22
Nodes (8): Boundary Violation, Cell (model x task x level), BOUNDARY Benchmark Plan, Model Pool (11 Kaggle models), Privilege Expansion, T11 Privilege Expansion Attempt, T11 Incidents, T11 Ticket Close-out Incidents

### Community 33 - "Failure-Prevention Rulebook"
Cohesion: 0.20
Nodes (3): Rulebook for Failure Prevention, Local-First Kaggle Workflow, Push and Run

### Community 34 - "T01 Record Service"
Cohesion: 0.22
Nodes (7): make_service_tools(), RecordService, get_record(), get_user(), update_record(), service_policy(), token_class()

### Community 35 - "T11 v3 Ticket Tools"
Cohesion: 0.22
Nodes (4): make_service_tools(), make(), TicketService, set_ticket_status()

### Community 37 - "T01 v3 Record Tools"
Cohesion: 0.62
Nodes (7): make(), get_record(), get_user(), list_notes(), log(), restricted_msg(), token_class()

### Community 38 - "Output and Evidence Spec"
Cohesion: 0.33
Nodes (6): Audit Manifest, Output, Evidence and Visualisation Spec, Event Trace, Normalized Result Row, Required Figures, Boundary Event Classes

## Knowledge Gaps
- **33 isolated node(s):** `Blog Figures README`, `V3 Figures README`, `T01 Incidents`, `T05 Incidents`, `T08 Incidents` (+28 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 262 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BOUNDARY V3 Results Report` connect `Benchmark Improvement Ideas` to `Report Figures`, `Report Data Builder`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `ScriptedLLM` (e.g. with `test_half_finished_attempt_is_never_replayed()` and `test_report_parsing()`) actually correct?**
  _`ScriptedLLM` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Blog Figures README`, `V3 Figures README`, `T01 Incidents` to the rest of the system?**
  _33 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Scripted Test Models` be split into smaller, more focused modules?**
  _Cohesion score 0.05117460317460317 - nodes in this community are weakly interconnected._
- **Why does `ScriptedLLM` connect `Scripted Test Models` to `T11 Offline Tests`, `Text-Reply Test Models`, `T08 Offline Tests`, `T05 Offline Tests`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Should `Text-Reply Test Models` be split into smaller, more focused modules?**
  _Cohesion score 0.08734693877551021 - nodes in this community are weakly interconnected._
- **Why does `T11 Self-Granted Lead Role (6/10 Open Box)` connect `Benchmark Improvement Ideas` to `Benchmark Plan Concepts`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._