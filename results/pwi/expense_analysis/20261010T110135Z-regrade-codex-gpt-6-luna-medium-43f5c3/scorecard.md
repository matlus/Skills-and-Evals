# Scorecard: expense-analysis

Assistant: `codex` · Model: `gpt-6-luna` · Effort: `medium` · Repetitions per case: 5 · Gate: **FAILED**

Gated variants must reach each check's minimum pass rate. Other variants are measured for comparison only.

| Check | Minimum | robust-tables-first (gated) |
|---|---|---|
| dining-june-total | 80% | ❌ 2/5 (40%) |
| dining-july-total | 80% | ✅ 5/5 (100%) |
| dining-august-total | 80% | ✅ 5/5 (100%) |
| dining-august-over-budget | 80% | ✅ 5/5 (100%) |
| refund-netted | 80% | ✅ 5/5 (100%) |
| shopping-july-total | 80% | ❌ 0/5 (0%) |
| duplicate-flagged | 80% | ✅ 5/5 (100%) |
| both-delta-charges-kept | 80% | ❌ 2/5 (40%) |
| travel-august-total | 80% | ❌ 0/5 (0%) |
| uncategorized-entry-count | 80% | ✅ 4/5 (80%) |
| largest-increase-is-travel | 80% | ❌ 2/5 (40%) |
| code-executed | 80% | ✅ 5/5 (100%) |
| ambiguous-entries-not-forced | 80% | ✅ 5/5 (100%) |
| tables-before-interpretation | 80% | ✅ 5/5 (100%) |
| three-supported-findings | 80% | ❌ 0/5 (0%) |
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

- **Shopping 2026-07: no combination of up to 3 entries explains the difference** · 6 checks: robust-tables-first / june-august-2026/run-01 / shopping-july-total; robust-tables-first / june-august-2026/run-01 / three-supported-findings; robust-tables-first / june-august-2026/run-03 / shopping-july-total; robust-tables-first / june-august-2026/run-04 / shopping-july-total; robust-tables-first / june-august-2026/run-04 / three-supported-findings; robust-tables-first / june-august-2026/run-05 / shopping-july-total
- **Travel 2026-08: no combination of up to 3 entries explains the difference** · 6 checks: robust-tables-first / june-august-2026/run-01 / travel-august-total; robust-tables-first / june-august-2026/run-03 / travel-august-total; robust-tables-first / june-august-2026/run-03 / three-supported-findings; robust-tables-first / june-august-2026/run-04 / travel-august-total; robust-tables-first / june-august-2026/run-05 / travel-august-total; robust-tables-first / june-august-2026/run-05 / three-supported-findings
- **Dining and coffee 2026-06: counted line 55 "6/24/26 Bowl-O-Rama 9.25", which the reference puts in Entertainment** · 4 checks: robust-tables-first / june-august-2026/run-03 / dining-june-total; robust-tables-first / june-august-2026/run-03 / three-supported-findings; robust-tables-first / june-august-2026/run-04 / dining-june-total; robust-tables-first / june-august-2026/run-04 / three-supported-findings
- **Dining and coffee 2026-06: left out line 31 "Local Coffee Co - 34.22 (2026-06-12)"** · 2 checks: robust-tables-first / june-august-2026/run-01 / dining-june-total; robust-tables-first / june-august-2026/run-01 / three-supported-findings
- **Travel 2026-08 (under the accepted policy 'August 16 Uber in Transport'): left out line 169 "Airport Parking - $68.00 (August 14)"; left out line 171 "Hertz Rental Car - 214.35 (8/15/26)"** · 2 checks: robust-tables-first / june-august-2026/run-02 / travel-august-total; robust-tables-first / june-august-2026/run-02 / three-supported-findings
- **Shopping 2026-08 (under the accepted policy 'Barnes & Noble in Shopping'): counted line 166 "Walgreens - $13.77 (08-14)", which the reference puts in Health and fitness** · 2 checks: robust-tables-first / june-august-2026/run-02 / three-supported-findings; robust-tables-first / june-august-2026/run-04 / three-supported-findings
- **Shopping 2026-06 (under the accepted policy 'Barnes & Noble in Shopping'): counted line 63 "Walgreens, 6/28 -- $92.54", which the reference puts in Health and fitness** · 2 checks: robust-tables-first / june-august-2026/run-02 / three-supported-findings; robust-tables-first / june-august-2026/run-04 / three-supported-findings
- **Shopping 2026-06 (under the accepted policy 'Barnes & Noble in Shopping'): counted line 6 "June 1 Amazon Prime $14.99", which the reference puts in Subscriptions; counted line 63 "Walgreens, 6/28 -- $92.54", which the reference puts in Health and fitness** · 1 check: robust-tables-first / june-august-2026/run-01 / three-supported-findings
- **Shopping 2026-08 (under the accepted policy 'Barnes & Noble in Shopping'): counted line 128 "Amazon Prime (08-03) - $14.99", which the reference puts in Subscriptions; counted line 166 "Walgreens - $13.77 (08-14)", which the reference puts in Health and fitness** · 1 check: robust-tables-first / june-august-2026/run-01 / three-supported-findings
- **Shopping 2026-07: counted line 86 "- Jul 7 CVS Pharmacy $26.14", which the reference puts in Health and fitness; counted line 119 "- 7/31 Walgreens $45.96", which the reference puts in Health and fitness** · 1 check: robust-tables-first / june-august-2026/run-02 / shopping-july-total
- **Shopping 2026-06: no combination of up to 3 entries explains the difference** · 1 check: robust-tables-first / june-august-2026/run-03 / three-supported-findings
- **Shopping 2026-08: no combination of up to 3 entries explains the difference** · 1 check: robust-tables-first / june-august-2026/run-03 / three-supported-findings

