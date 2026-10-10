| Category — net dollars | June 2026 | July 2026 | August 2026 | Period total |
|---|---:|---:|---:|---:|
| Groceries | $624.34 | $829.20 | $982.79 | $2,436.33 |
| Eating out / coffee | $212.74 | $165.14 | $398.69 | $776.57 |
| Shopping | $1,068.35 | $756.72 | $1,218.31 | $3,043.38 |
| Subscriptions | $55.45 | $55.45 | $55.45 | $166.35 |
| Internet / phone | $143.13 | $143.13 | $143.13 | $429.39 |
| Gas | $133.63 | $236.22 | $426.99 | $796.84 |
| Fitness | $67.82 | $132.81 | $54.19 | $254.82 |
| Entertainment | $95.84 | $135.51 | $160.88 | $392.23 |
| Healthcare / pharmacy | $276.43 | $138.36 | $168.61 | $583.40 |
| Local transport / parking¹ | $327.78 | $137.45 | $135.59 | $600.82 |
| Travel | $0.00 | $0.00 | $1,631.82 | $1,631.82 |
| Uncategorized² | $271.20 | $105.79 | $269.74 | $646.73 |
| **Total logged net outflows** | **$3,276.71** | **$2,835.78** | **$5,646.19** | **$11,758.68** |

| Budget category | Month | Net spending | Monthly target | Spending minus target | Comparison |
|---|---|---:|---:|---:|---|
| Eating out / coffee | June | $212.74 | $260.00 | −$47.26 | Under |
| Eating out / coffee | July | $165.14 | $260.00 | −$94.86 | Under |
| Eating out / coffee | August | $398.69 | $260.00 | +$138.69 | Over |
| Shopping | June | $1,068.35 | ~$1,200.00 | −$131.65 | Below reference |
| Shopping | July | $756.72 | ~$1,200.00 | −$443.28 | Below reference |
| Shopping | August | $1,218.31 | ~$1,200.00 | +$18.31 | Above reference |

Largest category changes, ranked by absolute dollar change:

| Category | Transition | Previous month | Next month | Change |
|---|---|---:|---:|---:|
| Travel | July → August | $0.00 | $1,631.82 | +$1,631.82 |
| Shopping | July → August | $756.72 | $1,218.31 | +$461.59 |
| Shopping | June → July | $1,068.35 | $756.72 | −$311.63 |

**Data-cleaning notes**

- **Parsing:** All 198 transaction lines parsed successfully. No transaction lines were unparseable. The title, introductory note, and blank line were excluded. Dates without a year were assigned **2026**, consistent with explicitly dated entries. Transactions were grouped by their written dates regardless of file order.
- **Category assumptions:** Costco was classified as groceries; Target, Amazon purchases, Home Depot, and Steam as shopping; Walgreens and CVS as healthcare/pharmacy. These are merchant-based classifications because item details are unavailable. Amazon Prime was classified as a subscription, Spotify Concert as entertainment, and breweries as eating out. ¹Local transport / parking also includes Jiffy Lube.
- **Exact duplicate:** Lines **111–112** both read `Trader Joe's (Jul. 22) - $54.12`. I provisionally excluded the second entry, leaving **197 transactions**. If these were separate purchases, July groceries and total outflows each need another **$54.12**.
- **Possible duplicate retained:** Lines **167–168** record Delta Air Lines on **August 14**, for **$412.60** and **$450.60**. Different amounts make automatic removal unjustified; both remain in travel pending confirmation.
- **Refund:** Line **108**, `Return processed - REI (7/18/26) - -$68.00`, was applied as **−$68.00 to July shopping**. Formatting separators elsewhere were not interpreted as negative signs.
- **²Uncategorized:** The entries below remain separate from shopping, dining, and other categories. They are included in logged outflows, but transfers and withdrawals do not establish what was ultimately spent—or whether money merely moved between your accounts. Consequently, total logged outflows are not a definitive consumption total.

| Source line | Date | Entry | Amount | What remains unknown |
|---|---|---|---:|---|
| 47 | June 20 | Zelle Payment | $102.66 | Recipient and purpose |
| 51 | June 21 | ATM Cash Withdrawal | $100.00 | Subsequent cash use |
| 60 | June 25 | Venmo – Sam | $68.54 | Payment purpose |
| 91 | July 9 | Venmo – Sam | $75.00 | Payment purpose |
| 117 | July 29 | ATM Cash Withdrawal | $30.79 | Subsequent cash use |
| 125 | August 2 | Zelle Payment | $120.00 | Recipient and purpose |
| 141 | August 7 | PayPal Transfer | $69.90 | Destination and purpose |
| 161 | August 13 | ATM Cash Withdrawal | $79.84 | Subsequent cash use |
| **Total** | | | **$646.73** | |

The Python computation used date extraction, exact merchant mapping, integer cents, duplicate exclusion, and signed refund amounts. This reproduces the tables and ranks all category changes:

