### Monthly totals by category (USD, duplicates removed)

| Category | Jun | Jul | Aug | Total |
|---|---:|---:|---:|---:|
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Travel | 0.00 | 0.00 | 1,563.82 | 1,563.82 |
| Gas & car | 133.63 | 274.59 | 426.99 | 835.21 |
| Rides & parking | 327.78 | 99.08 | 203.59 | 630.45 |
| Eating out & coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Health | 276.43 | 138.36 | 168.61 | 583.40 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Phone & internet | 143.13 | 143.13 | 143.13 | 429.39 |
| Fitness | 77.81 | 142.80 | 64.18 | 284.79 |
| Subscriptions | 45.46 | 45.46 | 45.46 | 136.38 |
| Uncategorized (see notes) | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

### Budget comparison

| Target | Monthly limit | Jun | Jul | Aug |
|---|---:|---:|---:|---:|
| Eating out & coffee | 260.00 | 212.74 (under by 47.26) | 165.14 (under by 94.86) | **398.69 (over by 138.69)** |
| Shopping, all retail incl. Amazon | 1,200.00 | 1,020.77 (under by 179.23) | 756.72 (under by 443.28) | **1,218.31 (over by 18.31)** |
| Amazon only, excl. Prime (no target) | — | 182.78 | 141.82 | 221.15 |

### Largest month-over-month changes

| Category | Change | From → To |
|---|---:|---|
| Travel | +1,563.82 | Jul → Aug (0.00 → 1,563.82) |
| Shopping | +461.59 | Jul → Aug |
| Eating out & coffee | +233.55 | Jul → Aug |
| Rides & parking | −228.70 | Jun → Jul |
| Groceries | +204.86 | Jun → Jul |
| Groceries | +153.59 | Jul → Aug |

## Data-cleaning notes

- **Parsing:** All 198 entries parsed (lines 4–201). Lines 1–2 are the header and were skipped. No lines failed. Every date falls in 2026, from Jun 1 to Aug 31. The log ends Aug 31, while today is Oct 9, so "this quarter" is covered only through August. Everything above uses the full June–August log.
- **Uncategorized (8 entries, $646.73):** These have no merchant or purpose, so I did not assign a category.
  - Zelle payments: 6/20 $102.66 and 8/2 $120.00. These are bank transfers with no payee or purpose.
  - ATM cash withdrawals: 6/21 $100.00, 7/29 $30.79, and 8/13 $79.84. Cash with unknown spending.
  - PayPal Transfer: 8/7 $69.90. Purpose unknown.
  - Venmo to "Sam": 6/25 $68.54 and 7/9 $75.00. Person-to-person payments with no purpose recorded.
- **Duplicate:** Lines 111 and 112 are identical (Trader Joe's, Jul 22, $54.12). I counted one and dropped the second. If both were real purchases, July groceries are $54.12 higher.
- **Refund:** Line 108, the REI return on Jul 18 (-$68.00), is netted against July Shopping as a negative amount.
- **Not treated as duplicates:** The recurring Netflix, Spotify, Verizon, Xfinity and iCloud charges. Also Delta on Aug 14 ($412.60 and $450.60, lines 167 and 168). The amounts differ, so I kept both, but they are worth checking.
- **Category assumptions:**
  - Costco counted as Groceries.
  - Amazon Prime counted as Subscriptions, not Shopping. If it were counted as Shopping, August would be $1,233.30, which is still over.
  - Rustic Tap Brewery counted as Eating out & coffee.
  - Home Depot, IKEA, REI and Target counted as Shopping.

The script is in the scratchpad as `analyze.py`.

## The three things to know

1. **Eating out & coffee went over your $260 limit in August, at $398.69 (over by $138.69).** June and July were under. August had 18 eating-out transactions, against 9 in July and 10 in June.
2. **Shopping crossed $1,200 in August, at $1,218.31 ($18.31 over).** It was the first month over the limit. Best Buy ($340.20 across Aug 11 and 31), Amazon ($221.15 across three orders), REI ($132.82) and Target ($127.80) drove it. Amazon alone is far below the $1,200 figure.
3. **August travel was $1,563.82, against zero in June and July.** It came from Delta ($412.60 and $450.60 on Aug 14), Marriott ($486.27) and Hertz ($214.35). It is the largest month-over-month change in the log. Your notes don't set a target for travel, so I did not judge it against one. The two Delta charges on the same day are worth checking.