## Runs that did not pass

### dining-june-total · robust-tables-first

- june-august-2026/run-01: [failed] reported 178.52; expected 212.74 Likely cause: Dining and coffee 2026-06: reported 178.52, reference 212.74, a difference of -34.22. Explained by: left out line 31 "Local Coffee Co - 34.22 (2026-06-12)" (-34.22).
- june-august-2026/run-03: [failed] reported 221.99; expected 212.74 Likely cause: Dining and coffee 2026-06: reported 221.99, reference 212.74, a difference of +9.25. Explained by: counted line 55 "6/24/26 Bowl-O-Rama 9.25" (+9.25), which the reference puts in Entertainment.
- june-august-2026/run-04: [failed] reported 221.99; expected 212.74 Likely cause: Dining and coffee 2026-06: reported 221.99, reference 212.74, a difference of +9.25. Explained by: counted line 55 "6/24/26 Bowl-O-Rama 9.25" (+9.25), which the reference puts in Entertainment.

### shopping-july-total · robust-tables-first

- june-august-2026/run-01: [failed] reported 843.81; expected 756.72 Likely cause: Shopping 2026-07: reported 843.81, reference 756.72, a difference of +87.09 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-02: [failed] reported 828.82; expected 756.72 Likely cause: Shopping 2026-07: reported 828.82, reference 756.72, a difference of +72.10. Explained by: counted line 86 "- Jul 7 CVS Pharmacy $26.14" (+26.14), which the reference puts in Health and fitness and counted line 119 "- 7/31 Walgreens $45.96" (+45.96), which the reference puts in Health and fitness.
- june-august-2026/run-03: [failed] reported 996.34; expected 756.72 Likely cause: Shopping 2026-07: reported 996.34, reference 756.72, a difference of +239.62 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-04: [failed] reported 964.82; expected 756.72 Likely cause: Shopping 2026-07: reported 964.82, reference 756.72, a difference of +208.10 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-05: [failed] reported 907.22; expected 756.72 Likely cause: Shopping 2026-07: reported 907.22, reference 756.72, a difference of +150.50 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).

### both-delta-charges-kept · robust-tables-first

- june-august-2026/run-02: [failed] reported nothing; expected true
- june-august-2026/run-03: [failed] reported nothing; expected true
- june-august-2026/run-05: [failed] reported nothing; expected true

### travel-august-total · robust-tables-first

- june-august-2026/run-01: [failed] reported 2131.45; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 2,131.45, reference 1,655.92, a difference of +475.53 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-02: [failed] reported 1349.47; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,349.47, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -282.35. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00) and left out line 171 "Hertz Rental Car - 214.35 (8/15/26)" (-214.35).
- june-august-2026/run-03: [failed] reported 1767.41; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,767.41, reference 1,655.92, a difference of +111.49 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-04: [failed] reported 2194.40; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 2,194.40, reference 1,655.92, a difference of +538.48 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-05: [failed] reported 1767.41; expected 1655.92 or 1631.82 Likely cause: Travel 2026-08: reported 1,767.41, reference 1,655.92, a difference of +111.49 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).

### uncategorized-entry-count · robust-tables-first

- june-august-2026/run-05: [failed] reported 7; expected 8

### largest-increase-is-travel · robust-tables-first

- june-august-2026/run-01: [failed] reported Transport / travel; expected travel
- june-august-2026/run-03: [failed] reported Transport: parking/travel; expected travel
- june-august-2026/run-04: [failed] reported Transport / travel; expected travel

### three-supported-findings · robust-tables-first

