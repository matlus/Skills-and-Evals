Over the quarter your eating-out total hit your target almost exactly, at 99.6%, but August alone was 53% over. Shopping came in under budget overall, though August went just over $1,200. The script is in the scratchpad as `analyze.py`. It uses only the Python standard library and does its sums in `Decimal`, so every number below comes from the code.

## 1. Parsing

- **All 198 lines parsed (lines 4–201) and none failed.** Lines with no year were set to 2026, since your note says June–August.
- **12 lines are out of date order**, for example the McDonald's "June 10" entry sits after a 6/12 line. Each was placed under its stated date, so nothing is lost.
- **Category choices you might decide differently:**
  - Amazon Prime counts as a subscription, not shopping.
  - Target, Home Depot and Barnes & Noble count as shopping.
  - "Spotify Concert" counts as entertainment (concert tickets), not the Spotify subscription.
  - Rustic Tap Brewery counts as eating out.

## 2. Uncategorized ($646.73 total, kept out of every budget category)

| Line | Date | Item | Amount | What it is |
|---|---|---|---|---|
| L47 | Jun 20 | Zelle Payment | 102.66 | Payment to a person, no reason given |
| L51 | Jun 21 | ATM Cash Withdrawal | 100.00 | Cash, spending not tracked |
| L60 | Jun 25 | Venmo – Sam | 68.54 | Payment to Sam, possibly a split bill |
| L91 | Jul 9 | Venmo – Sam | 75.00 | Payment to Sam |
| L117 | Jul 29 | ATM Cash Withdrawal | 30.79 | Cash (an odd amount, maybe a cash-back purchase) |
| L125 | Aug 2 | Zelle Payment | 120.00 | Payment to a person |
| L141 | Aug 7 | PayPal Transfer | 69.90 | Could be a purchase or a transfer |
| L161 | Aug 13 | ATM Cash Withdrawal | 79.84 | Cash |

If the Venmo payments to Sam were your share of meals, your eating-out numbers are understated.

## 3. Duplicates and refunds

- **Removed:** L112, Trader Joe's Jul 22 $54.12, an exact copy of L111.
- **Kept, but please check:**
  - **Delta Air Lines on Aug 14, $412.60 (L167) and $450.60 (L168).** These could be two tickets, or a rebooking with a refund still to come. If L168 shouldn't count, August travel drops from $1,631.82 to $1,181.22.
  - **Kroger on Jun 6 ($114.37) and Jun 8 ($112.18).** The dates and amounts differ, so these are probably two separate trips.
- **Refund:** REI −$68.00 on Jul 18 is subtracted from Shopping, so it lowers the July total instead of counting as a purchase.

## 4. Computed tables

**Monthly totals by category**
```
Category                        Jun        Jul        Aug     Q total     Avg/mo
Shopping                   1,020.77     756.72   1,218.31    2,995.80     998.60
Groceries                    624.34     829.20     982.79    2,436.33     812.11
Travel                         0.00       0.00   1,631.82    1,631.82     543.94
Gas & Transport              461.41     373.67     562.58    1,397.66     465.89
Eating Out & Coffee          212.74     165.14     398.69      776.57     258.86
Subscriptions & Bills        198.58     198.58     198.58      595.74     198.58
Health                       276.43     138.36     168.61      583.40     194.47
Entertainment                143.42     135.51     160.88      439.81     146.60
Fitness                       67.82     132.81      54.19      254.82      84.94
UNCATEGORIZED                271.20     105.79     269.74      646.73     215.58
TOTAL                      3,276.71   2,835.78   5,646.19   11,758.68   3,919.56
TOTAL excl. uncategorized  3,005.51   2,729.99   5,376.45
```