```python
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

date_re = re.compile(
    r"\b2026-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/26)?\b|"
    r"\b\d{2}-\d{2}\b|"
    r"\b(?:June|Jun\.?|July|Jul\.?|August|Aug\.?)\s+\d{1,2}\b",
    re.I,
)

groups = {
    "Groceries": ["Trader Joe's", "Aldi", "Kroger", "Costco", "Whole Foods"],
    "Eating out / coffee": [
        "Local Coffee Co",
        "Chipotle",
        "McDonald's",
        "Rustic Tap Brewery",
        "Panera Bread",
        "Starbucks",
        "Sushi Kame",
        "Thai Orchid",
        "Bagel Corner",
        "Luigi's Pizza",
    ],
    "Shopping": [
        "Steam",
        "Amazon",
        "Best Buy",
        "Home Depot",
        "Target",
        "REI",
        "Barnes & Noble",
        "Old Navy",
        "IKEA",
    ],
    "Subscriptions": [
        "iCloud+ 200GB",
        "Amazon Prime",
        "Netflix",
        "Planet Fitness App",
        "Spotify Premium",
    ],
    "Internet / phone": ["Xfinity Internet", "Verizon Wireless"],
    "Gas": ["Shell", "Chevron", "BP Gas"],
    "Fitness": ["Planet Fitness"],
    "Entertainment": [
        "Spotify Concert",
        "AMC Theatres",
        "Bowl-O-Rama",
        "Ticketmaster",
    ],
    "Healthcare / pharmacy": [
        "Riverside Physical Therapy",
        "Walgreens",
        "CVS Pharmacy",
        "Dr. Hensley Dental Copay",
    ],
    "Local transport / parking": [
        "Lyft",
        "Uber",
        "City Parking Authority",
        "Jiffy Lube",
    ],
    "Travel": [
        "Delta Air Lines",
        "Airport Parking",
        "Marriott",
        "Hertz Rental Car",
    ],
    "Uncategorized": [
        "Zelle Payment",
        "ATM Cash Withdrawal",
        "Venmo - Sam",
        "PayPal Transfer",
    ],
}
category_for = {merchant: category for category, merchants in groups.items() for merchant in merchants}

transactions, failures = [], []
for line_no, raw in enumerate(Path("personal_expenses.txt").read_text().splitlines(), 1):
    if not raw.strip():
        continue
    if raw.startswith(("misc expenses", "(started keeping track")):
        continue
    try:
        matches = list(date_re.finditer(raw))
        if len(matches) != 1:
            raise ValueError("expected exactly one date")
        match = matches[0]
        token = match.group()
        if token.startswith("2026-"):
            date = datetime.strptime(token, "%Y-%m-%d").date()
        elif "/" in token:
            month, day, *_ = token.split("/")
            date = datetime(2026, int(month), int(day)).date()
        elif "-" in token:
            month, day = token.split("-")
            date = datetime(2026, int(month), int(day)).date()
        else:
            name, day = token.replace(".", "").split()
            month = {"jun": 6, "jul": 7, "aug": 8}[name[:3].lower()]
            date = datetime(2026, month, int(day)).date()

        rest = raw[: match.start()] + raw[match.end() :]
        amounts = list(re.finditer(r"(?<![\w.])-?\$?\d+\.\d{2}(?!\d)", rest))
        if len(amounts) != 1:
            raise ValueError("expected exactly one amount")
        amount = amounts[0]
        cents = int(Decimal(amount.group().replace("$", "")) * 100)
        merchant = (rest[: amount.start()] + rest[amount.end() :]).strip(" -:|,()")
        merchant = re.sub(r"^Return processed\s*-\s*", "", merchant).strip(" -:|,()")
        if merchant not in category_for:
            raise ValueError(f"unmapped merchant: {merchant}")

        transactions.append(
            (
                line_no,
                date.isoformat(),
                merchant,
                cents,
                category_for[merchant],
            )
        )
    except ValueError as exc:
        failures.append((line_no, raw, str(exc)))

totals = defaultdict(int)
seen, kept, duplicates = {}, [], []
for transaction in transactions:
    line_no, date, merchant, cents, category = transaction
    key = (date, merchant, cents)
    if key in seen:
        duplicates.append((transaction, seen[key]))
        continue
    seen[key] = line_no
    kept.append(transaction)
    totals[(date[:7], category)] += cents

months = ["2026-06", "2026-07", "2026-08"]


def money(cents):
    return f"{Decimal(cents) / 100:.2f}"


for category in groups:
    values = [totals[(month, category)] for month in months]
    print(category, *map(money, values), money(sum(values)), sep=" | ")

monthly = [sum(totals[(month, category)] for category in groups) for month in months]
print("TOTAL", *map(money, monthly), money(sum(monthly)), sep=" | ")

# Targets transcribed from budget_notes.txt; shopping is approximate.
for category, target in [("Eating out / coffee", 26000), ("Shopping", 120000)]:
    for month in months:
        net = totals[(month, category)]
        print(category, month, money(net), money(target), money(net - target), sep=" | ")

changes = [
    (totals[(months[i], category)] - totals[(months[i - 1], category)], months[i - 1], months[i], category) for i in [1, 2] for category in groups
]
for difference, previous, current, category in sorted(changes, key=lambda row: abs(row[0]), reverse=True):
    print(category, previous, current, money(difference), sep=" | ")

print("Unparseable:", failures)
print("Duplicates:", duplicates)
print("Uncategorized:", [t for t in kept if t[4] == "Uncategorized"])
print("Refunds:", [t for t in kept if t[3] < 0])

assert not failures
assert len(transactions) == 198 and len(kept) == 197
assert sum(t[3] for t in kept) == sum(monthly) == 1175868
assert totals[("2026-08", "Eating out / coffee")] - 26000 == 13869
assert totals[("2026-08", "Shopping")] - 120000 == 1831
assert monthly[2] - monthly[1] == 281041
```

**The three things I’d most want you to know**

1. **August eating out / coffee is the clearest budget concern:** **$398.69**, or **$138.69 over** your $260 target. June and July were both under it, so the pattern is an August jump rather than a steady monthly climb.

2. **Shopping is your largest category across the period, at $3,043.38.** August reached **$1,218.31**, only **$18.31 above** your approximate $1,200 reference. Its **$461.59 increase from July** deserves attention, but your dining target is the more substantial August miss.

3. **August’s overall increase was led by travel.** Logged net outflows rose **$2,810.41 from July**, including **$1,631.82 of travel**, the largest category change. Confirm the two Delta entries before treating that travel total as settled.