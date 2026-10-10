Here are the computed tables (code in `scratchpad/a.py`).

**Monthly totals by category (after cleaning)**

| Category | Jun | Jul | Aug | Total |
|---|---|---|---|---|
| Eating out/coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Health/Fitness | 344.25 | 271.17 | 222.80 | 838.22 |
| Phone/Internet | 143.13 | 143.13 | 143.13 | 429.39 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| Transport/Auto | 327.78 | 137.45 | 135.59 | 600.82 |
| Travel | 0.00 | 0.00 | 1,219.22 | 1,219.22 |
| Uncategorized | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total** | **3,276.71** | **2,835.78** | **5,233.59** | **11,346.08** |

**Budget comparison**

| Category | Target | Jun | Jul | Aug | Jun vs target | Jul vs target | Aug vs target |
|---|---|---|---|---|---|---|---|
| Eating out/coffee | 260 | 212.74 | 165.14 | 398.69 | −47.26 | −94.86 | **+138.69** |
| Shopping | 1,200 | 1,020.77 | 756.72 | 1,218.31 | −179.23 | −443.28 | **+18.31** |

**Largest month-over-month changes (dollars)**

| Category | Jun→Jul | Jul→Aug |
|---|---|---|
| Travel | 0.00 | +1,219.22 (new in Aug) |
| Shopping | −264.00 | +461.60 (+61.0%) |
| Eating out/coffee | −47.60 | +233.60 (+141.4%) |
| Gas | +102.60 (+76.8%) | +190.80 (+80.8%) |
| Groceries | +204.90 (+32.8%) | +153.60 (+18.5%) |
| Transport/Auto | −190.30 (−58.1%) | −1.90 |
| Uncategorized | −165.40 | +164.00 |

## Data-cleaning notes

**Parsing.** All 198 transaction lines parsed with no failures. I skipped the two header lines. Dates came in about eight formats, and I assumed 2026 throughout. I assigned months by the date on each line, not by position in the file. For example, "Panera Bread (07-01)" counts as July, and the out-of-order June entries land in the right month.

**Categorization judgment calls.** These are my assumptions, and they matter for the budget lines:
- **Costco** is in Groceries. If some of it is general merchandise, Shopping would be higher.
- **Rustic Tap Brewery** is in Eating out. It's $8–35 per visit, so it looks like bar or food spending.
- **Target** is in Shopping, though some of it may be groceries.
- **Planet Fitness** is split. The $9.99 "App" charge is a Subscription. The larger, varying charges ($54–$74) are in Health/Fitness.
- **Amazon Prime** is a Subscription. Plain "Amazon" is Shopping.
- **Spotify Concert** and **Steam** are in Entertainment.

**Uncategorized (8 entries, $646.73).** These are transfers and cash with no description, so I didn't guess a category:
- Zelle Payment: 6/20 $102.66 and 8/2 $120.00.
- ATM Cash Withdrawal: 6/21 $100.00, 7/29 $30.79 and 8/13 $79.84.
- Venmo – Sam: 6/25 $68.54 and 7/9 $75.00. This is a payment to a person.
- PayPal Transfer: 8/7 $69.90.

**Duplicates.**
- **Trader Joe's, Jul 22, $54.12** appears twice back to back. I removed one.
- **Delta Air Lines, Aug 14** appears twice, at $412.60 and $450.60. The amounts differ, so I can't tell whether it's a duplicate, a correction or two tickets. I kept $450.60 and dropped $412.60. If both are real, Travel is $412.60 higher. If $412.60 is the right one, Travel is $38.00 lower. This doesn't affect either budget line.
- I kept several near-matches because the amounts and dates differ. These were Kroger 6/6 and 6/8, and Ticketmaster 8/4 and 8/11.

**Refunds.** The only negative line is REI on 7/18, a −$68.00 return. I netted it against Shopping, which brings July Shopping to $756.72. Before the refund, July Shopping was $824.72.

## Three things to know

1. **Eating out blew through its $260 target in August.** It was $398.69, which is $138.69 over. June ($212.74) and July ($165.14) were both under. August jumped $233.60 (+141.4%) from July. The log has 18 eating-out entries in August versus 10 in June and 9 in July. So the main driver is more frequent visits, not pricier ones. Average cost per entry was about $22 in August, close to June's $21.
2. **Shopping stayed within the $1,200 target in June and July, then went slightly over in August.** June was $1,020.77 and July was $756.72. August was $1,218.31, which is $18.31 over. July's low figure was helped by the $68 REI return. August rose $461.60 (+61.0%) from July.
3. **Gas has gone up every month, but you don't have a target for it.** It went from $133.63 in June to $236.22 in July to $426.99 in August, about 3.2 times June's level. June may be undercounted because you noted some entries were logged late from memory. August also includes a trip (flight, hotel, rental car). I can't tell from the log whether the trip explains the jump.