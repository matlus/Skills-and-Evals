# Scorecard: expense-analysis

Assistant: `claude_code` · Model: `claude-opus-5-5` · Effort: `medium` · Repetitions per case: 4 · Gate: **FAILED**

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
| three-supported-findings | 80% | ❌ 2/4 (50%) |
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

### three-supported-findings · robust-tables-first

- june-august-2026/run-02: [failed] The numbers are consistent with the reference facts under the answer's policy (books in Shopping, Steam in Entertainment). But the answer gives more than three findings. Its "Three things" section bundles two separate topics (shopping and gas) into item 3, and it then adds a "Smaller finding" about Planet Fitness double billing.
- june-august-2026/run-04: [failed] Finding 3 says "Shopping has stayed at or under $1,200", but the answer's own table shows August Shopping at $1,218.31 (+$18.31 over), and finding 2 says it "went just over its $1,200 target". It also says groceries plus gas "now cost more each month" than the shopping target, but June ($758) and July ($1,065) are below $1,200. The dining, travel and total figures match the reference.

