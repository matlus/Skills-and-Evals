| Category — USD | June 2026 | July 2026 | August 2026 | July − June | August − July |
|---|---:|---:|---:|---:|---:|
| Eating out / coffee | 212.74 | 165.14 | 398.69 | −47.60 | +233.55 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | −264.05 | +461.59 |
| Groceries | 624.34 | 829.20 | 982.79 | +204.86 | +153.59 |
| Gas | 133.63 | 236.22 | 426.99 | +102.59 | +190.77 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 0.00 | 0.00 |
| Internet / phone | 143.13 | 143.13 | 143.13 | 0.00 | 0.00 |
| Fitness | 67.82 | 132.81 | 54.19 | +64.99 | −78.62 |
| Entertainment | 143.42 | 135.51 | 160.88 | −7.91 | +25.37 |
| Health / pharmacy | 276.43 | 138.36 | 168.61 | −138.07 | +30.25 |
| Local transport / parking¹ | 327.78 | 137.45 | 135.59 | −190.33 | −1.86 |
| Travel | 0.00 | 0.00 | 1,631.82 | 0.00 | +1,631.82 |
| Uncategorized² | 271.20 | 105.79 | 269.74 | −165.41 | +163.95 |
| **Total recorded outflow²** | **3,276.71** | **2,835.78** | **5,646.19** | **−440.93** | **+2,810.41** |

| Month | Budgeted category | Net spending | Monthly target | Position against target |
|---|---|---:|---:|---|
| June | Eating out / coffee | $212.74 | $260.00 | $47.26 under |
| July | Eating out / coffee | $165.14 | $260.00 | $94.86 under |
| August | Eating out / coffee | $398.69 | $260.00 | $138.69 over |
| June | Shopping | $1,020.77 | ~$1,200.00 | $179.23 under |
| July | Shopping | $756.72 | ~$1,200.00 | $443.28 under |
| August | Shopping | $1,218.31 | ~$1,200.00 | $18.31 over |

**Data-cleaning notes**

- **Parsing:** All 198 transaction lines parsed successfully; none remain unparseable. Lines 1–2 are a title and introductory note, not transactions. Dates without a year use 2026, consistent with explicit dates in the log. Calculations group by parsed date, regardless of entry order.
- **Likely duplicate:** Lines 111–112 both record Trader Joe’s on July 22 for $54.12. I retained one and excluded the other provisionally, leaving 197 transactions. Matching date, merchant, and amount suggests duplication but does not prove it.
- **Refund:** Line 108 records a July 18 REI return of **−$68.00**. It reduces July shopping spending.
- **Possible duplicate requiring confirmation:** Lines 167–168 record Delta Air Lines on August 14 for $412.60 and $450.60. Because the amounts differ, both remain included.
- **Merchant assumptions:** Costco is classified as groceries; Target and Amazon purchases as shopping; Walgreens/CVS as health/pharmacy; breweries as eating out; Amazon Prime and Planet Fitness App as subscriptions. These are merchant-based classifications, since item details are absent. ¹Local transport includes Jiffy Lube vehicle maintenance.
- **²Uncategorized outflows:** The entries below remain separate from both budget categories. Transfers may move money between accounts, and withdrawn cash may later appear as purchases, so total recorded outflow is not necessarily total consumption spending.

| Source line | Date | Entry | Amount | What remains unknown |
|---|---|---|---:|---|
| 47 | 2026-06-20 | Zelle Payment | $102.66 | Recipient and purpose |
| 51 | 2026-06-21 | ATM Cash Withdrawal | $100.00 | How the cash was spent |
| 60 | 2026-06-25 | Venmo – Sam | $68.54 | Payment purpose |
| 91 | 2026-07-09 | Venmo – Sam | $75.00 | Payment purpose |
| 117 | 2026-07-29 | ATM Cash Withdrawal | $30.79 | How the cash was spent |
| 125 | 2026-08-02 | Zelle Payment | $120.00 | Recipient and purpose |
| 141 | 2026-08-07 | PayPal Transfer | $69.90 | Destination and purpose |
| 161 | 2026-08-13 | ATM Cash Withdrawal | $79.84 | How the cash was spent |

The following Python performs the parsing, classification, provisional deduplication, refund handling, aggregation, budget comparisons, and ranking of monthly changes. It uses `Decimal` for money and checks that category totals reconcile to retained transactions.

<details>
<summary>Show calculation code</summary>

