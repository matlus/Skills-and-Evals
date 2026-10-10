## Computed tables

**Monthly totals by category (USD, refunds netted, duplicate excluded)**

| Category | June | July | August | Quarter |
|---|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Transport & travel | 327.78 | 99.08 | 1,767.41 | 2,194.27 |
| Subscriptions & bills | 266.40 | 331.39 | 252.77 | 850.56 |
| Gas & car | 133.63 | 274.59 | 426.99 | 835.21 |
| Eating out & coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Health & pharmacy | 276.43 | 138.36 | 168.61 | 583.40 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Total (excl. uncategorized) | 3,005.51 | 2,729.99 | 5,376.45 | 11,111.95 |
| Uncategorized (see notes) | 271.20 | 105.79 | 269.74 | 646.73 |

**Budget comparison**

| Budget | June | July | August | Quarter |
|---|---|---|---|---|
| Eating out & coffee (target $260/mo, $780/qtr) | 212.74 (under 47.26) | 165.14 (under 94.86) | 398.69 (**over 138.69**) | 776.57 (under 3.43) |
| Shopping (target $1,200/mo, $3,600/qtr) | 1,020.77 (under 179.23) | 756.72 (under 443.28) | 1,218.31 (**over 18.31**) | 2,995.80 (under 604.20) |

**Largest month-over-month changes**

| Category | Jun→Jul | Jul→Aug |
|---|---:|---:|
| Transport & travel | -228.70 | **+1,668.33** |
| Shopping | -264.05 | +461.59 |
| Eating out & coffee | -47.60 | +233.55 |
| Groceries | +204.86 | +153.59 |
| Uncategorized | -165.41 | +163.95 |
| Gas & car | +140.96 | +152.40 |
| Health & pharmacy | -138.07 | +30.25 |
| Subscriptions & bills | +64.99 | -78.62 |
| Entertainment | -7.91 | +25.37 |

The parser and calculations are in `scratchpad\parse_expenses.py`.

## Data-cleaning notes

- **Parsing:** All 198 transaction lines parsed. Nothing was unreadable. Lines 1–3 are the header note and were skipped. Entries have no year, so I assumed 2026. Dates are used as written, even though the header says some entries were logged a day or two late. One line (Panera, "07-01") sits in the June block; it's counted in July.
- **Duplicate excluded:** Line 112, Trader Joe's 7/22 $54.12, is identical to line 111. If it was really two purchases, add $54.12 to July groceries.
- **Possible duplicate kept:** Delta Air Lines on 8/14 appears twice, at $412.60 (line 167) and $450.60 (line 168). I kept both since the amounts differ. If one is a correction, August transport drops by that amount.
- **Refund:** REI return on 7/18, -$68.00 (line 108), is netted against July shopping.
- **Uncategorized, $646.73 total:**
  - Zelle payments, 6/20 $102.66 and 8/2 $120.00: no recipient named.
  - PayPal Transfer, 8/7 $69.90: no recipient named.
  - Venmo to "Sam", 6/25 $68.54 and 7/9 $75.00: person-to-person, purpose unknown. These could be shared costs.
  - ATM cash withdrawals, 6/21 $100.00, 7/29 $30.79, and 8/13 $79.84: cash, so the spend is unknown.
- **Judgment calls:** Costco went to Groceries and Target to Shopping, though both sell non-grocery items. Amazon Prime went to Subscriptions, not Shopping. Walgreens and CVS went to Health. Rustic Tap Brewery went to Eating out.
- **Worth checking:** Planet Fitness charges of $67.82, $73.58, $59.23, and $54.19 are far above the $9.99 app charges. They may be misentered or a different plan.

## Three things to know

1. **August eating out and coffee went over target.** It came in at $398.69, which is $138.69 over the $260 target. June ($212.74) and July ($165.14) were both under, so this is a one-month spike rather than steady creep. The quarter ($776.57) is only $3.43 under its $780 equivalent, so the quarter total hides the August overage.
2. **August shopping barely went over target.** It came in at $1,218.31, which is $18.31 over the $1,200 target. June and July were both under, and the quarter ($2,995.80) is $604.20 under its $3,600 equivalent. Shopping is your largest category for the quarter, as your note suggested.
3. **August transport jumped and drove most of the month's increase.** Transport & travel went from $99.08 in July to $1,767.41 in August, up $1,668.33. That is mostly mid-August trip charges: Delta (two charges), Marriott, Hertz, and airport parking. This category has no budget target. It accounts for about 63% of the $2,646.46 increase in total spending from July ($2,729.99) to August ($5,376.45).