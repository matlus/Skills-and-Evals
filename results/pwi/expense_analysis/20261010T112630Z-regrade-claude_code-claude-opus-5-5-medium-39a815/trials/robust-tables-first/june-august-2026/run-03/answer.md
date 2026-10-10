All figures below come from `analyze.py`. Key excerpts are at the end of this reply.

### Monthly totals by category (USD, refunds netted, one duplicate removed)

| Category | Jun | Jul | Aug | Q total |
|---|--:|--:|--:|--:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Health & Fitness | 344.25 | 271.17 | 222.80 | 838.22 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Eating Out & Coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Transport & Parking | 327.78 | 137.45 | 135.59 | 600.82 |
| Subscriptions & Bills | 198.58 | 198.58 | 198.58 | 595.74 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| **Total (categorized)** | **3,005.51** | **2,729.99** | **5,376.45** | **11,111.95** |
| Uncategorized (cash/transfers) | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total incl. uncategorized** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

### Budget comparison

| Budget | Month | Target | Actual | Diff | % of target | Status |
|---|---|--:|--:|--:|--:|---|
| Eating Out & Coffee | Jun | 260.00 | 212.74 | −47.26 | 82% | under |
| Eating Out & Coffee | Jul | 260.00 | 165.14 | −94.86 | 64% | under |
| Eating Out & Coffee | Aug | 260.00 | 398.69 | **+138.69** | 153% | **OVER** |
| Shopping | Jun | 1,200.00 | 1,020.77 | −179.23 | 85% | under |
| Shopping | Jul | 1,200.00 | 756.72 | −443.28 | 63% | under |
| Shopping | Aug | 1,200.00 | 1,218.31 | **+18.31** | 102% | **OVER** |

### Largest month-over-month changes

| Category | Period | From | To | Change |
|---|---|--:|--:|--:|
| Travel | Jul→Aug | 0.00 | 1,631.82 | +1,631.82 |
| Shopping | Jul→Aug | 756.72 | 1,218.31 | +461.59 (+61%) |
| Shopping | Jun→Jul | 1,020.77 | 756.72 | −264.05 (−26%) |
| Eating Out & Coffee | Jul→Aug | 165.14 | 398.69 | +233.55 (+141%) |
| Groceries | Jun→Jul | 624.34 | 829.20 | +204.86 (+33%) |
| Gas | Jul→Aug | 236.22 | 426.99 | +190.77 (+81%) |
| Transport & Parking | Jun→Jul | 327.78 | 137.45 | −190.33 (−58%) |

---

## Data-cleaning notes

**Parsing:** All 198 transaction lines parsed into a date, merchant and amount. Only lines 1–2 failed, and they're the title and your intro note, not transactions. Dates without a year were treated as 2026. Formats like `06-01` were read as month-day.

During cleaning, my first run read the separator dash in lines like `Kroger - $114.37` as a minus sign, which turned about 100 purchases into refunds. I fixed it so a minus only counts when it's attached to the number (`-$68.00`). The tables above use the corrected run.

**Uncategorized (8 entries, $646.73, left out of both budgets):**

| Date | Entry | Amount | What it is |
|---|---|--:|---|
| Jun 20 | Zelle Payment | 102.66 | Person-to-person transfer, no recipient or reason |
| Jun 21 | ATM Cash Withdrawal | 100.00 | Cash; what it was spent on isn't recorded |
| Jun 25 | Venmo – Sam | 68.54 | Payment to Sam, no reason given (could be splitting a meal, rent, etc.) |
| Jul 9 | Venmo – Sam | 75.00 | Same as above |
| Jul 29 | ATM Cash Withdrawal | 30.79 | Cash |
| Aug 2 | Zelle Payment | 120.00 | Transfer, no recipient |
| Aug 7 | PayPal Transfer | 69.90 | Could be a purchase or a transfer to a person; can't tell |
| Aug 13 | ATM Cash Withdrawal | 79.84 | Cash |

If any of this went to restaurants or shopping, those two budget numbers are understated.

