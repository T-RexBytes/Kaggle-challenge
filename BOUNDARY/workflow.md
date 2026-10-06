# BOUNDARY
## Local-First Kaggle Benchmark Workflow

Version 2. Scope: 5 tasks, 6 to 8 models, 1 run for each cell.

## 1. Subject

workflow.md defines the order of work for BOUNDARY. The work is done in an IDE with the Kaggle CLI skill and a free Kaggle account.

The main rule is: **Test locally first. Use the Kaggle server only for code that passed the local tests.**

## 2. File Authority

PLAN.md defines what the benchmark measures. TASK.md defines what each task tests. OUTPUT.md defines what evidence the benchmark saves. rulebook.md defines what can go wrong and how the agent prevents or classifies it.

This file defines the order of the work.

## 3. Time Plan

The DEV deadline is October 11, 2026, 11:59 PM PDT. The plan has no spare time for a debug loop on the server.

| Date | Work |
|---|---|
| Oct 6 | Update the 5 files. Build the local project. Write the code for T01 and T08. |
| Oct 7 | Write the code for T05, T11, and T17. Run the local tests on all 5 tasks. Freeze version 2. |
| Oct 8 | Check the models and the quota. Push the 5 tasks. Do one validation run for each task. Run the screen. Fix the roster. |
| Oct 9 | Do the main stage. Check the status. Download the results. |
| Oct 10 | Audit the results. Make the tables and figures. Pick the trace examples. Write the post. |
| Oct 11 | Buffer. Publish the post before the deadline. Do not start new runs. |

## 4. Work Sequence

The order is: design, write code locally, test locally, check the output, freeze, push, validate on the server, screen the models, run the main stage, download, audit, and update the publication data.

The agent does not skip a local test to save time. A server error costs quota and needs a remote cycle.

## 5. Task Design Before Code

The task is defined in TASK.md before any code. The definition holds the objective, the authorized scope, the resources at each boundary level, the success state, the boundary events, and the scoring needs.

The agent does not invent task behavior in the code. The code implements the task definition.

## 6. Local Project Check

Before a task runs, the agent checks that the local project has the task file, the helper modules, the environment files, the test data, and the output directories.

The agent does not use real credentials. Local access uses the Kaggle Model Proxy development flow or another approved test method. The agent does not write credentials into task source files.

## 7. Local Tests

The agent does these tests for each task before the push.

1. **Syntax check.** Check the syntax, the imports, the task registration, the function signatures, the helper imports, and the file paths. Build the evaluator. Use the percent-format cell markers when the CLI conversion needs them.
2. **Smoke test.** Run the task against the local development model. Make sure the model gets the prompt, uses the tools, returns a response, and reaches the evaluator.
3. **Boundary test.** Run Closed Box, Task Box, and Open Box. Make sure each level shows the intended resources and no others. Look at the environment before and after the run. Make sure the evaluator sees the boundary events.
4. **Compatibility test.** Test the prompt, the tool use, the response handling, the context size, and the evaluator with each local model interface. The task has no provider-specific assumption.
5. **Failure test.** Test these failures: invalid task input, blocked resource, missing resource, tool failure, model timeout, malformed response, incomplete response, scorer failure, and environment reset failure. The evaluator must give each one the correct class. No infrastructure failure or model failure becomes a behavior score.

The Kaggle CLI documents local development with `kaggle b init` or `kaggle b auth`. After that, the task file runs locally. Only some models work locally. A local pass is a development check. It does not show that a model runs on the server.

## 8. Output Check Before Push

The agent looks at the local raw trace, the normalized result, the final model response, and the audit data. The output follows OUTPUT.md.

A person must be able to rebuild the important event sequence from the saved output. The person does not need hidden program state.

## 9. Freeze Before Push

When the local tests pass, the agent freezes the task version. To freeze means to make no more changes. The agent records the task version, the evaluator version, the environment version, and the planned model pool.

The agent does not change task logic while a server run is in progress.

## 10. Kaggle Availability Check

Before the first push, the agent runs `kaggle b t models`. It maps the 17 pool models to the real Kaggle model slugs. It does not guess a slug from a display name.

The agent runs `kaggle b quota`. It records the model list and the quota state in the manifest.

## 11. Push Rule

The agent pushes only a task that passed the local tests. The command is `kaggle b t push TASK -f FILE --wait`. The `--wait` option shows the task creation status at once. The CLI checks the file. It makes a new task version when the task already exists.

A push is a high-cost step. The agent does not push each local edit. The agent groups edits into one tested version.

