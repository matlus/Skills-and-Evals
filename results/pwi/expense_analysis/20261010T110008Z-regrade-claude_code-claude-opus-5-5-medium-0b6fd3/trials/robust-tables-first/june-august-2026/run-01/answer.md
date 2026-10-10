Figures below come from `parse.py` in the scratchpad. It parses each line with regex, matches merchants (longest name first), removes duplicates and does all the math in `Decimal`.

**Monthly totals by category (2026, after cleaning)**

| Category | Jun | Jul | Aug | Q total |
|---|--:|--:|--:|--:|
| Dining & Coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Gas & Auto | 133.63 | 274.59 | 426.99 | 835.21 |
| Transport & Parking | 327.78 | 99.08 | 135.59 | 562.45 |
| Subscriptions & Bills | 198.58 | 198.58 | 198.58 | 595.74 |
| Fitness | 67.82 | 132.81 | 54.19 | 254.82 |
| Health & Pharmacy | 276.43 | 138.36 | 168.61 | 583.40 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Uncategorized | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |
| Total excl. uncategorized | 3,005.51 | 2,729.99 | 5,376.45 | 11,111.95 |

**Budget comparison**

| Target | Budget/mo | Jun | Jul | Aug |
|---|--:|--:|--:|--:|
| Eating out / coffee | 260.00 | 212.74: under by 47.26 (82%) | 165.14: under by 94.86 (64%) | **398.69: over by 138.69 (153%)** |
| Amazon / shopping | 1,200.00 | 1,020.77: under by 179.23 (85%) | 756.72: under by 443.28 (63%) | **1,218.31: over by 18.31 (102%)** |

**Largest month-over-month changes**

| Category | Change | Amount |
|---|---|--:|
| Travel | Jul → Aug | +1,631.82 |
| Shopping | Jul → Aug | +461.59 |
| Shopping | Jun → Jul | −264.05 |
| Dining & Coffee | Jul → Aug | +233.55 |
| Transport & Parking | Jun → Jul | −228.70 |
| Groceries | Jun → Jul | +204.86 |

---

## Data-cleaning notes

**Lines I couldn't parse:** None. All 198 entry lines produced a date, a known merchant and exactly one amount. I assumed every entry is from 2026, since the header says June through August and every date that includes a year says 2026. Some entries are out of order (for example, line 23 is 6/8 and comes before line 24, which is 6/7). Each one was sorted into its month by its own date.

**Uncategorized (8 entries, $646.73 total).** These are money moving out with no merchant, so I can't tell what they paid for:
- **ATM cash withdrawals:** 6/21 $100.00, 7/29 $30.79, 8/13 $79.84
- **Zelle payments:** 6/20 $102.66, 8/2 $120.00 (no payee)
- **Venmo – Sam:** 6/25 $68.54, 7/9 $75.00. There's a payee but no purpose. It could be splitting a meal, rent or anything else.
- **PayPal transfer:** 8/7 $69.90

If any of this was food or shopping, it isn't counted against your targets.

**Duplicates**
- **Removed:** Trader Joe's, Jul 22, $54.12. It's logged twice back to back (lines 111–112) with the same merchant, date and amount.
- **Kept, but please check:** two Delta Air Lines charges on 8/14, $412.60 and $450.60. The amounts differ, so they're more likely two tickets or a fare plus a change than a double entry. If one is a duplicate, August Travel drops by that amount.
- **Kept:** other same-merchant charges within a couple of days, such as Kroger 6/6 $114.37 and 6/8 $112.18, or Uber 8/14 and 8/16. All had different amounts.

**Refunds:** The REI return on 7/18 (−$68.00) is subtracted from July Shopping, not counted as a purchase. July REI nets to $41.19.

**Category choices that affect the targets**
- **Shopping** = Amazon, Target, Best Buy, Old Navy, REI, IKEA, Home Depot, Barnes & Noble. Amazon Prime counts as a subscription, not shopping. Walgreens and CVS are under Health & Pharmacy.
- **Dining & Coffee** = coffee shops, restaurants, fast food and Rustic Tap Brewery.
- **Planet Fitness:** the $9.99 "App" charges are under Subscriptions. The larger charges that change each time are under Fitness.
- **Entertainment:** Spotify Concert and Ticketmaster charges are here, not with subscriptions.

---

## Three things to know

1. **Your sense that eating out is creeping up is right, and August went over the target.** You spent $398.69 against $260, which is $138.69 over. That came after two months under it ($212.74 in June, $165.14 in July). The cause is how often you went: 18 dining and coffee transactions in August, against 10 in June and 9 in July. The trip doesn't explain it, since only one $8.05 Starbucks charge falls on the travel dates (8/14–8/17).

2. **Shopping went just over $1,200 in August, but it's nowhere near $2,000.** August came to $1,218.31, only $18.31 over, after $1,020.77 in June and $756.72 in July. That small overage depends on what you count as shopping. If you leave out the $68.71 IKEA purchase, August is under. The biggest August item was Best Buy at $340.20 across two purchases. Over the quarter, shopping averaged under $1,200 a month.

3. **August's total nearly doubled, mostly because of a trip.** August was $5,646.19, compared with $2,835.78 in July. Travel accounts for $1,631.82 of that: Delta $863.20, Marriott $486.27, Hertz $214.35 and airport parking $68.00. Apart from the trip, two everyday categories rose every month. Groceries went $624.34 → $829.20 → $982.79, and gas went $133.63 → $274.59 → $426.99.