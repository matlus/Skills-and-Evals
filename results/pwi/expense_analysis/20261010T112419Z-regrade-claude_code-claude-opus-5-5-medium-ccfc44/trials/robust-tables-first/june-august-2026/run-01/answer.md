Totals below come from `analyze.py` in the scratchpad, which parses every line of the log.

**Monthly totals by category (cleaned)**

| Category | Jun | Jul | Aug | Quarter |
|---|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel (Aug trip) | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Eating out / coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Transport & parking | 327.78 | 137.45 | 135.59 | 600.82 |
| Subscriptions & bills | 198.58 | 198.58 | 198.58 | 595.74 |
| Health | 276.43 | 138.36 | 168.61 | 583.40 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Fitness | 67.82 | 132.81 | 54.19 | 254.82 |
| **Uncategorized** (transfers/cash) | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

**Budget comparison**

| Budget | Month | Target | Actual | Over/(under) | % of target |
|---|---|---:|---:|---:|---:|
| Eating out / coffee | Jun | 260 | 212.74 | (47.26) | 82% |
| | Jul | 260 | 165.14 | (94.86) | 64% |
| | Aug | 260 | **398.69** | **+138.69** | **153%** |
| Shopping | Jun | 1,200 | 1,020.77 | (179.23) | 85% |
| | Jul | 1,200 | 756.72 | (443.28) | 63% |
| | Aug | 1,200 | **1,218.31** | **+18.31** | **102%** |

**Largest month-over-month changes**

| Category | Period | From | To | Change |
|---|---|---:|---:|---:|
| Travel | Jul→Aug | 0.00 | 1,631.82 | +1,631.82 |
| Shopping | Jul→Aug | 756.72 | 1,218.31 | +461.59 |
| Shopping | Jun→Jul | 1,020.77 | 756.72 | −264.05 |
| Eating out / coffee | Jul→Aug | 165.14 | 398.69 | +233.55 |
| Groceries | Jun→Jul | 624.34 | 829.20 | +204.86 |
| Gas | Jul→Aug | 236.22 | 426.99 | +190.77 |
| Transport & parking | Jun→Jul | 327.78 | 137.45 | −190.33 |

The script is at `scratchpad/analyze.py`. It finds each line's date using five format patterns (`2026-06-09`, `6/3/26`, `6/2`, `06-01`, `Jun. 3`/`June 3`), takes the amount as the dollar figure with a sign, and uses what's left as the description. It assigns categories by merchant keyword, removes exact duplicates, keeps refunds as negative amounts in their category, and then groups by month. It also printed every parsed line next to the raw text, and I checked them all.

## Data-cleaning notes

**Lines I couldn't parse:** None. All 198 entries gave a clear date, merchant and amount. Some judgment calls:
- Dates without a year are treated as 2026. `06-01`-style dates are read as month-day.
- Some lines are out of order (e.g., L23 `6/8` comes before L24 `Jun. 7`, and L59 `Jun. 28` comes before L60 `06-25`). They're sorted by their actual date, not their position in the file.

**Uncategorized ($646.73 over the quarter).** These are money moved out, with no clue what it paid for:

| Line | Date | Entry | Amount |
|---|---|---|---:|
| 47 | Jun 20 | Zelle Payment | 102.66 |
| 51 | Jun 21 | ATM Cash Withdrawal | 100.00 |
| 60 | Jun 25 | Venmo – Sam | 68.54 |
| 91 | Jul 9 | Venmo – Sam | 75.00 |
| 117 | Jul 29 | ATM Cash Withdrawal | 30.79 |
| 125 | Aug 2 | Zelle Payment | 120.00 |
| 141 | Aug 7 | PayPal Transfer | 69.90 |
| 161 | Aug 13 | ATM Cash Withdrawal | 79.84 |

The Venmo payments to Sam could be splitting a bill (food or rent) or paying someone back. The cash could have gone anywhere. If any of it was meals, your eating-out totals are understated.

**Duplicates:**
- **Removed:** L111 and L112, `Trader Joe's (Jul. 22) - $54.12`, are the same text twice. I dropped one, which cuts July groceries by $54.12.
- **Flagged but kept, needs your check:** L167 and L168, two Delta Air Lines charges on Aug 14 ($412.60 and $450.60). The amounts differ, so this could be two tickets or a fare change. It could also be a mistyped repeat. If it's a repeat, travel is $450.60 lower. Neither budget changes.
- **Kept, probably real:** These are the same merchant within 3 days at similar amounts. Kroger Jun 6 ($114.37) and Jun 8 ($112.18), BP Gas Jul 15 and Jul 18, Barnes & Noble Aug 17 and Aug 20. They have different dates and amounts, so I treated them as separate purchases.

**Refunds:** L108, `Return processed - REI - -$68.00`, is the only negative amount. It's subtracted from July Shopping rather than counted as spending.

**Category choices that affect the results:**
- **Shopping** = Amazon, Target, Best Buy, REI, Old Navy, IKEA, Home Depot, Barnes & Noble. **Amazon Prime** counts as a subscription, not shopping. **Costco** counts as groceries.
- **Target** is the risky one. August shopping is only $18.31 over budget, and the single $127.80 Target trip on Aug 9 is bigger than that. If that trip was mostly groceries, you're actually under budget.
- **Spotify Concert** (four charges) is under Entertainment because it looks like ticket purchases, not the Premium subscription.
- **Planet Fitness**: The $9.99 "App" charge is a subscription. The separate $54–74 monthly "Planet Fitness" charges are under Fitness. Two different Planet Fitness charges every month is worth a look.

## The three things worth knowing

1. **August eating out was 153% of budget, and it wasn't the trip.** You had 18 eating-out charges in August, compared with 10 in June and 9 in July. Almost none of them fall during the Aug 14–16 trip. The amount per purchase didn't change; you just ate out about twice as often, all month long. That's the creep you mentioned not noticing. June and July were comfortably under $260.

2. **August cost about twice what July did, and the trip is only part of it.** Travel accounts for $1,631.82. But shopping, groceries, gas and eating out all went up in August too. Shopping jumped $461.59 and went just over $1,200, driven by Best Buy ($340 across two trips), REI, Barnes & Noble and Amazon. Gas nearly doubled. Groceries have gone up every month (624 → 829 → 983).

3. **Shopping is under control overall, but $647 isn't tracked at all.** Shopping averaged under $1,000 a month, nowhere near the $2,000 you're worried about. Meanwhile, Zelle, Venmo, PayPal and ATM cash came to $646.73 with no record of what they paid for. That's more than the whole quarter's eating out ($776.57) minus one month. Adding a word to those entries ("Sam – dinner", "cash – farmers market") would make both budgets more reliable.