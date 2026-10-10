# Scorecard: expense-analysis

Assistant: `claude_code` · Model: `sonnet` · Effort: `medium` · Repetitions per case: 1 · Gate: **NOT EVALUATED (no gated variant was run)**

Gated variants must reach each check's minimum pass rate. Other variants are measured for comparison only.

| Check | Minimum | standard | robust |
|---|---|---|---|
| dining-june-total | 80% | 1/1 (100%) | 1/1 (100%) |
| dining-july-total | 80% | 1/1 (100%) | 1/1 (100%) |
| dining-august-total | 80% | 1/1 (100%) | 1/1 (100%) |
| dining-august-over-budget | 80% | 1/1 (100%) | 1/1 (100%) |
| refund-netted | 80% | 1/1 (100%) | 1/1 (100%) |
| shopping-july-total | 80% | 1/1 (100%) | 1/1 (100%) |
| duplicate-flagged | 80% | 1/1 (100%) | 1/1 (100%) |
| both-delta-charges-kept | 80% | 1/1 (100%) | 0/1 (0%) |
| travel-august-total | 80% | 1/1 (100%) | 0/1 (0%) |
| uncategorized-entry-count | 80% | 0/1 (0%) | 1/1 (100%) |
| largest-increase-is-travel | 80% | 0/1 (0%) | 1/1 (100%) |
| code-executed | 80% | 1/1 (100%) | 1/1 (100%) |
| ambiguous-entries-not-forced | 80% | 1/1 (100%) | 1/1 (100%) |
| tables-before-interpretation | 80% | 1/1 (100%) | 1/1 (100%) |
| three-supported-findings | 80% | 1/1 (100%) | 0/1 (0%) |
| no-invented-budgets | 80% | 1/1 (100%) | 1/1 (100%) |

## Check descriptions

- **dining-june-total**: June dining & coffee total is $212.74.
- **dining-july-total**: July dining & coffee total is $165.14.
- **dining-august-total**: August dining & coffee total is $398.69.
- **dining-august-over-budget**: August dining is reported as over the $260 target.
- **refund-netted**: The -$68.00 REI refund reduces spending instead of adding to it.
- **shopping-july-total**: July shopping is $756.72, which is only true when the refund is netted.
- **duplicate-flagged**: The repeated Trader Joe's $54.12 entry on July 22 is flagged as a likely duplicate.
- **both-delta-charges-kept**: Both Delta charges ($412.60 and $450.60) are counted; neither is mistaken for a duplicate.
- **travel-august-total**: August travel is $1,655.92 (or $1,631.82 if the 8/16 Uber stays in transport).
- **uncategorized-entry-count**: All eight transfers and ATM withdrawals are left uncategorized.
- **largest-increase-is-travel**: Travel is identified as the largest July-to-August increase.
- **code-executed**: Totals were computed by running Python, not by mental arithmetic (read from the tool-call log).
- **ambiguous-entries-not-forced**: Transfers and ATM withdrawals are not forced into a spending category.
- **tables-before-interpretation**: Computed tables appear before the interpretation.
- **three-supported-findings**: Exactly three findings, each supported by the numbers.
- **no-invented-budgets**: Only the two stated budget targets are used.

## Failure causes

Wrong totals traced entry by entry in the case's reference ledger. One cause in several runs is a systematic mistake, or a reference key that is stricter than it should be.

- **Travel 2026-08 (under the accepted policy 'August 16 Uber in Transport'): left out line 168 "Delta Air Lines (8/14) - $450.60"** · 2 checks: robust / june-august-2026/run-01 / travel-august-total; robust / june-august-2026/run-01 / three-supported-findings

## Runs that did not pass

### both-delta-charges-kept · robust

- june-august-2026/run-01: [failed] reported false; expected true

### travel-august-total · robust

- june-august-2026/run-01: [failed] reported 1181.22; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,181.22, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -450.60. Explained by: left out line 168 "Delta Air Lines (8/14) - $450.60" (-450.60).

### uncategorized-entry-count · standard

- june-august-2026/run-01: [failed] reported nothing; expected 8

### largest-increase-is-travel · standard

- june-august-2026/run-01: [failed] reported nothing; expected travel

### three-supported-findings · robust

- june-august-2026/run-01: [failed] The answer's August Travel of $1,181.22 contradicts the reference $1,655.92 (or $1,631.82). It also drops a $450.60 Delta entry as a probable duplicate, which gives a cleaned total of $11,308.08 against the reference $11,758.68 or $11,812.80. Finding 1 builds on the understated Travel figure. Likely cause: Travel 2026-08: reported 1,181.22, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -450.60. Explained by: left out line 168 "Delta Air Lines (8/14) - $450.60" (-450.60).

