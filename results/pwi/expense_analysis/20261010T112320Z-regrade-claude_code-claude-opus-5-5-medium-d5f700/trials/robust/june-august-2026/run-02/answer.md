I parsed, cleaned and analyzed the whole log. Of 200 lines, 198 are transactions and all of them parsed. One was removed as a duplicate and one is a refund, which leaves 197 in the analysis. August went over both budgets.

## Computed tables

These are copied from the script output (`analyze.py`, run on `rows.json` from `parse.py`). I didn't do any of the arithmetic by hand.

**Monthly totals by category** (refunds netted, duplicate removed)
```
Category                           2026-06    2026-07    2026-08    Q total
Shopping                           1020.77     756.72    1218.31    2995.80
Groceries                           624.34     829.20     982.79    2436.33
Travel                                0.00       0.00    1631.82    1631.82
Health & Fitness                    344.25     271.17     222.80     838.22
Gas & Auto                          133.63     274.59     426.99     835.21
Dining & Coffee                     212.74     165.14     398.69     776.57
UNCATEGORIZED (transfer/cash)       271.20     105.79     269.74     646.73
Subscriptions & Utilities           198.58     198.58     198.58     595.74
Rideshare & Parking                 327.78      99.08     135.59     562.45
Entertainment                       143.42     135.51     160.88     439.81
TOTAL                              3276.71    2835.78    5646.19   11758.68
TOTAL excl. Travel                 3276.71    2835.78    4014.37   10126.86
```

**Budget comparison**
```
Category              Month    Budget    Actual      Diff   % used  Status
Dining & Coffee     2026-06    260.00    212.74    -47.26     82%   under
Dining & Coffee     2026-07    260.00    165.14    -94.86     64%   under
Dining & Coffee     2026-08    260.00    398.69   +138.69    153%   OVER
Shopping            2026-06   1200.00   1020.77   -179.23     85%   under
Shopping            2026-07   1200.00    756.72   -443.28     63%   under
Shopping            2026-08   1200.00   1218.31    +18.31    102%   OVER
```
Dining detail: June had 10 transactions (average $21.27), July had 9 (average $18.35) and August had 18 (average $22.15).

**Largest month-over-month changes**
```
Category                       Period                From        To    Change       %
Travel                         Jul -> Aug            0.00   1631.82  +1631.82     new
Shopping                       Jul -> Aug          756.72   1218.31   +461.59    +61%
Shopping                       Jun -> Jul         1020.77    756.72   -264.05    -26%
Dining & Coffee                Jul -> Aug          165.14    398.69   +233.55   +141%
Rideshare & Parking            Jun -> Jul          327.78     99.08   -228.70    -70%
Groceries                      Jun -> Jul          624.34    829.20   +204.86    +33%
Uncategorized                  Jun -> Jul          271.20    105.79   -165.41    -61%
Uncategorized                  Jul -> Aug          105.79    269.74   +163.95   +155%
Groceries                      Jul -> Aug          829.20    982.79   +153.59    +19%
Gas & Auto                     Jul -> Aug          274.59    426.99   +152.40    +56%
```

## Data cleaning notes

- **Parsing:** I found 7 different date formats. I assumed the year is 2026 wherever it's missing. Lines that are out of order (for example, line 60 is dated Jun 25 but comes after Jun 28) are grouped by their written date, not by where they sit in the file. My first parse missed 24 lines in the `Merchant - $X (date)` format. I fixed that and checked those lines by hand. Lines 1–2 are the header and note.
- **Duplicate removed:** Trader Joe's on Jul 22 for $54.12 appears twice (lines 111–112). I dropped one copy.
- **Possible duplicates I kept:**
  - Two Delta Air Lines charges on Aug 14, $412.60 and $450.60 (lines 167–168). They could be two tickets or a fare change, so I couldn't treat them as a duplicate. Check your card statement: if one is a mistake, Travel is overstated by about $400.
  - Kroger on Jun 6 ($114.37) and Jun 8 ($112.18). The amounts differ, so these are probably two real shopping trips.
- **Refund:** REI −$68.00 on Jul 18 is subtracted from Shopping, not counted as a purchase.
- **Uncategorized ($646.73 total):**
  - Zelle: $102.66 on Jun 20 and $120.00 on Aug 2
  - Venmo to Sam: $68.54 on Jun 25 and $75.00 on Jul 9
  - PayPal: $69.90 on Aug 7
  - ATM cash: $100.00 on Jun 21, $30.79 on Jul 29 and $79.84 on Aug 13

  None of these say what they were for. If the Venmo payments to Sam were for shared meals, they would add to Dining.
- **Category choices you might disagree with:**
  - Costco is in Groceries, not Shopping.
  - Target is in Shopping.
  - Amazon Prime is in Subscriptions, not Shopping.
  - "Spotify Concert" is treated as concert tickets (Entertainment), not the $11.99 Spotify subscription.
  - Steam is in Entertainment.
  - Rustic Tap Brewery is in Dining.
  - The August trip (Delta, Marriott, Hertz, airport parking) is its own Travel category, so it doesn't count toward Shopping.

## Three things to know

1. **Eating out went from under budget to 53% over in August, because you went out more often.** You had 18 dining transactions in August, compared with 9–10 in June and July. The average spend per visit barely changed ($18–22). The visits are spread across the whole month, not grouped around the trip, so this is the "creeping up without noticing" you were worried about. If the Venmo payments to Sam were for meals, the real number is higher.

2. **Shopping is within your $1,200 limit, but Amazon isn't the main driver.** August was only $18.31 over, and June and July were under. The biggest shopping merchant for the quarter is Best Buy ($592.79, $340.20 of it in August), then Amazon ($545.75) and Target ($420.89). Most of August's $461.59 jump came from Best Buy, Barnes & Noble ($156.38) and Old Navy, not Amazon.

3. **The categories you don't budget for are rising, and they're bigger than the two you do.** Not counting the trip, total spending went from $3,276.71 to $2,835.78 to $4,014.37. Groceries rose every month ($624 → $829 → $983) and are now about as large as Shopping. Gas & Auto more than tripled ($134 → $427). If spending keeps rising, these two are worth a budget number.

Two more things to check against your statements:
- **The two Delta charges** described above.
- **Planet Fitness:** you pay $9.99 a month for the app plus a separate gym charge that varies ($54–74), and there were two gym charges in July. A gym membership normally doesn't change amount from month to month.

The scripts are in the scratchpad folder as `parse.py` and `analyze.py` if you want to change a category and re-run.