**Budget comparison**
```
Category             Month   Budget    Actual      Diff   % of budget
Eating Out & Coffee    Jun   260.00    212.74    -47.26      81.8%
Eating Out & Coffee    Jul   260.00    165.14    -94.86      63.5%
Eating Out & Coffee    Aug   260.00    398.69   +138.69     153.3%
Eating Out & Coffee      Q   780.00    776.57     -3.43      99.6%
Shopping               Jun 1,200.00  1,020.77   -179.23      85.1%
Shopping               Jul 1,200.00    756.72   -443.28      63.1%
Shopping               Aug 1,200.00  1,218.31    +18.31     101.5%
Shopping                 Q 3,600.00  2,995.80   -604.20      83.2%
```

**Eating out by merchant**
```
                         Jun      Jul      Aug     Total
Panera Bread           33.59    31.64    54.70    119.93
Chipotle               16.85    28.36    72.17    117.38
Sushi Kame             37.51    27.08    36.94    101.53
Local Coffee Co        59.30    24.01    11.95     95.26
Rustic Tap Brewery      8.37    13.03    58.89     80.29
Luigi's Pizza           0.00     0.00    78.48     78.48
Starbucks              26.82     0.00    42.71     69.53
Thai Orchid            22.70    31.65     0.00     54.35
McDonald's              7.60     0.00    32.72     40.32
Bagel Corner            0.00     9.37    10.13     19.50
Transaction count         10        9       18
```

**Shopping by merchant (REI is net of the refund)**
```
                         Jun      Jul      Aug     Total
Best Buy               56.99   195.60   340.20    592.79
Amazon                182.78   141.82   221.15    545.75
Target                204.81    88.28   127.80    420.89
REI                   189.97    41.19   132.82    363.98
IKEA                    0.00   289.83    68.71    358.54
Old Navy              176.23     0.00   171.25    347.48
Barnes & Noble         60.70     0.00   156.38    217.08
Home Depot            149.29     0.00     0.00    149.29
```

**Largest month-over-month changes**
```
Category              Period      From        To     Change     Pct
Travel              Jul->Aug      0.00  1,631.82  +1,631.82     new
Shopping            Jul->Aug    756.72  1,218.31    +461.59    +61%
Shopping            Jun->Jul  1,020.77    756.72    -264.05    -26%
Eating Out & Coffee Jul->Aug    165.14    398.69    +233.55   +141%
Groceries           Jun->Jul    624.34    829.20    +204.86    +33%
Gas & Transport     Jul->Aug    373.67    562.58    +188.91    +51%
Groceries           Jul->Aug    829.20    982.79    +153.59    +19%
Health              Jun->Jul    276.43    138.36    -138.07    -50%
```

## The three things I'd most want you to know

1. **Eating out went over because you ate out more often, not because meals cost more.** August had 18 eating-out purchases, about double June (10) and July (9). The average purchase barely changed: $21.27, then $18.35, then $22.15. This fits your worry that it's creeping up without you noticing. Most of the jump is ordinary local spending like Chipotle, Luigi's and Rustic Tap, not the trip. Only one Starbucks purchase fell on a trip day. The quarter landing at 99.6% of budget is only because June and July were low.

2. **August's total is high for two reasons, and only one is a one-off.** The trip (flights, Marriott, Hertz, airport parking) adds $1,631.82, and up to $450.60 of that might be a duplicate Delta charge. But even without travel and the uncategorized items, August was $3,744.63, compared with $3,005.51 in June and $2,729.99 in July. Groceries rose every month, up 57% from $624 to $983. Shopping went just over budget, with Best Buy alone growing from $57 to $196 to $340.

3. **Shopping, the category you worried about, isn't your real problem yet, but groceries is on track to rival it.** Shopping averaged $999 a month, well under $1,200, and nowhere near $2,000. Groceries isn't budgeted, but it averaged $812 a month and is still rising.

Also worth checking:
- **Planet Fitness:** you were charged twice in July ($73.58 and $59.23), and the gym charges vary from month to month ($67.82, $73.58, $59.23, $54.19), which is unusual for a fixed membership.
- **Uncategorized payments:** $646.73 in Zelle, Venmo, PayPal and ATM cash went to things the log doesn't name.