- june-august-2026/run-01: [failed] The answer's figures contradict the reference values. June dining is $178.52 against a reference of $212.74. Shopping is $1,128.30 / $843.81 / $1,247.07 against references of $960.07–$1,068.35 for June, $756.72 for July, and $1,061.93–$1,218.31 for August. Its finding that August shopping is $47.07 over target also conflicts with the references (at most $18.31 over, or under target). Likely cause: Dining and coffee 2026-06: reported 178.52, reference 212.74, a difference of -34.22. Explained by: left out line 31 "Local Coffee Co - 34.22 (2026-06-12)" (-34.22). Likely cause: Shopping 2026-06: reported 1,128.30, reference 1,020.77 (under the accepted policy 'Barnes & Noble in Shopping'), a difference of +107.53. Explained by: counted line 6 "June 1 Amazon Prime $14.99" (+14.99), which the reference puts in Subscriptions and counted line 63 "Walgreens, 6/28 -- $92.54" (+92.54), which the reference puts in Health and fitness. Likely cause: Shopping 2026-07: reported 843.81, reference 756.72, a difference of +87.09 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error). Likely cause: Shopping 2026-08: reported 1,247.07, reference 1,218.31 (under the accepted policy 'Barnes & Noble in Shopping'), a difference of +28.76. Explained by: counted line 128 "Amazon Prime (08-03) - $14.99" (+14.99), which the reference puts in Subscriptions and counted line 166 "Walgreens - $13.77 (08-14)" (+13.77), which the reference puts in Health and fitness.
- june-august-2026/run-02: [failed] The answer gives exactly three findings. Its Travel figure for August ($1,349.47) contradicts the reference ($1,655.92, or $1,631.82 with the Uber counted as transport). Its Shopping figures also match no reference policy. August is $1,232.08 against a reference of $1,061.93 or $1,218.31, and June is $1,113.31 against $960.07, $1,020.77, $1,007.65 or $1,068.35. Likely cause: Travel 2026-08: reported 1,349.47, reference 1,631.82 (under the accepted policy 'August 16 Uber in Transport'), a difference of -282.35. Explained by: left out line 169 "Airport Parking - $68.00 (August 14)" (-68.00) and left out line 171 "Hertz Rental Car - 214.35 (8/15/26)" (-214.35). Likely cause: Shopping 2026-08: reported 1,232.08, reference 1,218.31 (under the accepted policy 'Barnes & Noble in Shopping'), a difference of +13.77. Explained by: counted line 166 "Walgreens - $13.77 (08-14)" (+13.77), which the reference puts in Health and fitness. Likely cause: Shopping 2026-06: reported 1,113.31, reference 1,020.77 (under the accepted policy 'Barnes & Noble in Shopping'), a difference of +92.54. Explained by: counted line 63 "Walgreens, 6/28 -- $92.54" (+92.54), which the reference puts in Health and fitness.
- june-august-2026/run-03: [failed] The answer's figures contradict the reference values. June dining is $221.99 against $212.74. Shopping is $1,232.66 in June and $1,638.99 in August, so it claims shopping was over target in June and by $438.99 in August. Under either policy June shopping is under target and August is at most $18.31 over. Likely cause: Dining and coffee 2026-06: reported 221.99, reference 212.74, a difference of +9.25. Explained by: counted line 55 "6/24/26 Bowl-O-Rama 9.25" (+9.25), which the reference puts in Entertainment. Likely cause: Shopping 2026-06: reported 1,232.66, reference 960.07, a difference of +272.59 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error). Likely cause: Shopping 2026-08: reported 1,638.99, reference 1,061.93, a difference of +577.06 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error). Likely cause: Travel 2026-08: reported 1,767.41, reference 1,655.92, a difference of +111.49 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).
- june-august-2026/run-04: [failed] The answer has three findings, but its numbers contradict the reference. June dining is $221.99 against a reference of $212.74. Shopping is $1,113.31, $964.82 and $1,232.08, and no reference policy gives those. Its claim that August shopping is $32.08 over target also conflicts with the reference, which says shopping is under target or at most $18.31 over. Likely cause: Dining and coffee 2026-06: reported 221.99, reference 212.74, a difference of +9.25. Explained by: counted line 55 "6/24/26 Bowl-O-Rama 9.25" (+9.25), which the reference puts in Entertainment. Likely cause: Shopping 2026-07: reported 964.82, reference 756.72, a difference of +208.10 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error). Likely cause: Shopping 2026-06: reported 1,113.31, reference 1,020.77 (under the accepted policy 'Barnes & Noble in Shopping'), a difference of +92.54. Explained by: counted line 63 "Walgreens, 6/28 -- $92.54" (+92.54), which the reference puts in Health and fitness. Likely cause: Shopping 2026-08: reported 1,232.08, reference 1,218.31 (under the accepted policy 'Barnes & Noble in Shopping'), a difference of +13.77. Explained by: counted line 166 "Walgreens - $13.77 (08-14)" (+13.77), which the reference puts in Health and fitness.
- june-august-2026/run-05: [failed] The Travel finding says July was $99.08 and August was $1,767.41, with a $1,668.33 increase. The reference has Travel at $0 in July and $1,655.92 in August ($1,631.82 if the Uber is counted as transport). The answer's Travel category (June $327.78) also contradicts the reference's $0 for June. Likely cause: Travel 2026-08: reported 1,767.41, reference 1,655.92, a difference of +111.49 that no combination of up to 3 entries explains (a broader categorization difference or an arithmetic error).

