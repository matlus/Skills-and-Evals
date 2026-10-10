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
| both-delta-charges-kept | 80% | 1/1 (100%) | 1/1 (100%) |
| travel-august-total | 80% | 1/1 (100%) | 1/1 (100%) |
| uncategorized-entry-count | 80% | 0/1 (0%) | 1/1 (100%) |
| largest-increase-is-travel | 80% | 1/1 (100%) | 1/1 (100%) |
| code-executed | 80% | 1/1 (100%) | 1/1 (100%) |
| ambiguous-entries-not-forced | 80% | 1/1 (100%) | 1/1 (100%) |
| tables-before-interpretation | 80% | 0/1 (0%) | 0/1 (0%) |
| three-supported-findings | 80% | 0/1 (0%) | 1/1 (100%) |
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

## Runs that did not pass

### uncategorized-entry-count · standard

- june-august-2026/run-01: [failed] reported nothing; expected 8

### tables-before-interpretation · standard

- june-august-2026/run-01: [failed] The answer opens with conclusions ("Your quarter came to $11,812.80... Dining went over your $260 budget in August, and shopping came in just over $1,200") before the tables. That is more than a brief framing sentence, so the tables don't come first.

### tables-before-interpretation · robust

- june-august-2026/run-01: [failed] The answer opens with conclusions ("August is the outlier, mostly because of a trip", one duplicate found) and puts parsing, uncategorized and duplicate notes before the computed tables in section 4. The tables come before the "Three things to know" section, but the opening statements already give findings ahead of any table, which is more than brief framing.

### three-supported-findings · standard

- june-august-2026/run-01: [failed] Finding 3 says groceries and gas "together added about $690 a month between June and August," but the answer's tables show about $652 total over the period (+$358.45 groceries, +$293.36 gas), or about $326 a month. It also claims these grew faster than anything else, though travel grew more.

