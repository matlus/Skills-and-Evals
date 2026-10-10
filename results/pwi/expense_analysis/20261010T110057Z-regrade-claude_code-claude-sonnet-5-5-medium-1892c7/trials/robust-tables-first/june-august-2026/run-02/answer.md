Here are the tables, computed in `a.py`, a pandas script in the scratchpad.

**Monthly totals by category ($)**

| Category | Jun | Jul | Aug | Jul vs Jun | Aug vs Jul |
|---|---:|---:|---:|---:|---:|
| Bills & Subscriptions | 198.58 | 198.58 | 198.58 | 0.00 | 0.00 |
| Dining & Coffee | 212.74 | 165.14 | 398.69 | −47.60 | +233.55 |
| Entertainment | 143.42 | 135.51 | 160.88 | −7.91 | +25.37 |
| Gas | 133.63 | 236.22 | 426.99 | +102.59 | +190.77 |
| Groceries (incl. Costco) | 624.34 | 829.20 | 982.79 | +204.86 | +153.59 |
| Health & Fitness | 344.25 | 271.17 | 222.80 | −73.08 | −48.37 |
| Shopping (net of the REI return) | 1020.77 | 756.72 | 1218.31 | −264.05 | +461.59 |
| Transport (rideshare, parking, Jiffy Lube) | 327.78 | 137.45 | 135.59 | −190.33 | −1.86 |
| Travel | 0.00 | 0.00 | 1631.82 | 0.00 | +1631.82 |
| Uncategorized | 271.20 | 105.79 | 269.74 | −165.41 | +163.95 |
| **Total** | **3276.71** | **2835.78** | **5646.19** | −440.93 | +2810.41 |

**Budget comparison**

| Target | Jun | Jul | Aug |
|---|---|---|---|
| Eating out / coffee, under $260 | 212.74 (under by 47.26) | 165.14 (under by 94.86) | 398.69 (**over by 138.69**) |
| Shopping, about $1200 | 1020.77 (under by 179.23) | 756.72 (under by 443.28) | 1218.31 (**over by 18.31**) |

## Data-cleaning notes

- **Parsing:** All 198 entries parsed into a date, merchant and amount. I flagged none as unparseable. The dates came in about seven formats. I read `07-01` and `08-01` as month-day, and I took every entry as 2026.
- **Order:** Several entries are out of order, such as Jun 25 and Jun 28 and a Jun 10 entry in the middle of Jun 12–13. That doesn't matter for monthly totals.
- **Uncategorized, eight entries, $646.73 in total:**
  - Zelle Payment: Jun 20 for $102.66 and Aug 2 for $120.00. These are person-to-person transfers with no description.
  - ATM Cash Withdrawal: Jun 21 for $100.00, Jul 29 for $30.79 and Aug 13 for $79.84. This is cash with unknown use.
  - Venmo – Sam: Jun 25 for $68.54 and Jul 9 for $75.00. These are payments to a person called Sam, with no purpose given.
  - PayPal Transfer: Aug 7 for $69.90. The purpose isn't stated.
- **Duplicate removed:** Trader Joe's on Jul 22 for $54.12 appears twice with the same date and amount, so I counted it once.
- **Possible duplicate kept:** Delta Air Lines on Aug 14 appears at $412.60 and at $450.60. The amounts differ, so I kept both. If one is a re-entry or a typo, August Travel falls by that amount. Please check which is right.
- **Refund:** "Return processed – REI" on Jul 18 for −$68.00 is a credit. I netted it against Shopping in July, so July Shopping is $756.72 and not $824.72.
- **Category judgment calls:**
  - **Costco:** I put it in Groceries. If you treat it as general shopping, Shopping would be higher in every month. Costco totals $196.90 in June, $224.63 in July and $405.69 in August. That would put August Shopping well over $1200.
  - **Planet Fitness:** I counted the $9.99 "App" charges as Subscriptions. The larger charges ($54–$74, four of them) are in Health & Fitness. They're oddly large for a gym membership, so they may be worth checking.
  - **Spotify:** "Spotify Concert" entries are Entertainment, not the Spotify Premium subscription.
  - **Rustic Tap Brewery:** I counted it as dining. Without it, August Dining would still be over $260.
  - **Gas:** Gas covers Shell, Chevron and BP.
  - **Travel:** Travel covers Delta, Marriott, Hertz and airport parking.

## Three things to know

1. **Eating out went over budget in August.** June ($212.74) and July ($165.14) were under $260. August was $398.69, which is $138.69 over and up $233.55 on July. The increase comes from more visits: Luigi's Pizza went from nothing to three visits ($78.48), Chipotle doubled to $72.17, and Rustic Tap rose to $58.89. Your "creeping up" worry looks right for August, though June and July showed no creep.

2. **Shopping is just over $1200 in August, not near $2000.** It went $1020.77, then $756.72, then $1218.31, which is $18.31 over. August's jump of $461.59 is mostly Best Buy ($340.20 in total, against $195.60 in July). Old Navy, Barnes & Noble and Amazon ($221.15) also added to it. Because Costco is in Groceries, this figure is the optimistic reading.

3. **August's total spending is far higher than the other months, mainly because of one trip.** The total was $5646.19, against $3276.71 in June and $2835.78 in July. Travel was $1631.82 (Delta, Marriott, Hertz and airport parking). That is the largest month-over-month change by a wide margin, and none of it is covered by your two targets. The Delta entry has a possible duplicate, so that figure could be lower.