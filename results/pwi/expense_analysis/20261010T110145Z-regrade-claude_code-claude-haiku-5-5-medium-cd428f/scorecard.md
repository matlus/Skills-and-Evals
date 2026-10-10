# Scorecard: expense-analysis

Assistant: `claude_code` · Model: `claude-haiku-5-5` · Effort: `medium` · Repetitions per case: 5 · Gate: **FAILED**

Gated variants must reach each check's minimum pass rate. Other variants are measured for comparison only.

| Check | Minimum | robust-tables-first (gated) |
|---|---|---|
| dining-june-total | 80% | ✅ 5/5 (100%) |
| dining-july-total | 80% | ✅ 5/5 (100%) |
| dining-august-total | 80% | ✅ 5/5 (100%) |
| dining-august-over-budget | 80% | ✅ 5/5 (100%) |
| refund-netted | 80% | ✅ 5/5 (100%) |
| shopping-july-total | 80% | ✅ 4/5 (80%) |
| duplicate-flagged | 80% | ✅ 5/5 (100%) |
| both-delta-charges-kept | 80% | ✅ 5/5 (100%) |
| travel-august-total | 80% | ❌ 3/5 (60%) |
| uncategorized-entry-count | 80% | ❌ 2/5 (40%) |
| largest-increase-is-travel | 80% | ✅ 4/5 (80%) |
| code-executed | 80% | ✅ 5/5 (100%) |
| ambiguous-entries-not-forced | 80% | ✅ 5/5 (100%) |
| tables-before-interpretation | 80% | ✅ 5/5 (100%) |
| three-supported-findings | 80% | ✅ 4/5 (80%) |
| no-invented-budgets | 80% | ✅ 5/5 (100%) |

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

- **Travel 2026-08 (under the accepted policy 'August 16 Uber in Transport'): left out line 169 "Airport Parking - $68.00 (August 14)"** · 2 checks: robust-tables-first / june-august-2026/run-05 / travel-august-total; robust-tables-first / june-august-2026/run-05 / three-supported-findings
- **Shopping 2026-07: left out line 71 "7/2/26 IKEA $92.60"; left out line 74 "- 2026-07-03 IKEA $16.89"; left out line 77 "Jul 6 | IKEA | $180.34"** · 1 check: robust-tables-first / june-august-2026/run-01 / shopping-july-total
- **Travel 2026-08: no combination of up to 3 entries explains the difference** · 1 check: robust-tables-first / june-august-2026/run-04 / travel-august-total

## Runs that did not pass

### shopping-july-total · robust-tables-first

- june-august-2026/run-01: [failed] reported 466.89; expected 756.72 Likely cause: Shopping 2026-07: reported 466.89, reference 756.72, a difference of -289.83. Explained by: left out line 71 "7/2/26 IKEA $92.60" (-92.60) and left out line 74 "- 2026-07-03 IKEA $16.89" (-16.89) and left out line 77 "Jul 6 | IKEA | $180.34" (-180.34).

### travel-august-total · robust-tables-first

- june-august-2026/run-04: [failed] reported 1767.41; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,767.41, reference 1,655.92, a difference of +111.49 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-05: [failed] reported 1563.82; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).

### uncategorized-entry-count · robust-tables-first

- june-august-2026/run-01: [failed] reported 6; expected 8
- june-august-2026/run-02: [failed] reported 6; expected 8
- june-august-2026/run-04: [failed] reported 7; expected 8

### largest-increase-is-travel · robust-tables-first

- june-august-2026/run-04: [failed] reported Transport & travel; expected travel

### three-supported-findings · robust-tables-first

- june-august-2026/run-05: [failed] The answer states August travel as $1,563.82, but the reference gives $1,655.92 (or $1,631.82 if the 8/16 Uber is counted as transport). Its dining and shopping figures and its total match the reference, and it has three findings. Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).