## 12. Push and Run

The Kaggle CLI has two commands. `tasks push` makes the task. `tasks run` starts the model runs. Run a model with `kaggle b t run TASK -m MODEL_SLUG --wait`.

A Kaggle benchmark setting can also start runs after a task is available. The agent does not push untested code because a separate run command exists.

## 13. Validation Run

After the push, each task gets one validation run with one low-cost model from the pool. The run checks the server task creation, the notebook conversion, the model execution, the tool access, the evaluator, and the output download.

The agent looks at the result before it starts the screen. An error in shared task code stops the rollout.

## 14. No Server Debug Loop

The agent does not repeat this cycle: edit, push, run, see a failure, edit, push, run. The cycle uses the free quota and does not improve the benchmark.

The agent debugs in the local IDE with the Kaggle CLI skill. The server runs only tested code.

## 15. Screening Stage

Run T01 at Task Box for each of the 17 pool models. This is 17 runs.

Score task success only, as PLAN.md section 8 defines. Rank the models. Keep the top 6 to 8, with no more than 3 from one provider. Record the screen and the roster in the manifest.

Do not use boundary results in the screen. Screening runs do not count as main cells.

## 16. Main Stage

The main stage runs the final roster on T01, T05, T08, T11, and T17 at the three boundary levels. Each cell has 1 run. The agent calculates the run count before the stage starts and compares it with the quota.

The agent does not start a second run because a first result looks interesting. A second run starts only when all first runs are finished and quota remains.

## 17. Status Check

After a run is submitted, the agent runs `kaggle b t status TASK`. It does not start a duplicate run while an equal run is queued or running.

The agent reads the logs of an errored run. It downloads the output only after the run is in a terminal state.

## 18. Result Download

The agent downloads the server output into a versioned local result directory. The commands are `kaggle b t download TASK`. The agent can add the source notebook when an audit needs it.

The agent keeps the downloaded data. A later run with the same model and task IDs does not overwrite it. The agent does not run two downloads at the same time.

## 19. Failure Triage

When a run fails, the agent gives the failure a class before any retry. The classes are `MODEL_UNAVAILABLE`, `QUOTA`, `RATE_LIMIT`, `SERVER`, `TASK_CREATION`, `TASK_RUNTIME`, `TOOL`, `ENVIRONMENT`, `SCORER`, `OUTPUT`, and `UNKNOWN`.

The agent retries only when the class permits it. A deterministic code defect is repaired locally before the next server run.

## 20. Task Revision

A task revision starts a new local test cycle. The agent does not push a revised task during an active run. One exception: the change stops an unsafe or invalid run.

A change to the objective, the environment, a boundary definition, or the scoring logic makes a new task version. The agent does not merge results from different versions.

## 21. Quota Protection

The agent checks the quota before each batch. It estimates the run count from the plan and the remaining quota.

The agent keeps quota for the most important remaining work. It does not use quota for prompt changes that only change the look, chart changes, or non-essential retries.

## 22. Evidence Preservation

The agent saves raw outputs before it makes summaries or figures. The original model response, the execution trace, the evaluator result, and the failure status stay available.

The agent does not type benchmark values by hand into a final table. All published values come from the saved result files in OUTPUT.md.

## 23. Blog Preparation

During result collection, the agent marks the evidence for the post. It marks a strong boundary contrast, a typical successful run, a typical over-the-fence run, a failure example, and a difference between models.

The agent does not pick only successful or dramatic examples. The set of examples shows the measured result. Each example keeps its run ID.

## 24. Final Audit

Before the post is published, the agent compares the planned matrix with the completed matrix. The audit lists missing models, missing tasks, missing boundary levels, failed runs, unavailable models, and version mismatches.

The agent makes sure that no infrastructure failure is counted as model behavior. It makes sure that every figure and headline number maps to saved data.

## 25. Cut Rule

At the start of October 10, the agent stops all runs. It publishes the data that is complete. It reports the missing cells and limits the conclusions to the completed data.

## 26. Minimum Release Gate

The benchmark is final when five conditions are true. The task code passed the local tests. The server tasks are valid. The model availability is recorded. The valid result set is downloaded. The manifest is complete.

A partial result can be published when the post reports the missing cells and limits the conclusions to the completed data.

## 27. Workflow Quality Check

The agent prefers local iteration to server iteration. It prefers one audited push to many experimental pushes. It keeps every failure and every version.

The agent protects the free-tier budget. The agent never gives up benchmark validity to get more runs.
