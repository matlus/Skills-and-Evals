All figures below come from the Python scripts shown in section 2. All three months are 2026.

## 1. Computed tables

**Monthly totals by category** (exact duplicate removed, REI refund subtracted)

| Category | Jun | Jul | Aug | Q total |
|---|---:|---:|---:|---:|
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Health / Fitness | 344.25 | 271.17 | 222.80 | 838.22 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Eating Out / Coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Transport / Parking / Auto | 327.78 | 137.45 | 135.59 | 600.82 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Phone / Internet | 143.13 | 143.13 | 143.13 | 429.39 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| **Uncategorized** (transfers/cash) | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

**Budget comparison**

| Budget | Month | Actual | Target | Over / (under) | % of target |
|---|---|---:|---:|---:|---:|
| Eating out / coffee | Jun | 212.74 | 260 | (47.26) | 82% |
| Eating out / coffee | Jul | 165.14 | 260 | (94.86) | 64% |
| Eating out / coffee | Aug | **398.69** | 260 | **+138.69** | **153%** |
| Shopping | Jun | 1,020.77 | 1,200 | (179.23) | 85% |
| Shopping | Jul | 756.72 | 1,200 | (443.28) | 63% |
| Shopping | Aug | **1,218.31** | 1,200 | **+18.31** | **102%** |

**Largest month-over-month changes**

| Category | Change | From → To | Δ |
|---|---|---:|---:|
| Travel | Jul→Aug | 0.00 → 1,631.82 | +1,631.82 |
| Shopping | Jul→Aug | 756.72 → 1,218.31 | +461.59 (+61%) |
| Shopping | Jun→Jul | 1,020.77 → 756.72 | −264.05 (−26%) |
| Eating Out / Coffee | Jul→Aug | 165.14 → 398.69 | +233.55 (+141%) |
| Groceries | Jun→Jul | 624.34 → 829.20 | +204.86 (+33%) |
| Gas | Jul→Aug | 236.22 → 426.99 | +190.77 (+81%) |
| Transport / Parking | Jun→Jul | 327.78 → 137.45 | −190.33 (−58%) |

## 2. Data-cleaning notes

**Lines I couldn't parse:** None. All 198 transaction lines produced a date, merchant and amount. Lines 1–2 are the header and your note, not transactions. Some entries are out of order (for example, line 23 is Jun 8 but sits before Jun 7). I used the date written on each line, so the order doesn't matter.

**Uncategorized ($646.73, 5.5% of the quarter).** These are money moving out with no information about what it bought:

| Line | Date | What it is | Amount |
|---|---|---|---:|
| 47 | Jun 20 | Zelle payment, no recipient | 102.66 |
| 51 | Jun 21 | ATM cash withdrawal | 100.00 |
| 60 | Jun 25 | Venmo to "Sam", no purpose | 68.54 |
| 91 | Jul 9 | Venmo to "Sam", no purpose | 75.00 |
| 117 | Jul 29 | ATM cash withdrawal | 30.79 |
| 125 | Aug 2 | Zelle payment, no recipient | 120.00 |
| 141 | Aug 7 | PayPal transfer, no description | 69.90 |
| 161 | Aug 13 | ATM cash withdrawal | 79.84 |

If the Venmo payments to Sam are for shared meals, your eating-out numbers are understated.

**Duplicates:**
- **Removed: line 112.** Trader Joe's, Jul 22, $54.12, is identical to line 111 and sits right after it, so it's almost certainly a double entry. Removing it takes $54.12 off July groceries.
- **Kept, but please check: lines 167–168.** Two Delta Air Lines charges on Aug 14 ($412.60 and $450.60). The amounts differ, so they look like two tickets rather than a duplicate. If one is a fare that was charged again, August Travel is overstated by about $410–450.
- I compared every pair of entries with the same merchant and amount within 3 days, or the same merchant on the same day. Nothing else matched.

