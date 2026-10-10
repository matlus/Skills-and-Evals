I parsed and categorised your log with Python, and all the totals below come from that code, not from mental arithmetic. Your August spending was about double July's. The $1,632 trip explains most of the jump, but eating out went over budget that month, shopping just went over, and gas and groceries have been rising every month.

The scripts are in your scratchpad: `expenses.py` does the main parse and analysis, and `followup.py` works out the extra figures I quote in the last section.

## How the data was cleaned

**Parsing:** 198 of the 200 non-blank lines parsed into a date, merchant and amount. The two that didn't are lines 1–2, the title and your note, which aren't transactions. The script handles every date format in the file (`June 1`, `Jun. 3`, `6/2`, `6/3/26`, `06-01`, `2026-06-05`) and assumes 2026 when no year is given. A minus sign only counts if it's attached to the amount (as in `-$68.00`), so the bullet and separator dashes aren't read as refunds. I checked every parsed row against the original line.

**Duplicates:**
- **Removed:** line 112, Trader Joe's on Jul 22 for $54.12. It's identical to line 111 (same date, store and amount).
- **Kept, but please check:** two Delta Air Lines charges on Aug 14, $412.60 and $450.60. They could be two tickets or a fare change plus a re-booking. If one is a duplicate, travel is $1,219.22 rather than $1,631.82.
- **Kept:** Kroger on Jun 6 ($114.37) and Jun 8 ($112.18). The dates and amounts both differ, so these look like two real shops.

**Refunds:** REI returned $68.00 on Jul 18. I subtracted it from July's shopping rather than counting it as a purchase.

**Uncategorised ($646.73, not in any budget figure):** I can't tell what these were for.

| Line | Date | What it is | Amount |
|---|---|---|---|
| 47 | Jun 20 | Zelle payment, no description | $102.66 |
| 51 | Jun 21 | ATM cash withdrawal | $100.00 |
| 60 | Jun 25 | Venmo to Sam | $68.54 |
| 91 | Jul 9 | Venmo to Sam | $75.00 |
| 117 | Jul 29 | ATM cash withdrawal | $30.79 |
| 125 | Aug 2 | Zelle payment, no description | $120.00 |
| 141 | Aug 7 | PayPal transfer | $69.90 |
| 161 | Aug 13 | ATM cash withdrawal | $79.84 |

If the Venmo payments to Sam were for meals out, your eating-out totals are understated.

**Categories I had to choose:**
- **Shopping:** Target is counted as shopping, not groceries. Home Depot, IKEA and Barnes & Noble are also counted as shopping.
- **Groceries:** Costco is counted as groceries.
- **Entertainment:** Steam and "Spotify Concert" (which I'm reading as concert tickets).
- **Eating out:** Rustic Tap Brewery is included.

## Monthly totals by category

| Category | Jun | Jul | Aug | Total |
|---|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Eating out / coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Transport (rideshare, parking, oil change) | 327.78 | 137.45 | 135.59 | 600.82 |
| Health | 276.43 | 138.36 | 168.61 | 583.40 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Phone / internet | 143.13 | 143.13 | 143.13 | 429.39 |
| Fitness (gym charges) | 67.82 | 132.81 | 54.19 | 254.82 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| Uncategorised | 271.20 | 105.79 | 269.74 | 646.73 |
| **All spending** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |
| All spending except travel | 3,276.71 | 2,835.78 | 4,014.37 | |

## Against your two budgets

| | Jun | Jul | Aug |
|---|---:|---:|---:|
| Eating out / coffee (target $260) | $212.74 (82%) | $165.14 (64%) | **$398.69 (153%), $138.69 over** |
| Shopping (target $1,200) | $1,020.77 (85%) | $756.72 (63%) | **$1,218.31 (102%), $18.31 over** |
| Eating-out transactions | 10 | 9 | 18 |
| Average eating-out bill | $21.27 | $18.35 | $22.15 |

## Largest month-over-month changes

| Category | Months | Change |
|---|---|---:|
| Travel | Jul → Aug | +$1,631.82 (up from $0) |
| Shopping | Jul → Aug | +$461.59 (+61%) |
| Shopping | Jun → Jul | −$264.05 (−26%) |
| Eating out / coffee | Jul → Aug | +$233.55 (+141%) |
| Groceries | Jun → Jul | +$204.86 (+33%) |
| Gas | Jul → Aug | +$190.77 (+81%) |
| Transport | Jun → Jul | −$190.33 (−58%) |

## The three things I'd most want you to know

These cover June to August, which is what the log contains.

1. **Eating out went over budget in August because you went out more often, not because you spent more each time.** The number of meals out doubled from 9 to 18, while the average bill stayed around $18–22. The trip doesn't explain it: only one eating-out charge ($8.05 at Starbucks) falls on the trip dates. It also isn't a steady creep, since July was your lowest month. It's a sudden jump, spread across Chipotle, Luigi's, Rustic Tap and McDonald's. If September looks like August, you're right to be worried.

2. **Shopping is around your $1,200 limit and nowhere near $2,000, but Best Buy keeps growing.** August was over by only $18, and if Target counted as groceries it would be $1,090.51, under budget. The shopping store that's been climbing is Best Buy: $57, then $196, then $340, with two charges over $150 in August.

3. **The categories you aren't tracking grew more than the ones you are.** Without the trip, August was still $4,014, compared with about $2,800–3,300 in June and July. Gas tripled (×3.2, from $134 to $427), and groceries rose 57% (from $624 to $983). Together they were up $651.81 from June to August, nearly three times the $233.55 rise in eating out from July to August. Some of the gas may be connected to the trip, but it was already rising in July.

**Smaller things to check:**
- Planet Fitness charged $73.58 and then $59.23 in July (on Jul 2 and Jul 18), on top of the $9.99 app. That could be a double charge, and a gym membership that costs a different amount each month is odd.
- The two Delta charges may include a duplicate, as noted above.