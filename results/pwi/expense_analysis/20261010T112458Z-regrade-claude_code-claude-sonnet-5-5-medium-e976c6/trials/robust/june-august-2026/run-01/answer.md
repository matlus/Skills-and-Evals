Code is in `scratchpad/an.py` (parse and categorize) and `an2.py` (tables). All figures below are program output.

## 1. Parsing
- **Parsed:** 198 of 198 transaction lines (log lines 4–201). I found no lines I couldn't parse.
- **Dates:** every date was inferred as 2026, since many entries have no year. All fall in June–August, matching your header.
- **Order:** the log is out of order in places, for example line 23 (6/8) sits before line 24 (6/7). I sorted by date, not log position.
- **Year not in the entry:** none of these is ambiguous, because I read `06-01` as MM-DD.

## 2. Categories and flags
- **Uncategorized, 8 transactions totaling $646.73.** These have no description, so I left them uncategorized:

  | Line | Date | Item | Amount |
  |---|---|---|---|
  | 47 | 6/20 | Zelle Payment | $102.66 |
  | 51 | 6/21 | ATM Cash Withdrawal | $100.00 |
  | 60 | 6/25 | Venmo – Sam | $68.54 |
  | 91 | 7/9 | Venmo – Sam | $75.00 |
  | 117 | 7/29 | ATM Cash Withdrawal | $30.79 |
  | 125 | 8/2 | Zelle Payment | $120.00 |
  | 141 | 8/7 | PayPal Transfer | $69.90 |
  | 161 | 8/13 | ATM Cash Withdrawal | $79.84 |

  This is about 5.5% of the quarter's spending, and I can't tell what any of it was for. The two Venmo payments to Sam look like a recurring item, maybe rent share or a split bill.
- **Judgment calls you may want to change:**
  - **Rustic Tap Brewery** is in Dining & coffee. It's a bar or brewery, and it totals $80.29 for the quarter.
  - **Costco** is in Groceries, and **Target** is in Shopping. Both are probably mixed baskets.
  - **Home Depot and IKEA** are in Shopping.
  - **Amazon Prime** is in Subscriptions, not Shopping.
  - **"Spotify Concert"** is Entertainment. It's an odd merchant name, and I'm taking it at face value.
  - **Planet Fitness** has a $9.99 "App" charge each month, which I put in Subscriptions. It also has four other charges of $54–$74 on irregular dates ($67.82, $73.58, $59.23, $54.19). They don't look like a flat membership, so I put them in Health & fitness and can't say what they are.
  - **Airport Parking** is in Travel, not Transport.

## 3. Duplicates and refunds
- **Removed one exact duplicate.** Line 112 repeats line 111: Trader Joe's on 7/22 for $54.12, same date and same amount to the cent. I dropped it, which lowers July groceries by $54.12.
- **Flagged but kept: Delta Air Lines on 8/14 for $412.60 (line 167) and $450.60 (line 168).** These are probably one flight entered twice, with one amount mistyped. I can't tell which is right, so both are in the totals. If one is a duplicate, August drops by $412.60 or $450.60, to $5,233.59 or $5,195.59. Check your card statement.
- **Recurring subscriptions and bills are not duplicates.** Each repeats once a month at the same amount.
- **One refund:** REI on 7/18 for −$68.00. I netted it against Shopping, which takes July from $824.72 gross to $756.72. It doesn't match the 7/7 REI purchase of $109.19, so it looks like a partial return.

## 4. Tables

**Monthly totals by category** (197 transactions after dedup)

| Category | Jun | Jul | Aug | Quarter | Avg/mo |
|---|---:|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 | 998.60 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 | 812.11 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 | 543.94 |
| Health & fitness | 344.25 | 271.17 | 222.80 | 838.22 | 279.41 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 | 265.61 |
| Dining & coffee | 212.74 | 165.14 | 398.69 | 776.57 | 258.86 |
| Uncategorized (transfer/cash) | 271.20 | 105.79 | 269.74 | 646.73 | 215.58 |
| Transport (rideshare/parking/auto) | 327.78 | 137.45 | 135.59 | 600.82 | 200.27 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 | 146.60 |
| Bills (internet/phone) | 143.13 | 143.13 | 143.13 | 429.39 | 143.13 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 | 55.45 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** | **3,919.56** |

