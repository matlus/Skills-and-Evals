# Skills and Evals

A hand-built eval harness for prompts, with real results you can read and reproduce. There is no plugin and nothing
hidden: every step, from starting a fresh coding-assistant session to grading its answer and explaining a failure, is
plain Python you can read and step through.

The repository answers one practical question: **when you change a prompt, or a new model ships, does the prompt still
do its job, and if not, exactly why not?** It does that for one realistic task (personal expense analysis) across
three prompt versions and six models from two vendors, and it keeps every answer, grade and scorecard in `results/`.

- [Results at a glance](#results-at-a-glance)
- [What is being evaluated](#what-is-being-evaluated)
- [Test vs. eval](#test-vs-eval)
- [How one eval run works](#how-one-eval-run-works)
- [The checks](#the-checks)
- [Why a check failed](#why-a-check-failed)
- [Reading the results](#reading-the-results)
- [Running the evals yourself](#running-the-evals-yourself)
- [Two versions of the same eval](#two-versions-of-the-same-eval)
- [Layout and tooling](#layout-and-tooling)

## Results at a glance

All results below come from the run folders in [`results/pwi/expense_analysis/`](results/pwi/expense_analysis/), graded
against the current reference key (revised 2026-10-10). Every model ran at medium effort; graders ran in Claude Code
(Sonnet, low effort). A model **passes the gate** when every check reaches its minimum pass rate of 80%.

### Six models on the final prompt (`robust-tables-first`, 5 runs each)

| Model | Assistant | Gate | Checks below 5/5 | Main traced causes |
|---|---|---|---|---|
| Claude Opus 5.5 | Claude Code | ✅ Passed | none | none |
| GPT-6.1 Sol | Codex | ✅ Passed | none | none |
| GPT-6 Astra | Codex | ✅ Passed | none | none |
| Claude Sonnet 5.5 | Claude Code | ✅ Passed | both Delta charges kept 4/5, August travel 4/5 | one run dropped the $412.60 Delta charge as a duplicate |
| Claude Haiku 5.5 | Claude Code | ❌ Failed | uncategorized count 2/5, August travel 3/5, three more at 4/5 | moved IKEA out of Shopping; left out Airport Parking; merged Transport and Travel |
| GPT-6 Luna | Codex | ❌ Failed | July shopping 0/5, August travel 0/5, findings 0/5, four more | counts pharmacies and Amazon Prime as Shopping; drops travel entries; puts Bowl-O-Rama in Dining |

### Three prompts on the same task

| Prompt | What it is | Opus 5.5 (5 runs) | Sonnet 5.5 (5 runs) |
|---|---|---|---|
| `standard` | the simple version | ❌ fails on uncategorized count 0/5, largest increase 2/5, findings 3/5, August travel 4/5 | ❌ fails on uncategorized count 0/5, findings 2/5, largest increase 2/5, August travel 3/5, tables first 3/5 |
| `robust` | the precise version | ❌ only "tables before interpretation" fails, 0/5 | ❌ only "tables before interpretation" fails, 1/5 |
| `robust-tables-first` | `robust` with an explicit reply order | ✅ passes every check 5/5 | ✅ passes |

The precise prompt fixes the analysis errors of the simple one, and the explicit reply order fixes its one remaining
formatting failure. Below Sonnet and Astra, the remaining misses are analysis errors rather than formatting, so a
stronger model helps more than a stronger prompt.

## What is being evaluated

The task: a user hands an assistant a messy, hand-kept list of 198 expenses for June to August 2026 plus two budget
notes, and asks for monthly totals, budget comparisons and the three most important findings.

The input (`evals/expense_analysis/cases/june_august_2026/inputs/`) is seeded with traps a careful analyst must handle:
inconsistent date formats, a refund written as `- -$68.00`, an exact duplicate entry, two different Delta charges on
the same day that are not duplicates, transfers and ATM withdrawals that are not spending, and merchants whose category
is a judgment call (books, a game store, an Uber during a trip).

Three prompt variants are compared in `evals/expense_analysis/prompts/`:

- `standard.md`: the simple prompt.
- `robust.md`: the precise prompt, which spells out cleaning, categorization, disclosure and output rules.
- `robust_tables_first.md`: `robust` with an explicit reply order, tables first, added after `robust` kept leading with conclusions.
  It is the **gated** variant: its pass rates decide whether a run passes.

The expected answers come from an independently computed reference key ([`expense_reference_key.md`](evals/expense_analysis/cases/june_august_2026/expense_reference_key.md)). It accepts more than one answer where the
input supports more than one reasonable policy (for example, books may be Entertainment or Shopping), as long as the
answer discloses the policy it used.

## Test vs. eval

A **test** checks deterministic code. Same input, same output. Anything less than 100% is a bug.

An **eval** measures a system that varies, such as an LLM following a prompt. It runs each case several times in
isolated sessions and reports a **pass rate** per check. A check passes the gate when its pass rate reaches the
minimum you chose, for example 80%.

This repository has both:

| What | Kind | Where | Runs a model? |
|---|---|---|---|
| The harness's own behavior (gateways, graders, scorecard, failure tracing) | Tests (115) | `packages/prompt-evals/tests` | No. A spy replaces the `claude` and `codex` processes. |
| The expense-analysis prompts | Eval | `evals/expense_analysis` | Yes, real isolated sessions |

The eval's graders are code, so they get ordinary tests too. For example, `test_amount_check_grading_processor.py`
proves that a one-cent difference passes and a two-cent difference fails.

## How one eval run works

```
eval_suite.json ──► for each prompt variant × case × repetition
                      │  Arrange: fresh temp folder with ONLY the case's input files
                      │  Act:     claude -p --model M --effort E --restricted --strict-mcp-config
                      │                    --disable-slash-commands --no-session-persistence
                      │                    --permission-mode dontAsk --tools Bash,Read,...
                      │                    --output-format stream-json --verbose   (prompt on stdin)
                      │           (or: codex exec --json --ephemeral ... for Codex models)
                      ▼
                  event stream: final answer + every tool call and its result
                      │
                      ▼  Assert (graders, each in its own tool-less session or in code)
                  fact extraction (LLM → JSON) ─► amount / fact_value checks (code)
                  tool-call log                ─► tool_use check (code)
                  rubric                       ─► judge check (LLM-as-judge)
                      │
                      ▼  a failed total is traced in the reference ledger (code): which entries make the difference
                  scorecard: pass rate per check per prompt variant, gate PASSED/FAILED, failure causes
```

The answer key never enters a trial session. Expected values live in files that only the grading code reads, and each
trial sees only the files in its case's `inputs/` folder. The suite loader refuses a key placed where a trial could read it.

## The checks

`evals/expense_analysis/eval_suite.json` defines 16 checks, each with a grader and a minimum pass rate:

| Check | Grader | What it proves |
|---|---|---|
| `dining-june-total`, `dining-july-total`, `dining-august-total` | amount | Dining & coffee totals are $212.74, $165.14, $398.69 |
| `dining-august-over-budget` | fact_value | August dining is reported over the $260 target |
| `refund-netted` | fact_value | The −$68.00 REI refund reduces spending |
| `shopping-july-total` | amount | July shopping is $756.72 (only true when the refund is netted) |
| `duplicate-flagged` | fact_value | The repeated Trader Joe's $54.12 entry is flagged |
| `both-delta-charges-kept` | fact_value | Both Delta charges are counted; neither is mistaken for a duplicate |
| `travel-august-total` | amount | August travel is $1,655.92 (or $1,631.82 with the 8/16 Uber in Transport) |
| `uncategorized-entry-count` | fact_value | All 8 transfers and ATM withdrawals stay uncategorized |
| `largest-increase-is-travel` | fact_value | Travel is the largest July-to-August increase |
| `code-executed` | tool_use | Totals were computed by running Python, read from the tool-call log |
| `ambiguous-entries-not-forced` | judge | Transfers are not forced into a spending category |
| `tables-before-interpretation` | judge | Computed tables come before the interpretation |
| `three-supported-findings` | judge | Exactly three findings, each consistent with the numbers |
| `no-invented-budgets` | judge | Only the two stated budget targets are used |

| Grader | Decides with | Use it for |
|---|---|---|
| `amount` | code, ±$0.01 | numbers that must be right |
| `fact_value` | code, case-insensitive match | flags, categories, statuses |
| `tool_use` | code, reading the tool-call log | proving something actually ran, e.g. Python |
| `judge` | a separate model with a rubric | judgment calls: ordering, "supported by the data", "nothing invented" |

`amount` and `fact_value` need a fact first. A separate model session reads the answer and fills a JSON schema, and
then code compares those facts to `expected_facts.json`. The model only extracts; the code decides.

## Why a check failed

A failing acceptance test tells you what was expected and what went wrong. These evals do the same for wrong totals,
so nobody has to reconcile the expense log by hand.

The reference key also exists entry by entry in `cases/june_august_2026/reference_ledger.json`: every line of the
expense log with its category, any other category an accepted policy allows, and whether it counts (the likely
duplicate does not). When a total is wrong, code looks for the fewest entry mistakes that add up exactly to the
difference: a reference entry left out, another category's entry counted in, the duplicate counted, or a refund with
its sign reversed. It first applies any accepted policy that brings the reference closer to the answer. For example:

> Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'),
> a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).

Amount checks are traced from the extracted amount. Judge checks are traced from the amounts the judge disputes: the
judge quotes the answer's number and the rubric's reference value, and code finds the one ledger total with that value.
The judge never explains the cause itself, so the cause is not another model's guess. Beyond two mistakes the search
tries only plausible ones, because among dozens of entries three arbitrary amounts add up to almost any difference.
When nothing simple fits, the cause says so instead of guessing. Counts and yes/no facts are not traced yet.

Each traced cause appears in the trial's `grade.json` (`diagnoses`), after the failure reason in `scorecard.md`, and
grouped in the scorecard's **Failure causes** section. One cause in many runs means one of two things: a systematic
mistake, or a reference key that is stricter than it should be.

The second kind happened here. Sol and Astra put Steam (a game store) in Shopping, said so in their answers, and were
marked wrong. The failure causes named the same entry, line 16 "June 4: Steam, 47.58", in every one of those runs. The
key now accepts Steam in Shopping, and both models pass every check.

The loader proves the ledger and `expected_facts.json` agree under every accepted policy, so the two cannot drift apart.

## Reading the results

```
results/
  pwi/expense_analysis/            runs of the PWI library (the command and the pytest gate)
    <timestamp>-<label>-<assistant>-<model>-<effort>-<id>/
      scorecard.md                 the report: pass-rate table, check descriptions, failure causes, every failing run
      scorecard.json               the same data as JSON
      regraded_from.txt            for a regrade: the run whose recorded trials were graded again
      trials/<variant>/<case>/run-NN/
        answer.md                  the model's final answer
        event_stream.jsonl         the raw session: every message, tool call and tool result
        grade.json                 extracted facts, every check outcome with its reason, and traced diagnoses
  minimal/expense_analysis/        runs of the one-file eval (none kept yet)
```

Start with `scorecard.md`, then open `answer.md` for any failing run it names. `event_stream.jsonl` shows exactly
what the model did, including the Python it ran.

Every folder here is a **regrade** (`-regrade-` in its name): the trials were recorded once, on 2026-10-08 and
2026-10-09, and graded again on 2026-10-10 against the current reference key, without running the models again. Older
gradings were removed so that only results under the current key remain. In the recorded sessions, the local Windows
user name in temporary paths is replaced with `<user>`.

| Run folder | Model | Prompt variants | Runs |
|---|---|---|---|
| `20261010T105946Z-regrade-claude_code-claude-opus-5-5-medium-c0bed1` | Opus 5.5 | robust-tables-first | 1 |
| `20261010T110008Z-regrade-claude_code-claude-opus-5-5-medium-0b6fd3` | Opus 5.5 | robust-tables-first | 4 |
| `20261010T105946Z-regrade-codex-gpt-6.1-sol-medium-83daba` | GPT-6.1 Sol | robust-tables-first | 1 |
| `20261010T110007Z-regrade-codex-gpt-6.1-sol-medium-86e1d4` | GPT-6.1 Sol | robust-tables-first | 4 |
| `20261010T110051Z-regrade-codex-gpt-6-astra-medium-d55b00` | GPT-6 Astra | robust-tables-first | 5 |
| `20261010T110057Z-regrade-claude_code-claude-sonnet-5-5-medium-1892c7` | Sonnet 5.5 | robust-tables-first | 5 |
| `20261010T110145Z-regrade-claude_code-claude-haiku-5-5-medium-cd428f` | Haiku 5.5 | robust-tables-first | 5 |
| `20261010T110135Z-regrade-codex-gpt-6-luna-medium-43f5c3` | GPT-6 Luna | robust-tables-first | 5 |
| `20261010T112320Z-regrade-claude_code-claude-opus-5-5-medium-d5f700` | Opus 5.5 | standard, robust | 5 each |
| `20261010T112458Z-regrade-claude_code-claude-sonnet-5-5-medium-e976c6` | Sonnet 5.5 | standard, robust | 5 each |
| `20261010T112320Z-regrade-claude_code-sonnet-medium-477ac8` | Sonnet (alias) | standard, robust | 1 each |
| `20261010T112349Z-regrade-claude_code-sonnet-medium-15a95e` | Sonnet (alias) | standard, robust | 1 each |
| `20261010T112419Z-regrade-claude_code-claude-opus-5-5-medium-ccfc44` | Opus 5.5 | robust-tables-first (earlier runs) | 1 |
| `20261010T112630Z-regrade-claude_code-claude-opus-5-5-medium-39a815` | Opus 5.5 | robust-tables-first (earlier runs) | 4 |

The last two hold Opus's first `robust-tables-first` runs, recorded while that prompt was still being refined; three of
those five runs pass `three-supported-findings`. The comparison table above uses the later five.

## Running the evals yourself

### Prerequisites

- **Python 3.14** and **[uv](https://docs.astral.sh/uv/)**. uv creates the virtual environment and installs everything.
- **Claude Code** (`claude` on your PATH), signed in. Trials and graders run as `claude -p` sessions on your Claude
  subscription. If `ANTHROPIC_API_KEY` is set, `claude -p` uses it instead and bills per token.
- **Optional: the OpenAI Codex CLI** (`codex`, signed in with `codex login`) to run trials on GPT models.

The harness was built and run on Windows (it contains child processes with a Windows Job Object there). The commands
below are PowerShell; in a POSIX shell, use forward slashes in paths.

### Setup and harness tests

```powershell
uv sync --all-packages --all-groups --cache-dir .\.uv-cache
uv run --cache-dir .\.uv-cache pytest -q
```

The 115 harness tests run in seconds and call no model.

### Run the eval

```powershell
# All three prompt variants, 5 isolated runs each, trials on Claude Sonnet.
# Writes results\pwi\expense_analysis\<timestamp>-claude_code-sonnet-medium-<id>\
uv run --cache-dir .\.uv-cache prompt_evals_app evals\expense_analysis --model sonnet --effort medium --repetitions 5

# Only the gated prompt
uv run --cache-dir .\.uv-cache prompt_evals_app evals\expense_analysis --variant robust-tables-first --model claude-opus-5-5 --repetitions 5

# The same eval as a pytest gate (the test fails if any gated check is below its minimum pass rate)
uv run --cache-dir .\.uv-cache pytest evals/expense_analysis -s --eval-model sonnet --eval-effort medium --eval-repetitions 5

# The minimal one-file version (Claude Code only); writes results\minimal\expense_analysis\
uv run --cache-dir .\.uv-cache pytest evals/minimal -s --eval-model sonnet --eval-effort medium --eval-repetitions 5
```

The command exits with 0 when the gate passes, 1 when it fails, 2 for invalid input and 3 when the environment fails.
Each trial takes one to two minutes; trials run two at a time and graders three at a time by default.

### Run the trials in Codex

The same eval suite runs unchanged in the OpenAI Codex CLI. Pass `--assistant codex` (or `--eval-assistant codex` for
the pytest gate) and a Codex model:

```powershell
uv run --cache-dir .\.uv-cache prompt_evals_app evals\expense_analysis --assistant codex --model gpt-6.1-sol --effort medium --repetitions 5
```

Each trial is one isolated `codex exec --json --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check`
run in a fresh folder that holds only the case's inputs. Graders keep running in Claude Code, so grading stays the
same whichever assistant ran the trials. Codex reports tokens, not cost, so a Codex trial records no cost.

### Grade an earlier run again

After you change the reference key or a rubric, grade recorded trials again without rerunning any model. The regrade
reads the model, effort and assistant from the run's `scorecard.json` and writes a new run folder:

```powershell
uv run --cache-dir .\.uv-cache prompt_evals_app evals\expense_analysis --regrade results\pwi\expense_analysis\<run folder>
```

Runs recorded before the scorecard named its assistant need `--assistant codex` when their trials ran in Codex.

### Compare a new model

Run the gated variant on the new model, then compare its `scorecard.md` with the ones here. If a check drops below its
minimum, start with the scorecard's **Failure causes**, then read the failing answers. Fix the prompt, or, if the
cause is a reasonable choice the key rejects, the key.

### Settings

Environment variables, all optional. A variable set to an empty value is rejected rather than ignored.

| Variable | Default |
|---|---|
| `PROMPT_EVALS_CLAUDE_EXECUTABLE` | `claude` |
| `PROMPT_EVALS_CODEX_EXECUTABLE` | `codex` |
| `PROMPT_EVALS_SESSION_TIMEOUT_SECONDS` | `900` |
| `PROMPT_EVALS_MAXIMUM_CONCURRENT_TRIALS` | `2` |
| `PROMPT_EVALS_GRADER_ASSISTANT` | `claude_code` |
| `PROMPT_EVALS_GRADER_MODEL` | `sonnet` |
| `PROMPT_EVALS_GRADER_EFFORT` | `low` |
| `PROMPT_EVALS_MAXIMUM_CONCURRENT_GRADINGS` | `3` |

## Two versions of the same eval

Both read the same eval suite folder, `evals/expense_analysis/`, so they evaluate exactly the same thing.

| | Where | What it shows |
|---|---|---|
| **Minimal** | `evals/minimal/test_expense_analysis_minimal_eval.py` | How an eval works: one file, read top to bottom. Arrange reads the eval suite, Act runs `claude -p`, Assert grades, traces failures and checks pass rates. |
| **PWI library** | `packages/prompt-evals` + `apps/prompt-evals-app` | The same logic built as a reusable, tested tool following PWI: facade, manager, engines, gateways, and its own test suite. Adds Codex support, concurrency, artifacts, regrading and validation. |

Start with the minimal file. Everything in the library exists in it in some form.

### The eval suite is data

`evals/expense_analysis/` holds everything the eval needs:

- `prompts/*.md`: the prompt variants.
- `cases/june_august_2026/inputs/`: the expense log and budget notes the model receives.
- `cases/june_august_2026/expense_reference_key.md`: the reference key itself, for people: conventions, monthly totals, budget
  comparisons, the alternative policies it accepts, and how to grade. Its links point to the author's private copies of
  the inputs and its calculation package, which are not part of this repository; the inputs are in `inputs/`.
- `cases/june_august_2026/expected_facts.json`: the reference key's answers. Each fact lists every value the key accepts.
- `cases/june_august_2026/reference_ledger.json`: the same key, entry by entry, used to explain wrong totals (optional for other suites).
- `grading/fact_extraction_*.{md,json}`: what the extractor model reads out of each answer.
- `grading/rubrics/*.md`: what the judge model applies.
- `eval_suite.json`: wires it together: variants, the gated variant, cases, and checks with their graders and minimum pass rates.

To evaluate a new prompt, add a folder like this one. No code changes are needed unless you need a new kind of grader.

## Layout and tooling

- `packages/prompt-evals`: the library. `DomainFacade` → `ManagerEvaluation` → engines (trial execution, trial
  grading) → processors and LLM processors → `GatewayLlmClaudeCli` or `GatewayLlmCodexCli` → process runner.
- `apps/prompt-evals-app`: the command-line host. It parses arguments, calls the facade, and writes artifacts to `results/pwi/`.
- `evals/`: eval suites and their pytest gates.
- `results/`: recorded runs, as described above.

```powershell
uv sync --all-packages --all-groups --cache-dir .\.uv-cache
uv run --all-packages --all-groups --cache-dir .\.uv-cache ruff check --no-cache packages apps evals
uv run --all-packages --all-groups --cache-dir .\.uv-cache ruff format --check --no-cache packages apps evals
uv run --all-packages --all-groups --cache-dir .\.uv-cache pyright
uv run --all-packages --all-groups --cache-dir .\.uv-cache pytest -q
```

Run ruff on `packages apps evals` only. Run against the whole folder, it would also reformat the uv cache and `.venv`.
