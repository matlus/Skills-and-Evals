Here are the tables, computed by `an.py` in the scratchpad. It parses the log, categorizes it, drops the duplicate, and totals by month.

**Monthly totals by category (USD, duplicate removed, refund netted)**

| Category | Jun | Jul | Aug | Total |
|---|---:|---:|---:|---:|
| Shopping | 1020.77 | 756.72 | 1218.31 | 2995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2436.33 |
| Travel | 0.00 | 0.00 | 1631.82 | 1631.82 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Eating out/coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Uncategorized | 271.20 | 105.79 | 269.74 | 646.73 |
| Auto & Transport | 327.78 | 137.45 | 135.59 | 600.82 |
| Healthcare | 276.43 | 138.36 | 168.61 | 583.40 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Bills & Phone | 143.13 | 143.13 | 143.13 | 429.39 |
| Health & Fitness | 67.82 | 132.81 | 54.19 | 254.82 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| **All** | **3276.71** | **2835.78** | **5646.19** | **11758.68** |

**Budget comparison**

| Target | Month | Spent | Target | Difference | % of target |
|---|---|---:|---:|---:|---:|
| Eating out/coffee | Jun | 212.74 | 260 | −47.26 | 82% |
| Eating out/coffee | Jul | 165.14 | 260 | −94.86 | 64% |
| Eating out/coffee | Aug | 398.69 | 260 | **+138.69** | 153% |
| Shopping | Jun | 1020.77 | 1200 | −179.23 | 85% |
| Shopping | Jul | 756.72 | 1200 | −443.28 | 63% |
| Shopping | Aug | 1218.31 | 1200 | **+18.31** | 102% |

**Largest month-over-month changes**

| Category | Change | From → To | Delta |
|---|---|---|---:|
| Travel | Jul→Aug | 0.00 → 1631.82 | +1631.82 |
| Shopping | Jul→Aug | 756.72 → 1218.31 | +461.59 |
| Shopping | Jun→Jul | 1020.77 → 756.72 | −264.05 |
| Eating out/coffee | Jul→Aug | 165.14 → 398.69 | +233.55 |
| Groceries | Jun→Jul | 624.34 → 829.20 | +204.86 |
| Gas | Jul→Aug | 236.22 → 426.99 | +190.77 |

## Data-cleaning notes

**Unparsed lines:** None. All 198 transaction lines gave exactly one amount and one date inside Jun 1–Aug 31, 2026. Dates with no year were assumed to be 2026. Lines 1–2 are a header and intro, so I skipped them.

**Uncategorized (8 entries, $646.73).** None of these has a description, so I didn't guess:
- **Zelle payments:** Jun 20 for $102.66 and Aug 2 for $120.00. These are person-to-person transfers.
- **Venmo to "Sam":** Jun 25 for $68.54 and Jul 9 for $75.00. These are transfers to a person, possibly shared costs or rent.
- **PayPal transfer:** Aug 7 for $69.90. I can't tell whether it's a purchase or a transfer.
- **ATM cash withdrawals:** Jun 21 for $100.00, Jul 29 for $30.79 and Aug 13 for $79.84. This is cash with unknown use.

**Duplicates:**
- **Removed:** Trader Joe's, Jul 22, $54.12 appears twice (lines 111 and 112). I counted it once.
- **Kept, but uncertain:** Delta Air Lines on Aug 14 appears at $412.60 and $450.60. The amounts differ, so I can't tell whether it's two tickets or a re-entry with a typo. Both are in the totals. If one is an error, August travel and the August total drop by that amount. The lower figure would leave travel at 1219.22. Neither budget target is affected.
- **Not duplicates:** The remaining same-merchant, same-amount repeats were all recurring subscriptions or more than 3 days apart.

**Refund:** The REI return on Jul 18 (−$68.00) is netted against Shopping, so it reduces July instead of counting as a purchase.

**Category judgment calls:**
- **Eating out/coffee** includes the Rustic Tap Brewery (a bar), coffee shops and fast food.
- **Costco** is under Groceries. If you treat it as shopping, Shopping becomes 1217.67 in June, 981.35 in July and 1624.00 in August.
- **Shopping** includes Amazon, Target, Best Buy, REI, Old Navy, IKEA, Home Depot and Barnes & Noble.
- **Amazon Prime** and the **Planet Fitness App** ($9.99) are Subscriptions. The larger, varying "Planet Fitness" charges are Health & Fitness.
- **Spotify Concert**, Ticketmaster, AMC, Steam and Bowl-O-Rama are Entertainment.

## Three things to know

1. **August was a different kind of month.** It totaled 5646.19, against 3276.71 in June and 2835.78 in July. The biggest driver was a new Travel category at 1631.82: Delta, Marriott, Hertz and airport parking around Aug 14–15. Gas also rose, from 236.22 to 426.99.
2. **Eating out/coffee went over target only in August.** It was 398.69 against 260 (153%), after 212.74 in June and 165.14 in July. August had 18 dining entries against 10 in June and 9 in July, and the average ticket barely changed. The overage comes from eating out more often. It may be linked to the trip.
3. **Shopping hit the $1200 line in August but isn't close to $2000.** It was 1218.31 (18.31 over), after 756.72 in July and 1020.77 in June. If Costco counts as shopping, August is 1624.00, which is over $1200 but still under $2000.