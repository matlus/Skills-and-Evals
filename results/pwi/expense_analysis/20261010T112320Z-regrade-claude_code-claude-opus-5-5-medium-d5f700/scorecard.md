# Scorecard: expense-analysis

Assistant: `claude_code` · Model: `claude-opus-5-5` · Effort: `medium` · Repetitions per case: 5 · Gate: **NOT EVALUATED (no gated variant was run)**

Gated variants must reach each check's minimum pass rate. Other variants are measured for comparison only.

| Check | Minimum | standard | robust |
|---|---|---|---|
| dining-june-total | 80% | 5/5 (100%) | 5/5 (100%) |
| dining-july-total | 80% | 5/5 (100%) | 5/5 (100%) |
| dining-august-total | 80% | 5/5 (100%) | 5/5 (100%) |
| dining-august-over-budget | 80% | 5/5 (100%) | 5/5 (100%) |
| refund-netted | 80% | 5/5 (100%) | 5/5 (100%) |
| shopping-july-total | 80% | 5/5 (100%) | 5/5 (100%) |
| duplicate-flagged | 80% | 5/5 (100%) | 5/5 (100%) |
| both-delta-charges-kept | 80% | 5/5 (100%) | 5/5 (100%) |
| travel-august-total | 80% | 4/5 (80%) | 5/5 (100%) |
| uncategorized-entry-count | 80% | 0/5 (0%) | 5/5 (100%) |
| largest-increase-is-travel | 80% | 2/5 (40%) | 5/5 (100%) |
| code-executed | 80% | 5/5 (100%) | 5/5 (100%) |
| ambiguous-entries-not-forced | 80% | 5/5 (100%) | 5/5 (100%) |
| tables-before-interpretation | 80% | 5/5 (100%) | 0/5 (0%) |
| three-supported-findings | 80% | 3/5 (60%) | 5/5 (100%) |
| no-invented-budgets | 80% | 5/5 (100%) | 5/5 (100%) |

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

- **Travel 2026-08 (under the accepted policy 'August 16 Uber in Transport'): left out line 169 "Airport Parking - $68.00 (August 14)"** · 2 checks: standard / june-august-2026/run-02 / travel-august-total; standard / june-august-2026/run-02 / three-supported-findings

## Runs that did not pass

### travel-august-total · standard

- june-august-2026/run-02: [failed] reported 1563.82; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).

### uncategorized-entry-count · standard

- june-august-2026/run-01: [failed] reported nothing; expected 8
- june-august-2026/run-02: [failed] reported nothing; expected 8
- june-august-2026/run-03: [failed] reported nothing; expected 8
- june-august-2026/run-04: [failed] reported nothing; expected 8
- june-august-2026/run-05: [failed] reported nothing; expected 8

### largest-increase-is-travel · standard

- june-august-2026/run-01: [failed] reported nothing; expected travel
- june-august-2026/run-02: [failed] reported nothing; expected travel
- june-august-2026/run-05: [failed] reported nothing; expected travel

### tables-before-interpretation · robust

- june-august-2026/run-01: [failed] The answer opens with conclusions in its summary paragraph: August was about double July's, the trip explains most of the jump, eating out went over budget, and gas and groceries are rising. The tables only come later, and the three key findings come after them.
- june-august-2026/run-02: [failed] The answer opens with summary conclusions ("August went over both budgets", counts of transactions) before the tables. That is a finding stated ahead of the tables, and it is more than a brief framing sentence. The tables come next, followed by the interpretation.
- june-august-2026/run-03: [failed] The answer opens with conclusions ("You went over both budgets in August. Eating out was 53% over...") before any tables, and the tables only come after data-cleaning prose. That is more than a brief framing line, so it fails the tables-first requirement.
- june-august-2026/run-04: [failed] The answer opens with conclusions ("Eating out went over budget in August, and shopping was just over too", duplicates, refund, uncategorised total). It then gives a long data-cleaning discussion before the monthly totals and budget tables. That is more than a brief framing line, so the tables don't come first.
- june-august-2026/run-05: [failed] The answer opens with conclusions ("eating-out total hit your target at 99.6%, August 53% over", shopping findings) and places the computed tables in section 4, with the key findings after. Its opening paragraph and sections 1–3 are not brief framing for the tables. They are findings and caveats that come before the tables.

### three-supported-findings · standard

- june-august-2026/run-02: [failed] The answer gives August travel as $1,563.82, which matches neither reference value ($1,655.92, or $1,631.82 with the Uber counted as transport). Its three findings are otherwise consistent with the reference facts. Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).
- june-august-2026/run-05: [failed] Finding 3 says groceries and gas "make up most of the $1,180 jump in non-travel spending in August". The answer's own table shows groceries rose about $154 (829→983) and gas about $152 (275→427) from July. That is about $306, roughly 26% of the $1,179 jump, not most of it. The dining, shopping and total figures match the reference.

