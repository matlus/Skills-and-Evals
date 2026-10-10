The script has run and I've checked all 198 parsed rows against the raw lines. Here are the results. Every figure comes from the Python script in section 2.

## 1. Computed tables

**Monthly totals by category (USD)**

| Category | Jun | Jul | Aug | Q total |
|---|---:|---:|---:|---:|
| Dining & Coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Gas & Auto | 133.63 | 274.59 | 426.99 | 835.21 |
| Rideshare & Parking | 327.78 | 99.08 | 135.59 | 562.45 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| Phone & Internet | 143.13 | 143.13 | 143.13 | 429.39 |
| Health & Fitness | 344.25 | 271.17 | 222.80 | 838.22 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| UNCATEGORIZED | 271.20 | 105.79 | 269.74 | 646.73 |
| **Categorized subtotal** | 3,005.51 | 2,729.99 | 5,376.45 | 11,111.95 |
| **All spending** | 3,276.71 | 2,835.78 | 5,646.19 | 11,758.68 |

**Budget comparison**

| Target | Month | Actual | Budget | Over/(under) | % of budget |
|---|---|---:|---:|---:|---:|
| Dining & Coffee | Jun | 212.74 | 260.00 | -47.26 | 82% |
| Dining & Coffee | Jul | 165.14 | 260.00 | -94.86 | 64% |
| Dining & Coffee | Aug | 398.69 | 260.00 | +138.69 | 153% |
| Shopping | Jun | 1,020.77 | 1,200.00 | -179.23 | 85% |
| Shopping | Jul | 756.72 | 1,200.00 | -443.28 | 63% |
| Shopping | Aug | 1,218.31 | 1,200.00 | +18.31 | 102% |

**Largest month-over-month changes**

| Category | Period | From | To | Change | % |
|---|---|---:|---:|---:|---:|
| Travel | Jul→Aug | 0.00 | 1,631.82 | +1,631.82 | n/a |
| Shopping | Jul→Aug | 756.72 | 1,218.31 | +461.59 | +61% |
| Shopping | Jun→Jul | 1,020.77 | 756.72 | -264.05 | -26% |
| Dining & Coffee | Jul→Aug | 165.14 | 398.69 | +233.55 | +141% |
| Rideshare & Parking | Jun→Jul | 327.78 | 99.08 | -228.70 | -70% |
| Groceries | Jun→Jul | 624.34 | 829.20 | +204.86 | +33% |
| UNCATEGORIZED | Jun→Jul | 271.20 | 105.79 | -165.41 | -61% |
| UNCATEGORIZED | Jul→Aug | 105.79 | 269.74 | +163.95 | +155% |

## 2. Data-cleaning notes

**Parsing:** Every line parsed: 198 transactions, none unparseable, all dated June–August 2026. Some lines needed assumptions, though:
- Dates with no year were treated as 2026.
- Dates like `06-01` were read as month-day.
- Lines out of order were placed by their own date. For example, line 23 (6/8 Kroger) sits above line 24 (Jun 7 Kroger).
- Amounts without a `$` were accepted.

**Uncategorized (8 entries, $646.73).** These are money moved with no description, so I can't tell what they paid for:

| Line | Date | What it is | Amount |
|---|---|---|---:|
| 47 | Jun 20 | Zelle payment | 102.66 |
| 51 | Jun 21 | ATM cash withdrawal | 100.00 |
| 60 | Jun 25 | Venmo to "Sam" | 68.54 |
| 91 | Jul 9 | Venmo to "Sam" | 75.00 |
| 117 | Jul 29 | ATM cash withdrawal | 30.79 |
| 125 | Aug 2 | Zelle payment | 120.00 |
| 141 | Aug 7 | PayPal transfer | 69.90 |
| 161 | Aug 13 | ATM cash withdrawal | 79.84 |

If any of these paid for meals (splitting a dinner with Sam, for example), the Dining & Coffee totals are too low.

**Category choices that affect the budgets:**
- Shopping = Amazon, Target, Best Buy, Old Navy, REI, IKEA, Home Depot and Barnes & Noble.
- Amazon Prime ($14.99/month) is under Subscriptions, not Shopping. Moving it into Shopping wouldn't change which months are over or under.
- Steam (June, $47.58) is under Entertainment. Counting it as Shopping would still leave June under $1,200.
- "Spotify Concert" is under Entertainment. The four charges are all different amounts, so they look like tickets, not the subscription.
- "Planet Fitness" (charges that vary each month) is under Health & Fitness. "Planet Fitness App" ($9.99) is under Subscriptions.
- Rustic Tap Brewery is counted as Dining & Coffee.

**Duplicates:**
- **Removed:** Trader Joe's, Jul 22, $54.12, entered on both line 111 and line 112. I kept one, which takes $54.12 out of July Groceries.
- **Flagged but kept:** Delta Air Lines on Aug 14, $412.60 (line 167) and $450.60 (line 168). The amounts differ, so these could be two tickets or a fare change. If one is a duplicate, August Travel is too high by that amount. This doesn't affect either budget.
- **Flagged but kept:** Kroger, Jun 6 $114.37 (line 22) and Jun 8 $112.18 (line 23). The amounts are close but not the same, so I kept both.
- The recurring bills (Netflix, Spotify Premium, iCloud, Prime, Planet Fitness App, Xfinity, Verizon) each appear exactly once a month. They aren't duplicates.

**Refunds:** Line 108, "Return processed – REI, 7/18, −$68.00", was subtracted from July Shopping, not counted as a purchase.

**Code** (the script is saved in the scratchpad as `analyze.py`):

