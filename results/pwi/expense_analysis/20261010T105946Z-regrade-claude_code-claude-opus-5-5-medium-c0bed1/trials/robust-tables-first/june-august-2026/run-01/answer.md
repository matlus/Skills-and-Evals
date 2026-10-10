All figures below come from `analyze.py` in the scratchpad (full code there; output pasted as-is).

**Monthly totals by category (USD, June–August 2026)**

| Category | Jun | Jul | Aug | Q total | Jun→Jul | Jul→Aug |
|---|---:|---:|---:|---:|---:|---:|
| Eating out / coffee | 212.74 | 165.14 | 398.69 | 776.57 | -47.60 | +233.55 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 | -264.05 | +461.59 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 | +204.86 | +153.59 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 | +102.59 | +190.77 |
| Transport / parking / car | 327.78 | 137.45 | 135.59 | 600.82 | -190.33 | -1.86 |
| Subscriptions & bills | 198.58 | 198.58 | 198.58 | 595.74 | +0.00 | +0.00 |
| Health & fitness | 344.25 | 271.17 | 222.80 | 838.22 | -73.08 | -48.37 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 | -7.91 | +25.37 |
| Travel (Aug trip) | 0.00 | 0.00 | 1,631.82 | 1,631.82 | +0.00 | +1,631.82 |
| UNCATEGORIZED | 271.20 | 105.79 | 269.74 | 646.73 | -165.41 | +163.95 |
| **Total (categorized)** | 3,005.51 | 2,729.99 | 5,376.45 | 11,111.95 | -275.52 | +2,646.46 |
| **Total (incl. uncategorized)** | 3,276.71 | 2,835.78 | 5,646.19 | 11,758.68 | -440.93 | +2,810.41 |

**Budget comparison (difference from target in parentheses)**

| Budget | Target | Jun | Jul | Aug | Months over |
|---|---:|---:|---:|---:|---:|
| Eating out / coffee | 260 | 212.74 (-47.26) | 165.14 (-94.86) | 398.69 (+138.69) | 1/3 |
| Shopping | 1,200 | 1,020.77 (-179.23) | 756.72 (-443.28) | 1,218.31 (+18.31) | 1/3 |

**Largest month-over-month changes:** Travel Jul→Aug +1,631.82 (from $0); Shopping Jul→Aug +461.59 (+61%); Shopping Jun→Jul −264.05 (−26%); Eating out Jul→Aug +233.55 (+141%); Groceries Jun→Jul +204.86 (+33%); Gas Jul→Aug +190.77 (+81%).

## Data-cleaning notes

**Parsing:** All 198 transaction lines parsed into a date, merchant and amount. None failed. The script also checks that every date falls between June 1 and August 31, 2026. Dates with no year were read as 2026. Lines that are out of order (e.g., line 23 dated 6/8 sits before 6/7 entries) were placed by their stated date, not their position.

**Uncategorized (8 entries, $646.73).** These are person-to-person payments or cash, so there's no way to tell what they paid for:
- Zelle Payment: 6/20 $102.66, 8/2 $120.00
- ATM Cash Withdrawal: 6/21 $100.00, 7/29 $30.79, 8/13 $79.84
- Venmo – Sam: 6/25 $68.54, 7/9 $75.00 (a named person, but no reason given; could be splitting a bill, rent, or paying back a loan)
- PayPal Transfer: 8/7 $69.90

They're in the grand total but not in either budget line. If any of them were meals out or shopping, those budget figures are understated.

**Duplicates:**
- **Removed:** Trader Joe's, Jul 22, $54.12 (lines 111 and 112): same date, merchant and amount on consecutive lines.
- **Kept, but please check:** Delta Air Lines on Aug 14, $412.60 and $450.60 (lines 167–168). Two tickets on the same day is plausible, but if one is a re-entry, Travel is overstated by that amount.
- **Kept:** Kroger on Jun 6 ($114.37) and Jun 8 ($112.18). The dates and amounts differ, so these look like two real trips.

**Refunds:** "Return processed – REI, 7/18, −$68.00" is counted as −$68 against July Shopping, not as a purchase.

**Category choices you might disagree with:**
- Shopping includes Amazon, Best Buy, Target, Old Navy, REI, IKEA, Barnes & Noble and Home Depot.
- Amazon Prime is under Subscriptions, not Shopping.
- Planet Fitness App ($9.99/mo) is under Subscriptions. The separate, varying Planet Fitness charges are under Health & fitness.
- Rustic Tap Brewery counts as eating out.
- "Spotify Concert" is under Entertainment.

## The three things to know

1. **Eating out is the target you broke by the most, and only in August.** June ($212.74) and July ($165.14) were under $260. August hit $398.69, which is $138.69 over the target and up 141% from July. The number of visits went from 9 in July to 18 in August. It wasn't the trip: only one meal ($8.05 Starbucks) fell on the Aug 14–16 travel days. Most of the increase came from places you already went, more often: Luigi's Pizza ($78.48, new in August), Chipotle ($72.17), Rustic Tap ($58.89) and Panera ($54.70).

2. **Shopping went over its target in August, but only just.** August was $1,218.31, which is $18.31 over $1,200, after two months under it ($1,020.77 and $756.72). Your worry about it drifting toward $2,000 hasn't happened. The quarter total of $2,995.80 averages under $1,200 a month. But it's still your largest category for the quarter. And the August overage is small enough that the category choices decide it: leaving out the IKEA purchase ($68.71) alone would put August at $1,149.60, under the target.

3. **August spending nearly doubled, and the trip explains only part of it.** Total spending went from $2,835.78 in July to $5,646.19 in August, an increase of $2,810.41. Travel accounts for $1,631.82 of that, so $1,178.59 came from everyday spending. Groceries ($624.34 → $829.20 → $982.79) and gas ($133.63 → $236.22 → $426.99) went up every month. Those two are the steady increase you said you might not be noticing.