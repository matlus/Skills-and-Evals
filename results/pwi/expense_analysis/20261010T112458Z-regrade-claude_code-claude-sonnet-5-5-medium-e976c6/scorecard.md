# Scorecard: expense-analysis

Assistant: `claude_code` · Model: `claude-sonnet-5-5` · Effort: `medium` · Repetitions per case: 5 · Gate: **NOT EVALUATED (no gated variant was run)**

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
| travel-august-total | 80% | 3/5 (60%) | 5/5 (100%) |
| uncategorized-entry-count | 80% | 0/5 (0%) | 5/5 (100%) |
| largest-increase-is-travel | 80% | 2/5 (40%) | 5/5 (100%) |
| code-executed | 80% | 5/5 (100%) | 5/5 (100%) |
| ambiguous-entries-not-forced | 80% | 5/5 (100%) | 5/5 (100%) |
| tables-before-interpretation | 80% | 3/5 (60%) | 1/5 (20%) |
| three-supported-findings | 80% | 2/5 (40%) | 5/5 (100%) |
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

- **Travel 2026-08 (under the accepted policy 'August 16 Uber in Transport'): left out line 169 "Airport Parking - $68.00 (August 14)"** · 4 checks: standard / june-august-2026/run-02 / travel-august-total; standard / june-august-2026/run-02 / three-supported-findings; standard / june-august-2026/run-05 / travel-august-total; standard / june-august-2026/run-05 / three-supported-findings

## Runs that did not pass

### travel-august-total · standard

- june-august-2026/run-02: [failed] reported 1563.82; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).
- june-august-2026/run-05: [failed] reported 1563.82; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).

### uncategorized-entry-count · standard

- june-august-2026/run-01: [failed] reported nothing; expected 8
- june-august-2026/run-02: [failed] reported nothing; expected 8
- june-august-2026/run-03: [failed] reported 0; expected 8
- june-august-2026/run-04: [failed] reported nothing; expected 8
- june-august-2026/run-05: [failed] reported nothing; expected 8

### largest-increase-is-travel · standard

- june-august-2026/run-01: [failed] reported nothing; expected travel
- june-august-2026/run-02: [failed] reported nothing; expected travel
- june-august-2026/run-05: [failed] reported Shopping; expected travel

### tables-before-interpretation · standard

- june-august-2026/run-03: [failed] The answer opens with a framing sentence that also flags that three entries need input, but then shows both tables (monthly totals by category and the budget comparison) before any interpretation or findings. The trends and "three things to know" sections come after the tables, so the ordering requirement is met. However, the verdict should be PASS.
- june-august-2026/run-04: [failed] The answer opens with conclusions ("August was by far your biggest month, and dining is the budget that got away from you") before the tables. That is more than a brief one-line framing sentence, so it leads with a finding.

### tables-before-interpretation · robust

- june-august-2026/run-01: [failed] The answer puts parsing notes, categorization flags, duplicate and refund findings (sections 1–3) before the tables in section 4. Those sections are interpretation and findings, not brief framing sentences, so the tables don't come first.
- june-august-2026/run-03: [failed] The answer puts a long "Cleaning results" section (duplicates, refund, uncategorized items, category judgment calls) before the tables. That section includes interpretive claims, such as the Delta duplicate possibly overstating August. The monthly totals and budget comparison tables only appear afterward, and the three key findings come after them. The tables are therefore not presented first, and a brief framing line would not cover this much material.
- june-august-2026/run-04: [failed] The answer puts its parsing notes, category judgment calls, duplicate/refund discussion and flags (sections 1–3) before the computed tables, which don't appear until section 4. Those sections are interpretive content rather than brief one-line framing, so the tables are not presented first. The "three things" findings do come after the tables.
- june-august-2026/run-05: [failed] The answer opens with a conclusion ("August is the main story, because it cost almost twice as much as the other two months"). It then covers parsing, categories and duplicates before the computed tables in section 4. The tables come before the "Three things" findings, but the opening already states a finding, and the tables are not presented first with only brief framing.

### three-supported-findings · standard

- june-august-2026/run-01: [failed] Finding 1 says the trip "explains less than half" of August's spike. The answer's own tables contradict this: August rose about $2,756 over July ($5,646 vs $2,890), and the $1,632 trip is about 59% of that. The "about $700 a month" for groceries plus gas is also loose, since the tables give roughly $650.
- june-august-2026/run-02: [failed] The answer gives exactly three findings, and its dining and shopping figures match the reference. But it puts August travel at $1,563.82 and calls the trip "$1,564". The reference gives $1,655.92, or $1,631.82 if the Uber is counted as transport, and the answer's figure is lower than both. It also puts the $68 airport parking in transport, outside travel. Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).
- june-august-2026/run-05: [failed] The answer gives August travel as $1,563.82, but the reference is $1,655.92 (or $1,631.82 with the 8/16 Uber counted as transport). It repeats the figure in finding 1 ("the trip... was $1,564"). Its other figures (dining, shopping, the $11,812.80 total) match the reference. Likely cause: Travel 2026-08: reported 1,563.82, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -68.00. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00).