**Against your budgets**

| Budget | Month | Spent | Target | Difference | % of target |
|---|---|---:|---:|---:|---:|
| Dining & coffee | Jun | 212.74 | 260 | −47.26 | 82% |
| Dining & coffee | Jul | 165.14 | 260 | −94.86 | 64% |
| Dining & coffee | **Aug** | **398.69** | 260 | **+138.69** | **153%** |
| Shopping | Jun | 1,020.77 | 1,200 | −179.23 | 85% |
| Shopping | Jul | 756.72 | 1,200 | −443.28 | 63% |
| Shopping | **Aug** | **1,218.31** | 1,200 | **+18.31** | **102%** |

How much these results depend on my category choices:
- Dining without Rustic Tap is $204.37, $152.11 and $339.80 for Jun, Jul and Aug. August is still over budget.
- Shopping without Home Depot and IKEA is $871.48, $466.89 and $1,149.60.
- Amazon alone is $182.78, $141.82 and $221.15.

**Largest month-over-month changes** (by category, in dollars)

| Category | Change | From | To | Change ($) | Change (%) |
|---|---|---:|---:|---:|---:|
| Travel | Jul→Aug | 0.00 | 1,631.82 | +1,631.82 | n/a |
| Shopping | Jul→Aug | 756.72 | 1,218.31 | +461.59 | +61% |
| Shopping | Jun→Jul | 1,020.77 | 756.72 | −264.05 | −26% |
| Dining & coffee | Jul→Aug | 165.14 | 398.69 | +233.55 | +141% |
| Groceries | Jun→Jul | 624.34 | 829.20 | +204.86 | +33% |
| Gas | Jul→Aug | 236.22 | 426.99 | +190.77 | +81% |
| Transport | Jun→Jul | 327.78 | 137.45 | −190.33 | −58% |
| Uncategorized | Jun→Jul | 271.20 | 105.79 | −165.41 | −61% |
| Uncategorized | Jul→Aug | 105.79 | 269.74 | +163.95 | +155% |
| Groceries | Jul→Aug | 829.20 | 982.79 | +153.59 | +19% |

Total spending changed by −$440.93 from Jun to Jul and by +$2,810.41 from Jul to Aug.

## 5. Three things to know

1. **August is a one-month spike, driven by the trip and by broad creep.** Total spending was $5,646 against $3,277 in June and $2,836 in July. Travel (flights, hotel, rental car, airport parking) explains $1,632 of that. Even without Travel, August is $4,014, which is $1,178 above July and $737 above June. Every variable category except Health and Transport rose in August: Shopping +$462, Dining +$234, Gas +$191, Groceries +$154, and the uncategorized transfers and cash +$164. Part of this may be trip-related, such as gas and restaurants on the road, but the log can't show that.

2. **Dining is where your worry about creeping spending showed up, though only in one month.** You were under $260 in June and July at 82% and 64% of target, then hit $398.69 in August (153%). Transaction count doubled from 9 to 18. The cause is more meals out, not coffee: coffee-only spending (Local Coffee, Starbucks, Bagel Corner) was $86, $33 and $65. Pizza, Chipotle and the brewery made up most of the jump. Rustic Tap also rose from $8 to $13 to $59. The quarter's average of $258.86 is just under your cap, but that average hides the August overrun.

3. **Shopping stayed within your $1,200 level until August, when it only just reached it, and the real money is in groceries and unclassified transfers.** Shopping was $1,021, $757 and $1,218. The $2,000 you were worried about hasn't happened, and Amazon is only $142–$221 a month. The August figure is mostly Best Buy ($340), Amazon, Old Navy and Barnes & Noble. Shopping is about as large as you thought, but it isn't what's growing fastest. Groceries rose every month ($624, $829, $983, +57% from June to August) and aren't budgeted. The $647 in cash, Zelle, Venmo and PayPal, which I can't classify, is larger than your whole quarter of Entertainment or Bills. Telling me what those eight items were would be the most useful next step.

Two things to verify with your statements: the Delta amount, and whether the Planet Fitness charges really are four separate non-membership payments.