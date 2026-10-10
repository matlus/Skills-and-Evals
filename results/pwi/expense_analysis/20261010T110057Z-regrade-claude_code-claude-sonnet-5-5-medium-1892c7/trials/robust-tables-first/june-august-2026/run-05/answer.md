Tables below were computed from the 198 log lines, with one exact duplicate removed.

**Monthly totals by category (USD)**

| Category | Jun | Jul | Aug | Total |
|---|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Dining/Coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Uncategorized | 271.20 | 105.79 | 269.74 | 646.73 |
| Transport/Parking | 327.78 | 137.45 | 135.59 | 600.82 |
| Health | 276.43 | 138.36 | 168.61 | 583.40 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Bills (internet/phone) | 143.13 | 143.13 | 143.13 | 429.39 |
| Fitness | 77.81 | 142.80 | 64.18 | 284.79 |
| Subscriptions | 45.46 | 45.46 | 45.46 | 136.38 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

**Budget comparison**

| Target | Month | Spent | Target | Difference | % of target |
|---|---|---:|---:|---:|---:|
| Dining/Coffee | Jun | 212.74 | 260 | −47.26 | 82% |
| Dining/Coffee | Jul | 165.14 | 260 | −94.86 | 64% |
| Dining/Coffee | Aug | 398.69 | 260 | **+138.69** | 153% |
| Shopping | Jun | 1,020.77 | 1,200 | −179.23 | 85% |
| Shopping | Jul | 756.72 | 1,200 | −443.28 | 63% |
| Shopping | Aug | 1,218.31 | 1,200 | **+18.31** | 102% |

**Largest month-over-month changes**

| Category | Change | From | To | Difference |
|---|---|---:|---:|---:|
| Travel | Jul→Aug | 0.00 | 1,631.82 | +1,631.82 |
| Shopping | Jul→Aug | 756.72 | 1,218.31 | +461.59 |
| Shopping | Jun→Jul | 1,020.77 | 756.72 | −264.05 |
| Dining/Coffee | Jul→Aug | 165.14 | 398.69 | +233.55 |
| Groceries | Jun→Jul | 624.34 | 829.20 | +204.86 |
| Gas | Jul→Aug | 236.22 | 426.99 | +190.77 |

**Code:** `p.py` parses the lines and `c.py` categorizes and totals them. Both are in `$TEMP`, and `c.py` read the `rows.json` that `p.py` wrote.

## Data-cleaning notes

- **Unparsed lines:** none. All 198 lines had one date and one amount. Dates came in about eight formats, and I assumed 2026 throughout. Entries dated 07-01 and 07-02 count toward July even though they sit among the June lines.
- **Uncategorized (8 entries, 646.73 total):**
  - Zelle Payment: 6/20 $102.66 and 8/2 $120.00.
  - ATM Cash Withdrawal: 6/21 $100.00, 7/29 $30.79 and 8/13 $79.84.
  - Venmo - Sam: 6/25 $68.54 and 7/9 $75.00. This is a payment to a person, with no purpose given.
  - PayPal Transfer: 8/7 $69.90.
  - None has a description, so I left them uncategorized rather than guess. They are person-to-person transfers and cash.
- **Duplicates removed:** one exact repeat, Trader Joe's on Jul 22 for $54.12, which appeared twice. I counted it once.
- **Likely duplicate I kept:** Delta Air Lines on 8/14 appears as $412.60 and $450.60. It looks like a mis-entry and a re-entry, but I can't tell which is right, so both are in Travel. Travel is overstated by whichever amount is wrong.
- **Similar entries I kept as separate purchases:**
  - Kroger 6/6 $114.37 and 6/8 $112.18.
  - Two Barnes & Noble pairs.
  - Two BP Gas fill-ups in July.
  - Ticketmaster 8/4 $59.42 and 8/11 $59.68.
- **Refund:** the REI return on 7/18 of −$68.00 is netted against Shopping in July. It is not treated as a purchase.
- **Category judgment calls:**
  - Rustic Tap Brewery counts as Dining/Coffee. Moving it out would lower dining.
  - Spotify Concert counts as Entertainment, not as the Spotify subscription.
  - Both "Planet Fitness" and "Planet Fitness App" go to Fitness.
  - Home Depot, IKEA and Barnes & Noble count as Shopping.
  - Amazon Prime counts as a Subscription, not Shopping.
  - Walgreens and CVS count as Health.

## Three things to know

1. **Eating out was fine until August, then jumped past the target.** June ($212.74) and July ($165.14) were both under $260. August was $398.69, which is $138.69 over and 153% of target. That is not a gradual creep. The number of dining transactions went from 9 in July to 18 in August.
2. **Shopping stayed within slack until August, when it barely went over.** It was $1,020.77 in June and $756.72 in July (after the $68 REI refund). August was $1,218.31, which is $18.31 over the $1,200 line and up $461.59 from July. It is nowhere near $2,000, but August is the first month at or above the line.
3. **August was by far your biggest month, mainly because of a trip.** Total spending was $5,646.19, against $3,276.71 in June and $2,835.78 in July. Travel was $1,631.82 of that (Delta, Marriott, Hertz and airport parking), and it had no spending in the earlier months. Part of that figure is the double Delta entry. Neither budget target covers travel.