**Duplicates:**
- **Removed:** Trader Joe's, Jul 22, $54.12. It appears twice in a row on lines 111–112 with the same date, merchant and amount.
- **Kept but worth checking:** two Kroger entries, Jun 6 for $114.37 (line 22) and Jun 8 for $112.18 (line 23). They're next to each other in the log, two days apart, and within 2% of each other. Since you mentioned entering some things from memory a day or two late, this could be one trip logged twice. If so, June groceries are $112.18 too high.
- **Kept but worth checking:** two Delta Air Lines charges on Aug 14, $412.60 and $450.60. These could be two tickets or a rebooking where the first fare was refunded. If it was a rebooking, Travel is $412.60 too high.

**Refunds:** There's one: the REI return on Jul 18 for −$68.00. I subtracted it from July Shopping instead of counting it as a purchase. Nothing else in the log is negative.

**Category choices that affect the budgets:**
- Shopping includes Amazon, Target, Best Buy, Old Navy, REI, IKEA, Barnes & Noble and Home Depot. Target ($420.89 for the quarter) may include groceries.
- Amazon Prime is under Subscriptions, not Shopping.
- "Spotify Concert" is under Entertainment (tickets), and Spotify Premium is under Subscriptions.
- Planet Fitness in-person charges ($54–$74 each, in Health & Fitness) are separate from the $9.99 app subscription.

---

## Three things you should know about this quarter

1. **Eating out jumped in August because you went out more often, not because meals cost more.** You logged 18 eating-out purchases in August versus 10 in June and 9 in July. The average purchase stayed about the same ($21.27, $18.35 and $22.15). That's the "creeping up without noticing" you were worried about: the total rose from $165 to $399, 153% of your $260 target.

2. **Groceries are rising every month, and you aren't budgeting them.** They went from $624 to $829 to $983, up 57% from June to August. They're now about the same size as Shopping ($998 a month on average). Shopping only went over its target once, by $18 in August, and Best Buy accounts for a lot of it ($592.79 for the quarter, $340.20 in August).

3. **August spending was almost double the other months, and the trip is only part of it.** The trip (Delta, Marriott, Hertz, airport parking) cost $1,631.82. Even without it, August categorized spending was $3,744.63, compared with an average of $2,867.75 for June and July. Gas also rose every month ($134 → $236 → $427). Separately, $647 left as cash and transfers that the log doesn't explain.

---

### Code (key parts of `analyze.py`, saved in the session scratchpad)

```python
AMOUNT_RE = re.compile(r"(-?)\$?(-?)(\d+\.\d{2})(?!\d)")   # minus only if attached to the number
DATE_PATTERNS = [ISO yyyy-mm-dd, m/d/yy, m/d, mm-dd, "Jun. 3"/"August 4" ...]  # first match wins

def parse(line):
    am = list(AMOUNT_RE.finditer(line))[-1]
    amount = float(am[3]) * (-1 if (am[1] or am[2]) else 1)
    # strip the amount, find the date, and the leftover text is the merchant

MERCHANT_TO_CAT = {...}   # explicit merchant -> category map; Zelle/ATM/Venmo/PayPal -> UNCATEGORIZED

# exact duplicates: same (date, merchant, amount) -> keep the first, drop the rest
# near-duplicates: same merchant, <=2 days apart, amounts within 10% -> reported, not dropped
clean = [r for r in rows if r["line"] not in dupe_lines]

tot = defaultdict(float)
for r in clean:
    tot[(r["cat"], r["date"].month)] += r["amount"]   # refunds are negative, so they net out

budgets = {"Eating Out & Coffee": 260.0, "Shopping": 1200.0}
for c, b in budgets.items():
    for m in (6, 7, 8):
        v = tot[(c, m)]; print(c, m, b, v, v - b, f"{100*v/b:.0f}%")

changes = [(c, a, b, tot[(c, b)] - tot[(c, a)]) for c in cats for a, b in [(6, 7), (7, 8)]]
changes.sort(key=lambda x: -abs(x[3]))
```