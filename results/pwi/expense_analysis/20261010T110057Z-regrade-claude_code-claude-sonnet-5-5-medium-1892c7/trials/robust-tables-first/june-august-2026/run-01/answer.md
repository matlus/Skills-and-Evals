Both tables come from the script `b.py`, which I ran on the parsed log (June–August 2026, 197 transactions after cleaning).

**Monthly totals by category (USD)**

| Category | Jun | Jul | Aug | Total |
|---|---:|---:|---:|---:|
| Dining & Coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Entertainment | 95.84 | 135.51 | 160.88 | 392.23 |
| Gas & Auto | 133.63 | 274.59 | 426.99 | 835.21 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Health & Fitness | 344.25 | 271.17 | 222.80 | 838.22 |
| Phone & Internet | 143.13 | 143.13 | 143.13 | 429.39 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Subscriptions | 103.03 | 55.45 | 55.45 | 213.93 |
| Transport & Parking | 327.78 | 99.08 | 135.59 | 562.45 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Uncategorized | 271.20 | 105.79 | 269.74 | 646.73 |
| **All** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

**Budget comparison**

| Target | Month | Spent | Target | Difference | % of target |
|---|---|---:|---:|---:|---:|
| Eating out / coffee | Jun | 212.74 | 260 | −47.26 | 82% |
| | Jul | 165.14 | 260 | −94.86 | 64% |
| | Aug | 398.69 | 260 | **+138.69** | 153% |
| Shopping (incl. Amazon) | Jun | 1,020.77 | 1,200 | −179.23 | 85% |
| | Jul | 756.72 | 1,200 | −443.28 | 63% |
| | Aug | 1,218.31 | 1,200 | **+18.31** | 102% |

**Largest month-over-month changes**

| Category | Change | From → To | Delta | % |
|---|---|---|---:|---:|
| All | Jul→Aug | 2,835.78 → 5,646.19 | +2,810.41 | +99% |
| Travel | Jul→Aug | 0.00 → 1,631.82 | +1,631.82 | n/a |
| Shopping | Jul→Aug | 756.72 → 1,218.31 | +461.59 | +61% |
| All | Jun→Jul | 3,276.71 → 2,835.78 | −440.93 | −13% |
| Shopping | Jun→Jul | 1,020.77 → 756.72 | −264.05 | −26% |
| Dining & Coffee | Jul→Aug | 165.14 → 398.69 | +233.55 | +141% |
| Transport & Parking | Jun→Jul | 327.78 → 99.08 | −228.70 | −70% |
| Groceries | Jun→Jul | 624.34 → 829.20 | +204.86 | +33% |

## Data-cleaning notes

**Parsing.** All 198 entries parsed into a date, merchant and amount. No line needed to be flagged as unparseable. Dates came in about eight formats. Entries without a year are assumed to be 2026, and every date falls between Jun 1 and Aug 31.

**Judgment calls on categories.** These are my assumptions, so correct me if any are wrong.
- Costco is in Groceries, though it may include household goods.
- Home Depot and IKEA are in Shopping.
- "Spotify Concert" is Entertainment (tickets), not the Spotify subscription.
- "Planet Fitness App" ($9.99) is a Subscription. "Planet Fitness" with varying amounts ($54–$74) is Health & Fitness.
- Rustic Tap Brewery is in Dining.

**Uncategorized (8 entries, $646.73).** These have no description of what they were for.

| Date | Entry | Amount |
|---|---|---:|
| Jun 20 | Zelle Payment | 102.66 |
| Jun 21 | ATM Cash Withdrawal | 100.00 |
| Jun 25 | Venmo – Sam | 68.54 |
| Jul 9 | Venmo – Sam | 75.00 |
| Jul 29 | ATM Cash Withdrawal | 30.79 |
| Aug 2 | Zelle Payment | 120.00 |
| Aug 7 | PayPal Transfer | 69.90 |
| Aug 13 | ATM Cash Withdrawal | 79.84 |

Together these are two Zelle payments, two Venmo payments to Sam, one PayPal transfer and three cash withdrawals. Some of that cash may have been dining or shopping spend, so the two budget figures could be understated.

**Duplicates.**
- Removed one exact duplicate: Trader Joe's, Jul 22, $54.12 (line 112, entered twice in a row).
- Kept but flagged: two Delta Air Lines charges on Aug 14, $412.60 and $450.60. They could be a typo or a corrected entry, or two separate tickets. I kept both. If one is a mistake, Travel and the August total are lower by $412.60 or $450.60.
- Checked and kept as separate purchases: Kroger on Jun 6 and Jun 8, and Barnes & Noble on Aug 17 and Aug 20. The amounts are close but the dates differ.

**Refunds.** There is one: "Return processed – REI" on Jul 18, −$68.00. I netted it against Shopping, so July Shopping is reduced by $68.00.

## Three things to know

1. **Eating out jumped past its target in August, after two months under it.** It went from $212.74 to $165.14 to $398.69, which is $138.69 over the $260 target. That is a jump rather than a steady creep. August has 18 dining transactions, against 10 in June and 9 in July, while the average per transaction stayed near $22. The extra spend comes from eating out more often, not from pricier meals.

2. **Shopping was well under $1,200 in June and July, then landed just over it in August.** August was $1,218.31, which is $18.31 over, after $1,020.77 and $756.72. It is a borderline call that depends on categorization. Without Home Depot and IKEA, August is $1,149.60, under the target. The jump from July is $461.59, and Best Buy ($340.20) was the largest August shopping merchant. Nothing here is near the $2,000 you were worried about.

3. **August's total spending nearly doubled because of one trip, not a change in daily habits.** The total went from $2,835.78 to $5,646.19, and Travel was $1,631.82 of that (flights, hotel, rental car and airport parking, Aug 14–15). Without Travel, August is $4,014.37. That is still higher than July, mostly because of the dining and shopping increases above. The unresolved Delta pair also accounts for up to $450.60 of the August total.