## Monthly totals by category (Jun–Aug 2026)

| Category | Jun | Jul | Aug | Quarter |
|---|---:|---:|---:|---:|
| Eating out / coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Transport & parking | 327.78 | 137.45 | 135.59 | 600.82 |
| Subscriptions & bills | 198.58 | 198.58 | 198.58 | 595.74 |
| Fitness (gym) | 67.82 | 132.81 | 54.19 | 254.82 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Health | 276.43 | 138.36 | 168.61 | 583.40 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Uncategorized (transfers/cash) | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |
| Total excl. uncategorized | 3,005.51 | 2,729.99 | 5,376.45 | 11,111.95 |

## Budget comparison

| Target | Month | Actual | Target | Over / (under) | % of target |
|---|---|---:|---:|---:|---:|
| Eating out / coffee | Jun | 212.74 | 260.00 | (47.26) | 81.8% |
| Eating out / coffee | Jul | 165.14 | 260.00 | (94.86) | 63.5% |
| Eating out / coffee | Aug | 398.69 | 260.00 | **+138.69** | 153.3% |
| Shopping | Jun | 1,020.77 | 1,200.00 | (179.23) | 85.1% |
| Shopping | Jul | 756.72 | 1,200.00 | (443.28) | 63.1% |
| Shopping | Aug | 1,218.31 | 1,200.00 | **+18.31** | 101.5% |

**Largest month-over-month changes:**

| Category | Period | From | To | Change |
|---|---|---:|---:|---:|
| Travel | Jul→Aug | 0.00 | 1,631.82 | +1,631.82 |
| Shopping | Jul→Aug | 756.72 | 1,218.31 | +461.59 (+61.0%) |
| Shopping | Jun→Jul | 1,020.77 | 756.72 | −264.05 (−25.9%) |
| Eating out / coffee | Jul→Aug | 165.14 | 398.69 | +233.55 (+141.4%) |
| Groceries | Jun→Jul | 624.34 | 829.20 | +204.86 (+32.8%) |
| Gas | Jul→Aug | 236.22 | 426.99 | +190.77 (+80.8%) |
| Transport & parking | Jun→Jul | 327.78 | 137.45 | −190.33 (−58.1%) |

I computed all of these with a Python script (`scratchpad/analyze.py`). It reads each line, finds the date, amount and merchant with regexes, checks for duplicates and refunds, and adds up the totals in `Decimal` so there are no rounding errors.

## Data-cleaning notes

**Lines I couldn't parse:** Only lines 1–2, which are the file's header and intro note rather than transactions. All 198 transaction lines (4–201) parsed. Dates without a year were assumed to be 2026, and every date fell between June and August. Twelve lines are out of date order (for example, L24 Kroger 6/7 comes after L23 Kroger 6/8). That fits your note about logging some entries late, and it doesn't affect the totals.

**Uncategorized ($646.73 in total).** These are money movements with no stated purpose:
- **Zelle payments:** L47 6/20 $102.66 and L125 8/2 $120.00. These are person-to-person transfers with no recipient listed.
- **ATM cash withdrawals:** L51 6/21 $100.00, L117 7/29 $30.79 and L161 8/13 $79.84. The cash could have been spent on anything, including eating out.
- **Venmo to "Sam":** L60 6/25 $68.54 and L91 7/9 $75.00. These are payments to a person, possibly splitting a bill or rent, but the log doesn't say.
- **PayPal transfer:** L141 8/7 $69.90. This could be a purchase or a transfer to a person.

**Duplicates:**
- **Removed:** L112 *Trader Joe's (Jul. 22) $54.12* is an exact copy of L111 (same date, merchant and amount), so I dropped it.
- **Kept, but please check:** L167 and L168 are both *Delta Air Lines on 8/14*, for $412.60 and $450.60. The amounts differ, so this could be two tickets or a fare plus a change. It could also be a double charge, which would be worth $412.60–$450.60.
- **Kept as separate purchases:** The script also flagged Kroger 6/6 $114.37 vs. 6/8 $112.18, BP 7/15 vs. 7/18, and Barnes & Noble 8/17 vs. 8/20. These are on different dates for different amounts, so they look like normal repeat visits.

**Refunds:** L108 *Return processed – REI, 7/18, −$68.00* is subtracted from July Shopping rather than counted as a purchase. It probably relates to the REI purchase on 7/7 ($109.19).

**Category choices that change the totals:**
- **Shopping** includes Amazon, Target, Best Buy, Old Navy, IKEA, REI, Barnes & Noble and Home Depot. **Amazon Prime** is counted under Subscriptions.
- **Target and Costco** could include groceries, but the log doesn't say. I put Target under Shopping and Costco under Groceries.
- **"Spotify Concert"** went under Entertainment. "Planet Fitness App" ($9.99) is under Subscriptions, and the separate larger Planet Fitness charges are under Fitness.

## Three things to know about this quarter

1. **Eating out and coffee went well over your $260 target in August.** You spent $398.69, which is $138.69 over (153.3% of the target). June ($212.74) and July ($165.14) were both under. The jump comes from how often you went: 18 eating-out transactions in August, compared with 10 in June and 9 in July. These were mostly small purchases, which fits your sense that it's creeping up without you noticing. Some of the $79.84 ATM cash taken out on 8/13 may also have gone to food, so the real figure could be higher.

2. **Shopping went just over your $1,200 target in August, after two months comfortably under it.** August came to $1,218.31, which is $18.31 over. That's a $461.59 increase (+61.0%) on July's $756.72 and follows $1,020.77 in June. It's nowhere near the $2,000 you're worried about, but it's moving the wrong way. The main drivers in August were Best Buy ($156.79 and $183.41), Amazon ($185.90 and $35.25), Target ($127.80) and Old Navy ($92.34). This total depends on Target counting as shopping: if some Target spending was groceries, August would come in under the target.

3. **Your August spending was almost double July's, and a trip accounts for most of the increase.** August totalled $5,646.19, against $2,835.78 in July. Travel on 8/14–8/15 cost $1,631.82 (two Delta charges, Marriott, Hertz and airport parking). Gas also rose to $426.99 from $236.22. Check the two Delta charges on 8/14 against your card statement: if one is a double charge, you could get $412.60–$450.60 back.