**Refunds:** Line 108, "Return processed – REI", −$68.00 on Jul 18. I subtracted it from July Shopping rather than counting it as a purchase. It most likely relates to the Jul 7 REI purchase of $109.19.

**Categorization choices you might want to change:**
- **Shopping:** Amazon, Target, Best Buy, Old Navy, IKEA, REI, Home Depot, Barnes & Noble.
- **Health / Fitness, not Shopping:** Walgreens and CVS.
- **Subscriptions:** Amazon Prime.
- **Groceries:** Costco, even though it can include household goods.
- **Eating out:** Rustic Tap Brewery.
- **Entertainment:** "Spotify Concert", since the amounts vary like ticket purchases rather than a subscription.
- **Two Planet Fitness merchants:** "Planet Fitness App" ($9.99 every month) is under Subscriptions. The separate "Planet Fitness" charges ($54–74, and two of them in July) are under Health / Fitness.

**The code** (full files are in the scratchpad as `parse.py` and `analyze.py`). This is the core of it:

```python
# parse.py – amount is the trailing money token; date can be in a trailing "(...)" or inline
AMT = re.compile(r"(-?)\$?(-?)(\d+\.\d{2})\s*$")
DATE_PATS = [
    (r"\b(2026)-(\d{2})-(\d{2})\b", lambda m: (int(m[2]), int(m[3]))),
    (r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", lambda m: (int(m[1]), int(m[2]))),
    (r"\b(\d{2})-(\d{2})\b", lambda m: (int(m[1]), int(m[2]))),
    (r"\b(Jan|...|Dec)[a-z]*\.?\s+(\d{1,2})\b", lambda m: (MON[m[1].lower()], int(m[2]))),
]
# any line whose cleaned merchant isn't in the explicit CATS map is reported as unparsed

# analyze.py
for a, b in combinations(rows, 2):  # duplicate scan
    dd = abs((a["date"] - b["date"]).days)
    if a["merch"] == b["merch"] and (a["amt"] == b["amt"] and dd <= 3 or dd == 0):
        print(...)
DROP = {112}
clean = [r for r in rows if r["line"] not in DROP]

tot = defaultdict(float)  # refunds are negative, so they net out
for r in clean:
    tot[(r["cat"], r["date"].month)] += r["amt"]

BUD = {"Eating Out / Coffee": 260, "Shopping": 1200}
for c, b in BUD.items():
    for m in months:
        v = round(tot[(c, m)], 2)
        print(c, m, v, b, v - b, 100 * v / b)

ch = [(tot[(c, b)] - tot[(c, a)], c, a, b) for c in cats for a, b in [(6, 7), (7, 8)]]
sorted(ch, key=lambda t: -abs(t[0]))[:8]
```

## 3. Three things worth knowing

1. **Eating out was within budget in June and July, then jumped to 153% of target in August.** It rose from $165 to $399. The average meal hardly changed ($18–22 per visit); what changed is how often you ate out, from 9 visits in July to 18 in August. You were right that it creeps up without you noticing: it's many small charges (Sushi Kame $6.45, Starbucks $8.05, McDonald's $9.21) rather than one big night out.

2. **August's total of $5,646 is nearly double July's, and the Aug 14–15 trip explains only part of it.** The trip cost $1,632 (Delta ×2, Marriott, Hertz, airport parking). Without it, August is still $4,014, about $1,180 more than July. The extra came from shopping, eating out, groceries and gas all rising at once. Shopping went just over its $1,200 target, mostly from Best Buy ($340 across two purchases) and Barnes & Noble ($156). Also check the two Delta charges, as noted above.

3. **Spending you aren't budgeting has grown steadily all quarter.** Groceries rose every month ($624 → $829 → $983, +57%). Gas more than tripled ($134 → $236 → $427). Some of August's gas is probably the trip, but July had already grown from June. Together, groceries and gas now cost more each month than your shopping target allows. They may deserve a target more than Shopping does, since Shopping has stayed at or under $1,200.