```python
import re
from collections import defaultdict
from datetime import date

SRC = r"...\personal_expenses.txt"
YEAR = 2026
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), lambda m: date(int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2})\b"), lambda m: date(2000 + int(m[3]), int(m[1]), int(m[2]))),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})\b"), lambda m: date(YEAR, int(m[1]), int(m[2]))),
    (re.compile(r"\b(\d{2})-(\d{2})\b"), lambda m: date(YEAR, int(m[1]), int(m[2]))),
    (
        re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b", re.I),
        lambda m: date(YEAR, MONTHS[m[1][:3].lower()], int(m[2])),
    ),
]


def parse(line):
    s = line.strip().lstrip("- ").strip()
    d = None
    dspan = None
    for pat, fn in DATE_PATTERNS:
        m = pat.search(s)
        if m:
            d = fn(m)
            dspan = m.span()
            break
    amts = list(re.finditer(r"(-?)\$?(-?)(\d+\.\d{2})", s))  # dates never contain a decimal point
    if d is None or len(amts) != 1:
        return None  # -> flagged as unparsed
    am = amts[0]
    amt = float(am[3]) * (-1 if (am[1] or am[2]) else 1)
    rest = (s[: dspan[0]] + " " + s[dspan[1] :]).replace(am.group(0), " ")
    rest = re.sub(r"\(\s*\)", " ", rest)
    rest = re.sub(r"[|:(),]|--|\s-\s|^\s*-|-\s*$", " ", rest)
    return d, re.sub(r"\s+", " ", rest).strip(" -"), amt


CATS = {
    "Dining & Coffee": [
        "Local Coffee Co",
        "Starbucks",
        "Chipotle",
        "McDonald's",
        "Rustic Tap Brewery",
        "Panera Bread",
        "Sushi Kame",
        "Thai Orchid",
        "Bagel Corner",
        "Luigi's Pizza",
    ],
    "Shopping": ["Amazon", "Best Buy", "Target", "REI", "Old Navy", "Home Depot", "IKEA", "Barnes & Noble"],
    "Groceries": ["Trader Joe's", "Aldi", "Kroger", "Costco", "Whole Foods"],
    "Gas & Auto": ["Shell", "Chevron", "BP Gas", "Jiffy Lube"],
    "Rideshare & Parking": ["Lyft", "Uber", "City Parking Authority"],
    "Subscriptions": ["iCloud+ 200GB", "Amazon Prime", "Netflix", "Spotify Premium", "Planet Fitness App"],
    "Phone & Internet": ["Xfinity Internet", "Verizon Wireless"],
    "Health & Fitness": ["Planet Fitness", "Riverside Physical Therapy", "Walgreens", "CVS Pharmacy", "Dr. Hensley Dental Copay"],
    "Entertainment": ["AMC Theatres", "Steam", "Bowl-O-Rama", "Spotify Concert", "Ticketmaster"],
    "Travel": ["Delta Air Lines", "Airport Parking", "Marriott", "Hertz Rental Car"],
    "UNCATEGORIZED": ["Zelle Payment", "Venmo Sam", "ATM Cash Withdrawal", "PayPal Transfer"],
}
M2C = {m: c for c, ms in CATS.items() for m in ms}

rows, unparsed = [], []
for i, line in enumerate(open(SRC, encoding="utf-8").read().splitlines(), 1):
    if i <= 3 or not line.strip():
        continue
    p = parse(line)
    if p is None:
        unparsed.append((i, line))
        continue
    d, merchant, amt = p
    key = merchant.replace("Return processed ", "").strip()
    rows.append(dict(line=i, date=d, merchant=key, amount=amt, cat=M2C.get(key), raw=line, refund=amt < 0))
# (script also prints: unparsed lines, merchants with no category rule (none), out-of-range dates (none))

# exact duplicates (same date, merchant, amount): keep first; same-merchant entries <=2 days apart are reported for review
seen = defaultdict(list)
for r in rows:
    seen[(r["date"], r["merchant"], r["amount"])].append(r)
drop = {r["line"] for rs in seen.values() if len(rs) > 1 for r in rs[1:]}
clean = [r for r in rows if r["line"] not in drop]

# refunds are negative amounts, so summing nets them against their category
tot = defaultdict(float)
for r in clean:
    tot[(r["cat"], r["date"].month)] += r["amount"]
# ...then prints the category x month table, budget table vs {Dining & Coffee: 260, Shopping: 1200},
#    and month-over-month changes sorted by absolute size
```

## 3. Three things to know

1. **August was the only month over your eating-out/coffee target, by a wide margin.** You spent $398.69 against $260 (153%). June ($212.74) and July ($165.14) were both under. From July to August the total rose $233.55 (+141%), and the number of purchases went from 9 to 18. More visits, not pricier ones, drove the jump, which matches your worry that you weren't noticing it day to day. This figure leaves out the cash, Venmo and Zelle entries, so the real number could be higher.

2. **Shopping went slightly over $1,200 in August after two months well under.** August was $1,218.31 (102%), compared with $1,020.77 in June and $756.72 in July. The +$461.59 jump from July to August was the second-largest change of the quarter. Over the quarter, Shopping is your largest category at $2,995.80, so you guessed right that it's your biggest.

3. **Groceries and gas went up every month, even though they're unbudgeted.** Groceries rose from $624.34 to $829.20 to $982.79, and Gas & Auto from $133.63 to $274.59 to $426.99. The August trip (Travel, $1,631.82) is a one-time cost and the main reason August ($5,646.19) cost far more than June or July. The steady rise in groceries and gas is the trend that will keep going if you don't watch it.