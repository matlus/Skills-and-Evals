# Scorecard: expense-analysis

Assistant: `codex` · Model: `gpt-6.1-sol` · Effort: `medium` · Repetitions per case: 4 · Gate: **PASSED**

Gated variants must reach each check's minimum pass rate. Other variants are measured for comparison only.

| Check | Minimum | robust-tables-first (gated) |
|---|---|---|
| dining-june-total | 80% | ✅ 4/4 (100%) |
| dining-july-total | 80% | ✅ 4/4 (100%) |
| dining-august-total | 80% | ✅ 4/4 (100%) |
| dining-august-over-budget | 80% | ✅ 4/4 (100%) |
| refund-netted | 80% | ✅ 4/4 (100%) |
| shopping-july-total | 80% | ✅ 4/4 (100%) |
| duplicate-flagged | 80% | ✅ 4/4 (100%) |
| both-delta-charges-kept | 80% | ✅ 4/4 (100%) |
| travel-august-total | 80% | ✅ 4/4 (100%) |
| uncategorized-entry-count | 80% | ✅ 4/4 (100%) |
| largest-increase-is-travel | 80% | ✅ 4/4 (100%) |
| code-executed | 80% | ✅ 4/4 (100%) |
| ambiguous-entries-not-forced | 80% | ✅ 4/4 (100%) |
| tables-before-interpretation | 80% | ✅ 4/4 (100%) |
| three-supported-findings | 80% | ✅ 4/4 (100%) |
| no-invented-budgets | 80% | ✅ 4/4 (100%) |

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

Every run passed every check.
