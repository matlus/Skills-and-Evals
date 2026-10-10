**Monthly totals by category (USD, parsed from personal_expenses.txt; 197 transactions after removing one duplicate)**

| Category | Jun | Jul | Aug | Total |
|---|---:|---:|---:|---:|
| Shopping | 871.48 | 466.89 | 1,149.60 | 2,487.97 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Health | 344.25 | 271.17 | 222.80 | 838.22 |
| Gas & car | 133.63 | 274.59 | 426.99 | 835.21 |
| Eating out & coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Rideshare & parking | 327.78 | 99.08 | 135.59 | 562.45 |
| Home | 149.29 | 289.83 | 68.71 | 507.83 |
| Uncategorized | 202.66 | 30.79 | 269.74 | 503.19 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Phone & internet | 143.13 | 143.13 | 143.13 | 429.39 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| Peer payments | 68.54 | 75.00 | 0.00 | 143.54 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

**Budget comparison**

| | Jun | Jul | Aug |
|---|---:|---:|---:|
| Eating out & coffee | 212.74 | 165.14 | 398.69 |
| vs. $260 target | -47.26 | -94.86 | **+138.69** |
| Shopping + Home | 1,020.77 | 756.72 | 1,218.31 |
| vs. $1,200 target | -179.23 | -443.28 | **+18.31** |
| vs. $2,000 alarm | -979.23 | -1,243.28 | -781.69 |

**Largest month-over-month changes**

| Category | Change | From → To | Change % |
|---|---:|---|---:|
| Travel | +1,631.82 | 0.00 → 1,631.82 (Jul→Aug) | n/a (from zero) |
| Shopping | +682.71 | 466.89 → 1,149.60 (Jul→Aug) | +146.2% |
| Shopping | -404.59 | 871.48 → 466.89 (Jun→Jul) | -46.4% |
| Uncategorized | +238.95 | 30.79 → 269.74 (Jul→Aug) | +776.1% |
| Eating out & coffee | +233.55 | 165.14 → 398.69 (Jul→Aug) | +141.4% |
| Rideshare & parking | -228.70 | 327.78 → 99.08 (Jun→Jul) | -69.8% |
| Home | -221.12 | 289.83 → 68.71 (Jul→Aug) | -76.3% |
| Groceries | +204.86 | 624.34 → 829.20 (Jun→Jul) | +32.8% |

**Data-cleaning notes**

- **Parsing:** All 198 transaction lines parsed. None were unparseable. Dates are all 2026, from 6/1 to 8/31. The log covers June through August, so it spans Q2 and Q3 and leaves out September. I treated the whole file as "this quarter."
- **Out-of-order entry:** "Panera Bread (07-01)" sits in the June block. I counted it as July 1.
- **Duplicate removed:** Trader Joe's, Jul 22, $54.12, on lines 111 and 112. The lines are identical, so I kept one. If they were two real purchases, add $54.12 to July groceries.
- **Possible duplicate kept:** Delta Air Lines, Aug 14, $412.60 (line 167) and $450.60 (line 168). Same day and airline, different amounts. I kept both. If one is a duplicate or a correction, Travel drops by that amount.
- **Refund:** REI "Return processed" -$68.00 on Jul 18 (line 108). It is netted against July Shopping, not counted as a purchase.
- **Uncategorized, $503.19 across 6 lines.** The log doesn't say what these were for:
  - Zelle payments: $102.66 on Jun 20 (line 47) and $120.00 on Aug 2 (line 125). No recipient is listed.
  - PayPal Transfer: $69.90 on Aug 7 (line 141). No recipient is listed.
  - ATM cash withdrawals: $100.00 on Jun 21 (line 51), $30.79 on Jul 29 (line 117), and $79.84 on Aug 13 (line 161). I can't tell what the cash was spent on.
- **Peer payments:** Two "Venmo - Sam" payments, $68.54 (Jun 25) and $75.00 (Jul 9). I categorized them as peer payments, which aren't in either budget.
- **Choices that affect the targets:**
  - Eating out & coffee includes Rustic Tap Brewery ($80.29 total), which I treated as eating out.
  - The shopping figure is the Shopping category plus Home (Home Depot, IKEA).
  - Costco is counted as groceries. Costco in August was $405.69. If you count it as shopping, August shopping + home becomes $1,624.00, which is well over the $1,200 target and close to the $2,000 alarm.
  - Amazon Prime ($14.99/month) is in Subscriptions. Adding it to shopping gives August $1,233.30, still over $1,200.

**Three things to know**

1. **Eating out & coffee went over its $260 target in August only.** August was $398.69, which is $138.69 over. June ($212.74) and July ($165.14) were under. August rose $233.55 from July. The data shows one August jump, not a steady climb.
2. **Shopping + Home is just over its $1,200 target in August.** August was $1,218.31, which is $18.31 over, and up $461.59 from July's $756.72. It stayed $781.69 under the $2,000 alarm. This depends on the Costco choice above.
3. **Total spending nearly doubled in August.** August totaled $5,646.19, up from $2,835.78 in July. Travel accounts for $1,631.82 of that, more than half of the $2,810.41 increase. Travel has no budget target, so I haven't judged it against one.