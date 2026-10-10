I parsed all 198 transactions and found one exact duplicate, one refund and $646.73 of transfers and cash that I couldn't categorise. Eating out went over budget in August, and shopping was just over too.

**How I checked it:** the script is at `scratchpad/expenses.py` and the cleaned data at `scratchpad/clean_expenses.csv`. As a separate check, a plain sum of every dollar amount in the raw file came to $11,812.80. Taking off the $54.12 duplicate gives $11,758.68, which matches the parsed total.

## Data cleaning

**Parsing:** all 198 lines parsed into date, merchant and amount, and every merchant matched a known name, so no lines needed flagging. Some assumptions:
- Dates with no year are taken as 2026, which is what every line that does have a year says.
- `06-01`-style dates are read as month-day.
- Four entries are out of order (lines 32, 60, 62, 73). They're sorted by date now, and nothing was lost.

**Duplicates:**
- **Removed:** Trader Joe's on Jul 22 for $54.12 appears twice in a row (lines 111–112).
- **Kept, but please check:** Delta Air Lines on Aug 14 has two charges, $412.60 and $450.60. They're different amounts, so it could be two tickets, or a booking plus a rebooking where one should have been refunded.
- Kroger on Jun 6 ($114.37) and Jun 8 ($112.18) is not a duplicate. The amounts and dates differ.

**Refund:** "Return processed – REI" for −$68.00 on Jul 18 is subtracted from July's Shopping total, not counted as a purchase.

**Uncategorised ($646.73):** these are payments where I can't tell what the money went on.

| Line | Date | What it is | Amount |
|---|---|---|---|
| 47 | Jun 20 | Zelle payment (recipient unknown) | $102.66 |
| 51 | Jun 21 | ATM cash withdrawal | $100.00 |
| 60 | Jun 25 | Venmo to Sam | $68.54 |
| 91 | Jul 9 | Venmo to Sam | $75.00 |
| 117 | Jul 29 | ATM cash withdrawal | $30.79 |
| 125 | Aug 2 | Zelle payment (recipient unknown) | $120.00 |
| 141 | Aug 7 | PayPal transfer | $69.90 |
| 161 | Aug 13 | ATM cash withdrawal | $79.84 |

If any of the cash or the Venmo payments to Sam went on meals out, your eating-out totals below are too low.

**Category choices you might want to change:**
- **Eating out/coffee:** includes Rustic Tap Brewery.
- **Shopping:** Target is counted here, though it may include groceries. Amazon Prime is counted under Subscriptions, not Shopping.
- **Subscriptions vs. Health:** the "Planet Fitness App" charge ($9.99) is under Subscriptions. The separate in-person Planet Fitness charges ($54–74 a month) are under Health & fitness.
- **Entertainment:** includes "Spotify Concert", which I took to be concert tickets.

## Monthly totals by category

```
Category                         Jun       Jul       Aug    Q total
Shopping                     1020.77    756.72   1218.31    2995.80
Groceries                     624.34    829.20    982.79    2436.33
Travel                          0.00      0.00   1631.82    1631.82
Health & fitness              344.25    271.17    222.80     838.22
Gas                           133.63    236.22    426.99     796.84
Eating out/coffee             212.74    165.14    398.69     776.57
UNCATEGORIZED                 271.20    105.79    269.74     646.73
Rideshare/parking/auto        327.78    137.45    135.59     600.82
Subscriptions & bills         198.58    198.58    198.58     595.74
Entertainment                 143.42    135.51    160.88     439.81
-------------------------------------------------------------------
TOTAL                        3276.71   2835.78   5646.19   11758.68
```

## Budget vs. actual

```
Category             Month    Budget    Actual  Over/(Under)  % of budget
Eating out/coffee      Jun    260.00    212.74        -47.26        81.8%
Eating out/coffee      Jul    260.00    165.14        -94.86        63.5%
Eating out/coffee      Aug    260.00    398.69        138.69       153.3%
Shopping               Jun   1200.00   1020.77       -179.23        85.1%
Shopping               Jul   1200.00    756.72       -443.28        63.1%
Shopping               Aug   1200.00   1218.31         18.31       101.5%

Eating out/coffee transactions:  Jun 10 (avg $21.27) | Jul 9 (avg $18.35) | Aug 18 (avg $22.15)
```

## Largest month-over-month changes

```
Category                     Period      From        To    Change        %
Travel                     Jul->Aug      0.00   1631.82  +1631.82      n/a
Shopping                   Jul->Aug    756.72   1218.31   +461.59   +61.0%
Shopping                   Jun->Jul   1020.77    756.72   -264.05   -25.9%
Eating out/coffee          Jul->Aug    165.14    398.69   +233.55  +141.4%
Groceries                  Jun->Jul    624.34    829.20   +204.86   +32.8%
Gas                        Jul->Aug    236.22    426.99   +190.77   +80.8%
Rideshare/parking/auto     Jun->Jul    327.78    137.45   -190.33   -58.1%
```

## Three things I'd most want you to know

**1. Eating out went over budget in August because you went out more often, not because meals cost more.** You spent $398.69, which is 153% of the $260 target. You had 18 transactions, against 9–10 in June and July, and the average spend barely changed ($22 vs. $18–21). The August trip doesn't explain it: only one eating-out charge (Starbucks, $8.05) falls during the trip dates. Taking out the brewery charges would still leave you about $80 over. This matches your worry about not noticing it day to day.

**2. Shopping is under control on average, but August hit the limit and Best Buy is rising.** The three-month average is about $999, under your $1,200. August was $1,218, slightly over. It's spread across eight shops, and Amazon itself is only $140–220 a month. The one steady climb is Best Buy: $57, then $196, then $340.

**3. August cost $5,646, and the trip only explains part of that.** The trip (flights, Marriott, Hertz, airport parking) came to $1,632. Without it, August was still $4,014, compared with $3,277 in June and $2,836 in July. The other increases:
- **Groceries** have gone up every month: $624, then $829, then $983.
- **Gas** has roughly tripled: $134, then $236, then $427.
- **Things to check:** whether the second Delta charge ($450.60) should have been refunded, and what the $647 in transfers and cash was for. Those could change these figures.

Two smaller points: your bills and subscriptions are exactly $198.58 every month, and you pay both the $9.99 Planet Fitness App charge and a $54–74 Planet Fitness charge each month. That may be intended, but it's worth confirming you aren't being billed twice.