```python
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
import re


@dataclass(frozen=True)
class Transaction:
    line: int
    day: date
    description: str
    merchant: str
    amount: Decimal
    category: str


groups: dict[str, str] = {
    "Eating out / coffee": (
        "Local Coffee Co|Chipotle|McDonald's|Rustic Tap Brewery|Panera Bread|Starbucks|Sushi Kame|Thai Orchid|Bagel Corner|Luigi's Pizza"
    ),
    "Shopping": ("Amazon|Best Buy|Home Depot|Target|REI|Barnes & Noble|Old Navy|IKEA"),
    "Groceries": "Trader Joe's|Aldi|Kroger|Costco|Whole Foods",
    "Gas": "Shell|Chevron|BP Gas",
    "Subscriptions": ("iCloud+ 200GB|Amazon Prime|Netflix|Planet Fitness App|Spotify Premium"),
    "Internet / phone": "Xfinity Internet|Verizon Wireless",
    "Fitness": "Planet Fitness",
    "Entertainment": ("Steam|Spotify Concert|AMC Theatres|Bowl-O-Rama|Ticketmaster"),
    "Health / pharmacy": ("Riverside Physical Therapy|Walgreens|CVS Pharmacy|Dr. Hensley Dental Copay"),
    "Local transport / parking": ("Lyft|Uber|City Parking Authority|Jiffy Lube"),
    "Travel": "Delta Air Lines|Airport Parking|Marriott|Hertz Rental Car",
    "Uncategorized": ("Zelle Payment|ATM Cash Withdrawal|Venmo - Sam|PayPal Transfer"),
}
lookup: dict[str, str] = {merchant: category for category, names in groups.items() for merchant in names.split("|")}

date_re: re.Pattern[str] = re.compile(
    r"2026-\d{2}-\d{2}|\b\d{1,2}[/-]\d{1,2}(?:/26)?\b|"
    r"\b(?:June|Jun\.?|July|Jul\.?|August|Aug\.?)\s+\d{1,2}\b",
    re.I,
)
amount_re: re.Pattern[str] = re.compile(r"(?<!\w)-?\$?\d+\.\d{2}(?!\d)")


def parse_day(token: str) -> date:
    if token.startswith("2026-"):
        return date.fromisoformat(token)
    if token[0].isdigit():
        parts: list[str] = re.split(r"[/-]", token)
        return date(2026, int(parts[0]), int(parts[1]))
    name, day = token.replace(".", "").split()
    month: int = {"jun": 6, "jul": 7, "aug": 8}[name[:3].lower()]
    return date(2026, month, int(day))


def parse_line(line_no: int, line: str) -> Transaction:
    match: re.Match[str] | None = date_re.search(line)
    if match is None:
        raise ValueError("No recognizable date")
    day: date = parse_day(match.group())
    remainder: str = line[: match.start()] + line[match.end() :]
    amounts: list[re.Match[str]] = list(amount_re.finditer(remainder))
    if len(amounts) != 1:
        raise ValueError("Expected exactly one amount")
    amount_match: re.Match[str] = amounts[0]
    amount: Decimal = Decimal(amount_match.group().replace("$", ""))
    description: str = (remainder[: amount_match.start()] + remainder[amount_match.end() :]).strip(" -:|,()")
    merchant: str = re.sub(r"^Return processed\s*-\s*", "", description)
    if merchant not in lookup:
        raise ValueError("Unrecognized merchant: " + merchant)
    return Transaction(line_no, day, description, merchant, amount, lookup[merchant])


parsed: list[Transaction] = []
failures: list[tuple[int, str, str]] = []
metadata: list[tuple[int, str]] = []

for line_no, line in enumerate(Path("personal_expenses.txt").read_text().splitlines(), 1):
    if not line.strip():
        continue
    if line.startswith(("misc expenses", "(started keeping")):
        metadata.append((line_no, line))
        continue
    try:
        parsed.append(parse_line(line_no, line))
    except ValueError as error:
        failures.append((line_no, line, str(error)))

seen: dict[tuple[date, str, Decimal], Transaction] = {}
clean: list[Transaction] = []
duplicates: list[tuple[Transaction, Transaction]] = []

for transaction in parsed:
    key: tuple[date, str, Decimal] = (transaction.day, transaction.merchant, transaction.amount)
    if key in seen:
        duplicates.append((seen[key], transaction))
    else:
        seen[key] = transaction
        clean.append(transaction)


def zero() -> Decimal:
    return Decimal("0.00")


totals: defaultdict[tuple[int, str], Decimal] = defaultdict(zero)
for transaction in clean:
    totals[(transaction.day.month, transaction.category)] += transaction.amount

monthly: dict[int, Decimal] = {month: sum((totals[(month, category)] for category in groups), zero()) for month in (6, 7, 8)}
assert sum(monthly.values(), zero()) == sum((transaction.amount for transaction in clean), zero())

print("Category | June | July | August | July-June | August-July")
for category in groups:
    june, july, august = (totals[(month, category)] for month in (6, 7, 8))
    print(
        category,
        june,
        july,
        august,
        july - june,
        august - july,
        sep=" | ",
    )
print(
    "Total",
    monthly[6],
    monthly[7],
    monthly[8],
    monthly[7] - monthly[6],
    monthly[8] - monthly[7],
    sep=" | ",
)

# The two monthly targets specified in budget_notes.txt:
targets: dict[str, Decimal] = {
    "Eating out / coffee": Decimal("260.00"),
    "Shopping": Decimal("1200.00"),
}
for month in (6, 7, 8):
    for category, target in targets.items():
        print(
            "Budget",
            month,
            category,
            totals[(month, category)],
            target,
            totals[(month, category)] - target,
        )

changes: list[tuple[Decimal, int, str, Decimal]] = []
for month in (7, 8):
    for category in groups:
        delta: Decimal = totals[(month, category)] - totals[(month - 1, category)]
        changes.append((abs(delta), month, category, delta))
print("Largest absolute changes:", sorted(changes, reverse=True)[:5])

print("Parsed, retained:", len(parsed), len(clean))
print("Unparseable:", failures)
print("Metadata:", metadata)
print("Uncategorized:", [transaction for transaction in clean if transaction.category == "Uncategorized"])
print("Duplicates:", duplicates)
print("Refunds:", [transaction for transaction in clean if transaction.amount < 0])
```

</details>

**The three things I’d most want you to know**

1. **Eating out / coffee is the clearest departure from your targets.** August spending was **$398.69**, **$138.69 over** your $260 target, following two months under it. The July-to-August increase was **$233.55**.
2. **Shopping rose sharply, but August was only slightly above your approximate target.** It increased **$461.59** from July to **$1,218.31**, or **$18.31 over** roughly $1,200. June and July were under that target; July includes the REI refund.
3. **Travel accounts for the largest monthly category change.** It rose from **$0.00 in July to $1,631.82 in August**, alongside total recorded outflow increasing **$2,810.41**. Confirming the two Delta entries would help validate that increase. Travel has no stated budget target, so this is a change to understand, rather than a budget judgment.