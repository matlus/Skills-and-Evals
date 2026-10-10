Script used: `expenses.py` in the session scratchpad (output below).

**Monthly totals by category** (after removing one duplicate; refunds netted)

| Category | Jun | Jul | Aug | Total |
|---|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Gas & transport | 461.41 | 373.67 | 562.58 | 1,397.66 |
| Health & fitness | 354.24 | 281.16 | 232.79 | 868.19 |
| Eating out & coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Uncategorized (transfer/cash) | 271.20 | 105.79 | 269.74 | 646.73 |
| Bills & subscriptions | 188.59 | 188.59 | 188.59 | 565.77 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

**Budget comparison**

| Category (target) | Month | Spent | Over / (under) | % of target |
|---|---|---:|---:|---:|
| Eating out & coffee ($260) | Jun | 212.74 | (47.26) | 81.8% |
| | Jul | 165.14 | (94.86) | 63.5% |
| | Aug | 398.69 | 138.69 | 153.3% |
| Shopping ($1,200) | Jun | 1,020.77 | (179.23) | 85.1% |
| | Jul | 756.72 | (443.28) | 63.1% |
| | Aug | 1,218.31 | 18.31 | 101.5% |

**Largest month-over-month changes**

| Category | Change | $ change | % change |
|---|---|---:|---:|
| Travel | Jul to Aug | +1,631.82 | n/a (from 0) |
| Shopping | Jul to Aug | +461.59 | +61.0% |
| Shopping | Jun to Jul | -264.05 | -25.9% |
| Eating out & coffee | Jul to Aug | +233.55 | +141.4% |
| Groceries | Jun to Jul | +204.86 | +32.8% |
| Gas & transport | Jul to Aug | +188.91 | +50.6% |

**Data-cleaning notes**

- **Parsing:** All 198 transaction lines parsed. None failed. Dates appeared in four formats and all resolved to 2026.
- **Duplicate removed:** Line 112, "Trader Joe's (Jul. 22) - $54.12", is identical to line 111. I excluded it from totals (-$54.12). If you really made two trips, the total is understated.
- **Same-day, different amounts (kept both):** Delta Air Lines on Aug 14 appears as $412.60 (line 167) and $450.60 (line 168). This could be an outbound and return fare, or a correction. If one is a double charge, Travel drops by that amount.
- **Refund:** Line 108, REI return of -$68.00 on Jul 18, is netted against Shopping. I can't tell which REI purchase it reverses.
- **Recurring charges:** iCloud, Amazon Prime, Xfinity, Netflix, Planet Fitness App, Verizon, and Spotify Premium repeat monthly at the same amount. I treated them as real, not duplicates.
- **Uncategorized, $646.73 across 8 entries:**
  - Zelle Payment, Jun 20, $102.66
  - ATM Cash Withdrawal, Jun 21, $100.00
  - Venmo - Sam, Jun 25, $68.54
  - Venmo - Sam, Jul 9, $75.00
  - ATM Cash Withdrawal, Jul 29, $30.79
  - Zelle Payment, Aug 2, $120.00
  - PayPal Transfer, Aug 7, $69.90
  - ATM Cash Withdrawal, Aug 13, $79.84
  
  The ATM withdrawals and Zelle/PayPal transfers have no description. The two Venmo payments are to a person, but the purpose isn't recorded. These are included in the total, but not in any category.
- **Judgment calls:** Costco is counted as Groceries, and Target as Shopping (both may include non-grocery items). Rustic Tap Brewery is counted as Eating out & coffee. Home Depot is counted as Shopping.
- **Coverage:** The log runs Jun 1 to Aug 31 only. It is not a calendar quarter, and September has no entries. Some entries were logged late from memory, which I couldn't verify.

**Three things to know**

1. **Eating out & coffee went over its $260 target only in August**, at $398.69 (153.3%, $138.69 over). It was $165.14 in July and $212.74 in June, so August is a sharp jump rather than a steady climb.
2. **Shopping is $18.31 over its $1,200 target in August**, at $1,218.31. It was under target in June (85.1%) and July (63.1%), and rose $461.59 (+61.0%) from July. Two large August purchases are Amazon at $185.90 (Aug 9) and Best Buy at $183.41 (Aug 31).
3. **August Travel totals $1,631.82, with no travel in June or July.** It covers Delta (two entries on Aug 14), Marriott ($486.27), Hertz ($214.35), and airport parking ($68.00). Travel is why August's total of $5,646.19 is nearly double July's $2,835.78.