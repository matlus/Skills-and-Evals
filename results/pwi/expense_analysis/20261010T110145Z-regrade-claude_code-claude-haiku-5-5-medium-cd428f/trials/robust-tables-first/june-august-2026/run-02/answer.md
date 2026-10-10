Monthly totals and budget comparison are below. These come from the script in `expense_parse.py` in my scratchpad folder, covering the log's June to August 2026 entries.

**Monthly totals by category**

| Category | Jun | Jul | Aug | Quarter |
|---|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Eating out & coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Gas & car | 133.63 | 274.59 | 426.99 | 835.21 |
| Health | 276.43 | 138.36 | 168.61 | 583.40 |
| Transportation | 327.78 | 99.08 | 135.59 | 562.45 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Utilities & phone | 143.13 | 143.13 | 143.13 | 429.39 |
| Uncategorized | 202.66 | 30.79 | 269.74 | 503.19 |
| Health & fitness | 67.82 | 132.81 | 54.19 | 254.82 |
| Transfers to people | 68.54 | 75.00 | 0.00 | 143.54 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

**Budget comparison**

| Target | Jun | Jul | Aug |
|---|---|---|---|
| Eating out & coffee (<$260) | 212.74, under by 47.26 | 165.14, under by 94.86 | 398.69, **over by 138.69** |
| Shopping (~$1,200) | 1,020.77, under by 179.23 | 756.72, under by 443.28 | 1,218.31, **over by 18.31** |

**Largest month-over-month changes:** Travel +1,631.82 (Jul to Aug); Shopping +461.59 (Jul to Aug, after -264.05 Jun to Jul); Uncategorized +238.95 (Jul to Aug); Eating out & coffee +233.55 (Jul to Aug); Groceries +204.86 (Jun to Jul).

**Data-cleaning notes**

- **Parsing:** All 196 transaction lines parsed on the first pass. Nothing was unparseable. The two header lines were skipped. Years were assumed to be 2026 where missing. Some lines sit under the wrong month heading (e.g., "Panera Bread (07-01)" in the June section); I assigned each by its date.
- **Uncategorized (no description to classify):**
  - ATM cash withdrawals: 6/21 $100.00, 7/29 $30.79, 8/13 $79.84.
  - Zelle payments: 6/20 $102.66, 8/2 $120.00.
  - PayPal transfer: 8/7 $69.90.
  - Total $503.19. These are excluded from every budget target.
- **Person-to-person:** Venmo to "Sam" on 6/25 ($68.54) and 7/9 ($75.00). I kept these in a separate "Transfers to people" line. They might be shared meals, so you may want to recategorize them.
- **Duplicates:**
  - Removed: Trader Joe's $54.12 on 7/22 appears on two consecutive lines. I counted it once.
  - Kept, please check: Delta Air Lines on 8/14 for $412.60 and $450.60. Same day, different amounts, so I kept both. These could be a fare change or a rebooking, not a real duplicate.
  - Recurring subscriptions with identical amounts each month (iCloud, Amazon Prime, Xfinity, Netflix, Verizon, Spotify, Planet Fitness App) are real repeats, not duplicates.
- **Refund:** "Return processed - REI" on 7/18 is -$68.00. It reduces July Shopping. It may be a partial refund of the REI purchase on 7/7 ($109.19), but the log doesn't say.
- **Category choices that affect the targets:**
  - Eating out & coffee includes Rustic Tap Brewery (a bar) and all restaurants and coffee shops.
  - Shopping includes Target, Home Depot, and IKEA. Costco is counted under Groceries. Amazon Prime is counted under Subscriptions, not Shopping.
  - If you'd count these differently, the Shopping and Eating-out totals will shift.

**Three things to know about this quarter**

1. **Eating out & coffee went over its $260 target in August**, at $398.69 (over by $138.69). It was under in June ($212.74) and July ($165.14). August is up $233.55 from July, a 141% jump.
2. **Shopping is just over its $1,200 target in August**, at $1,218.31 (over by $18.31). It was up $461.59 from July. June and July were both well under, so this is a one-month overage, not a steady climb toward $2,000.
3. **August total spending is $5,646.19, about double July's $2,835.78.** Most of the jump is one-time travel: $1,631.82 from the two Delta charges, Marriott, Hertz, and airport parking. Even excluding travel, August is $1,178.59 above July, so the increase isn't only trip-related.