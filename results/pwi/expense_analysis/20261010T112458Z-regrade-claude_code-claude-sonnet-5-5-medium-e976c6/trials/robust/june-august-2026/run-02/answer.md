All 198 entries parsed, with no unparsed lines. The tables below come from `parse.py` and `run1.py` to `run3.py` in the scratchpad, and every figure was computed in Python with `Decimal`.

## Data cleaning

**Parsing.** I assumed all dates are 2026 and that `07-05` means July 5, not May 7. Every date fell in June–August. The log is out of order in 12 places, mostly by a day or two, and I sorted by parsed date rather than line order. No line was ambiguous enough to flag as unparseable.

**Duplicates and refunds**
- **Removed:** the Trader Joe's entry on Jul 22 for $54.12 appears twice, back to back (lines 111 and 112). I dropped the second one, which takes $54.12 out of July groceries. If you really made two identical trips, add it back.
- **Kept but flagged:** Delta Air Lines on Aug 14 appears twice, at $412.60 and $450.60. These could be a re-entry after a fare change, or two travelers. Either way, one may be a duplicate worth $412–$451. Aug total would be $5,233.59 without the first, or $5,195.59 without the second.
- **Not duplicates:** the repeated amounts for iCloud, Prime, Netflix, Spotify, Xfinity, Verizon and Planet Fitness App are monthly recurring charges, one per month.
- **Refund:** the only negative is the REI return of −$68.00 on Jul 18. I netted it against Shopping in July, the month it was processed. It does not count as income or spending. July shopping is $756.72 net, or $824.72 before the refund.

**Uncategorized.** These 8 entries total $646.73 and I did not force a category on them. They are all money movements with no merchant:

| Date | Item | Amount |
|---|---|---|
| Jun 20 | Zelle Payment | $102.66 |
| Jun 21 | ATM Cash Withdrawal | $100.00 |
| Jun 25 | Venmo – Sam | $68.54 |
| Jul 9 | Venmo – Sam | $75.00 |
| Jul 29 | ATM Cash Withdrawal | $30.79 |
| Aug 2 | Zelle Payment | $120.00 |
| Aug 7 | PayPal Transfer | $69.90 |
| Aug 13 | ATM Cash Withdrawal | $79.84 |

**Judgment calls.** These affect the budget numbers, so check them:
- **Costco is Groceries.** It could be shopping, and it is $197–$406 a month.
- **Rustic Tap Brewery is Dining/Coffee.** I counted bars as eating out. It is $8–$59 a month.
- **Planet Fitness without "App" is Health/Fitness.** The "App" entries at $9.99 are Subscriptions. The others vary ($54–$74), so they don't look like the subscription.
- **Spotify Concert is Entertainment, not a Spotify subscription.**
- **Amazon Prime is a Subscription,** so it is not in the Shopping budget line.
- **Shopping** covers Amazon, Target, Best Buy, REI, Old Navy, IKEA, Home Depot and Barnes & Noble.

## Tables

**Monthly totals by category**

| Category | Jun | Jul | Aug | Total | Avg/mo |
|---|---:|---:|---:|---:|---:|
| Dining/Coffee | 212.74 | 165.14 | 398.69 | 776.57 | 258.86 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 | 998.60 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 | 812.11 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 | 265.61 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 | 55.45 |
| Bills/Utilities | 143.13 | 143.13 | 143.13 | 429.39 | 143.13 |
| Health/Fitness | 344.25 | 271.17 | 222.80 | 838.22 | 279.41 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 | 146.60 |
| Transport/Parking | 327.78 | 137.45 | 135.59 | 600.82 | 200.27 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 | 543.94 |
| Uncategorized | 271.20 | 105.79 | 269.74 | 646.73 | 215.58 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** | **3,919.56** |

**Budget check**

| Budget | Month | Spent | Target | Difference | % of target |
|---|---|---:|---:|---:|---:|
| Eating out/coffee | Jun | 212.74 | 260 | −47.26 | 82% |
| Eating out/coffee | Jul | 165.14 | 260 | −94.86 | 64% |
| Eating out/coffee | **Aug** | **398.69** | 260 | **+138.69** | **153%** |
| Shopping | Jun | 1,020.77 | 1,200 | −179.23 | 85% |
| Shopping | Jul | 756.72 | 1,200 | −443.28 | 63% |
| Shopping | **Aug** | **1,218.31** | 1,200 | **+18.31** | **102%** |

**Eating-out detail**

| Month | Entries | Coffee/bagel | Brewery | Restaurants/fast food | Total |
|---|---:|---:|---:|---:|---:|
| Jun | 10 | 86.12 | 8.37 | 118.25 | 212.74 |
| Jul | 9 | 33.38 | 13.03 | 118.73 | 165.14 |
| Aug | 18 | 64.79 | 58.89 | 275.01 | 398.69 |

**Largest month-over-month changes (category by month pair, top 10 by dollar change)**

| Category | Change | From | To | $ change | % change |
|---|---|---:|---:|---:|---:|
| Travel | Jul→Aug | 0.00 | 1,631.82 | +1,631.82 | n/a |
| Shopping | Jul→Aug | 756.72 | 1,218.31 | +461.59 | +61% |
| Shopping | Jun→Jul | 1,020.77 | 756.72 | −264.05 | −26% |
| Dining/Coffee | Jul→Aug | 165.14 | 398.69 | +233.55 | +141% |
| Groceries | Jun→Jul | 624.34 | 829.20 | +204.86 | +33% |
| Gas | Jul→Aug | 236.22 | 426.99 | +190.77 | +81% |
| Transport/Parking | Jun→Jul | 327.78 | 137.45 | −190.33 | −58% |
| Uncategorized | Jun→Jul | 271.20 | 105.79 | −165.41 | −61% |
| Uncategorized | Jul→Aug | 105.79 | 269.74 | +163.95 | +155% |
| Groceries | Jul→Aug | 829.20 | 982.79 | +153.59 | +19% |

Total spending fell 13.5% from June to July (−$440.93). It rose 99.1% from July to August (+$2,810.41).

## The three things I'd most want you to know

1. **Eating out blew past the target in August, and the quarterly average hides it.** The 3-month average is $258.86, just under $260. But spending went $213, then $165, then $399. August had 18 entries against 9–10 in the other months. The overage isn't one-off. Restaurants and fast food went from about $118 to $275, and the brewery went from $13 to $59. Even without the brewery, August is $339.80, still over target. Your note says it has been creeping up without you noticing, and August is where it shows.

2. **Shopping is within budget, but August brought it back to the line.** It was $1,021, then $757, then $1,218, which is $18 over. That is nowhere near $2,000, but July's low number includes a $68 REI refund, so the true trend is flatter than it looks. August was driven by Best Buy ($340 across 2 purchases) and Amazon ($221, your highest month). Costco is classified as Groceries, so if you think of it as shopping, the picture is worse. Costco went from $197 to $225 to $406, and groceries overall rose every month (+57% from June to August).

3. **August also had a one-off trip, which hides a broader increase.** Travel was $1,631.82 (flights, Marriott, Hertz, airport parking), which is why August is nearly double July. Without it, August is $4,014.37, still $1,179 above July. Gas more than tripled from June to August ($134 to $427, partly the trip but also more fill-ups at BP and Shell). The Delta double-entry could mean the real August total is $412–$451 lower, so please check it first. Also, $647 across 8 Zelle, Venmo, PayPal and ATM entries has no destination, about 5.5% of everything logged. If you tell me what they were, I can move them into the right categories.