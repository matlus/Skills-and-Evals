| Category — USD, net of refunds | June 2026 | July 2026 | August 2026 | Period total |
|---|---:|---:|---:|---:|
| Eating out / coffee | 212.74 | 165.14 | 398.69 | 776.57 |
| Shopping | 1,020.77 | 756.72 | 1,218.31 | 2,995.80 |
| Groceries | 624.34 | 829.20 | 982.79 | 2,436.33 |
| Gas | 133.63 | 236.22 | 426.99 | 796.84 |
| Local transport / auto | 327.78 | 137.45 | 135.59 | 600.82 |
| Subscriptions | 55.45 | 55.45 | 55.45 | 166.35 |
| Internet / phone | 143.13 | 143.13 | 143.13 | 429.39 |
| Fitness | 67.82 | 132.81 | 54.19 | 254.82 |
| Entertainment | 143.42 | 135.51 | 160.88 | 439.81 |
| Health / pharmacy | 276.43 | 138.36 | 168.61 | 583.40 |
| Travel | 0.00 | 0.00 | 1,631.82 | 1,631.82 |
| Uncategorized transfers / cash | 271.20 | 105.79 | 269.74 | 646.73 |
| **Total logged net amounts** | **3,276.71** | **2,835.78** | **5,646.19** | **11,758.68** |

| Budget comparison | Monthly target | June actual | June − target | July actual | July − target | August actual | August − target |
|---|---:|---:|---:|---:|---:|---:|---:|
| Eating out / coffee | Under $260 | $212.74 | −$47.26 | $165.14 | −$94.86 | $398.69 | +$138.69 |
| Shopping | Approximately $1,200 | $1,020.77 | −$179.23 | $756.72 | −$443.28 | $1,218.31 | +$18.31 |

The largest category changes across either monthly transition, ranked by absolute dollar change:

| Category | Transition | Change |
|---|---|---:|
| Travel | July → August | +$1,631.82 |
| Shopping | July → August | +$461.59 |
| Shopping | June → July | −$264.05 |
| Eating out / coffee | July → August | +$233.55 |
| Groceries | June → July | +$204.86 |

**Data-cleaning notes**

All **198 transaction lines** parsed into date, description, and signed amount; **197 remain** after excluding the likely duplicate. No transaction lines were unparseable. The opening title, explanatory note, and blank line are not transactions.

Dates without a year were assigned **2026**, consistent with the explicitly dated entries. Transactions were grouped by their parsed dates, regardless of position in the log. The reporting period is **June–August**, rather than a calendar quarter.

These entries remain uncategorized because their purpose is unknown:

| Source line | Date | Description | Amount | What it represents |
|---|---|---|---:|---|
| 47 | June 20 | Zelle Payment | $102.66 | Transfer; recipient/purpose unspecified |
| 51 | June 21 | ATM Cash Withdrawal | $100.00 | Cash withdrawn; subsequent use unknown |
| 60 | June 25 | Venmo - Sam | $68.54 | Payment involving Sam; purpose unspecified |
| 91 | July 9 | Venmo - Sam | $75.00 | Payment involving Sam; purpose unspecified |
| 117 | July 29 | ATM Cash Withdrawal | $30.79 | Cash withdrawn; subsequent use unknown |
| 125 | August 2 | Zelle Payment | $120.00 | Transfer; recipient/purpose unspecified |
| 141 | August 7 | PayPal Transfer | $69.90 | Transfer; recipient/purpose unspecified |
| 161 | August 13 | ATM Cash Withdrawal | $79.84 | Cash withdrawn; subsequent use unknown |

These amounts are included in the logged totals, but are **not confirmed consumption spending**. They could include transfers between accounts or cash subsequently recorded as purchases.

- **Likely duplicate excluded:** lines 111–112 both say `Trader Joe's (Jul. 22) - $54.12`. I counted it once. This assumes a repeated entry rather than two identical purchases.
- **Possible duplicate retained and flagged:** lines 167–168 record Delta Air Lines on August 14 for **$412.60** and **$450.60**. Different amounts prevent confident deduplication; both remain in Travel pending confirmation.
- **Refund subtracted:** line 108, `Return processed - REI (7/18/26) - -$68.00`, reduces July Shopping by **$68.00**.
- **Merchant-based assumptions:** Costco is Groceries; Target and other general retailers are Shopping; Walgreens/CVS are Health / pharmacy. Receipts could change those classifications. Brewery purchases count as Eating out / coffee. Amazon Prime and Planet Fitness App count as Subscriptions; Spotify Concert counts as Entertainment. Airport Parking counts as Travel, while other parking and rideshares count as Local transport / auto.

**Code**

The Python below shows the parsing, category assignments, duplicate rule, signed arithmetic, and calculations. It uses `Decimal` for money. I also independently extracted and summed the raw signed amounts to verify the cleaned total.

<details>
<summary>Show reproducible Python</summary>

```python
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Transaction:
    line: int
    day: date
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
    "Local transport / auto": "Lyft|Uber|City Parking Authority|Jiffy Lube",
    "Subscriptions": ("iCloud+ 200GB|Amazon Prime|Netflix|Planet Fitness App|Spotify Premium"),
    "Internet / phone": "Xfinity Internet|Verizon Wireless",
    "Fitness": "Planet Fitness",
    "Entertainment": ("Steam|Spotify Concert|AMC Theatres|Bowl-O-Rama|Ticketmaster"),
    "Health / pharmacy": ("Riverside Physical Therapy|Walgreens|CVS Pharmacy|Dr. Hensley Dental Copay"),
    "Travel": "Delta Air Lines|Airport Parking|Marriott|Hertz Rental Car",
    "Uncategorized": ("Zelle Payment|ATM Cash Withdrawal|Venmo - Sam|PayPal Transfer"),
}
categories: dict[str, str] = {merchant: category for category, merchants in groups.items() for merchant in merchants.split("|")}
date_pattern: str = (
    r"\b(?:2026-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/26)?|"
    r"0[678]-\d{2}|"
    r"(?:June|Jun\.?|July|Jul\.?|August|Aug\.?)\s+\d{1,2})\b"
)
amount_pattern: str = r"(?<![\d.])-?\$?\d+\.\d{2}(?!\d)"
month_numbers: dict[str, int] = {"jun": 6, "jul": 7, "aug": 8}


def parse_day(raw: str) -> date:
    if raw.startswith("2026-"):
        return date.fromisoformat(raw)
    if raw[0].isalpha():
        month_text, day_text = raw.split()
        return date(2026, month_numbers[month_text[:3].lower()], int(day_text))
    parts: list[str] = re.split(r"[/\-]", raw)
    return date(2026, int(parts[0]), int(parts[1]))


source: str = Path("personal_expenses.txt").read_text()
parsed: list[Transaction] = []
failures: list[tuple[int, str]] = []
metadata: list[tuple[int, str]] = []

for line_number, raw in enumerate(source.splitlines(), 1):
    if not raw.strip():
        continue
    if raw.startswith(("misc expenses", "(started keeping")):
        metadata.append((line_number, raw))
        continue

    dates: list[re.Match[str]] = list(re.finditer(date_pattern, raw))
    amounts: list[re.Match[str]] = list(re.finditer(amount_pattern, raw))
    if len(dates) != 1 or len(amounts) != 1:
        failures.append((line_number, raw))
        continue

    day_match, amount_match = dates[0], amounts[0]
    remainder: str = raw
    for match in sorted(
        [day_match, amount_match],
        key=lambda item: item.start(),
        reverse=True,
    ):
        remainder = remainder[: match.start()] + remainder[match.end() :]

    merchant: str = remainder.strip(" -:|,()")
    merchant = re.sub(r"^Return processed\s*-\s*", "", merchant).strip(" -:|,()")

    if merchant not in categories:
        failures.append((line_number, raw))
        continue

    parsed.append(
        Transaction(
            line_number,
            parse_day(day_match.group()),
            merchant,
            Decimal(amount_match.group().replace("$", "")),
            categories[merchant],
        )
    )

# Count exact date/merchant/signed-amount repeats once.
clean: list[Transaction] = []
seen: dict[tuple[date, str, Decimal], int] = {}
duplicates: list[tuple[int, int]] = []

for transaction in parsed:
    key: tuple[date, str, Decimal] = (transaction.day, transaction.merchant, transaction.amount)
    if key in seen:
        duplicates.append((transaction.line, seen[key]))
    else:
        seen[key] = transaction.line
        clean.append(transaction)

# Flag same-day merchant repeats with different amounts; retain them.
same_day: dict[tuple[date, str], list[Transaction]] = defaultdict(list)
for transaction in clean:
    same_day[transaction.day, transaction.merchant].append(transaction)
print("Review repeated merchant/date:", [items for items in same_day.values() if len(items) > 1])

totals: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
for transaction in clean:
    totals[transaction.category, transaction.day.strftime("%Y-%m")] += transaction.amount

months: list[str] = ["2026-06", "2026-07", "2026-08"]
print("CATEGORY | JUNE | JULY | AUGUST | PERIOD")
for category in groups:
    values: list[Decimal] = [totals[category, month] for month in months]
    print(category, *values, sum(values), sep=" | ")

monthly: list[Decimal] = [sum(totals[category, month] for category in groups) for month in months]
print("TOTAL", *monthly, sum(monthly), sep=" | ")

# Transcribed from budget_notes.txt; no targets for other categories.
targets: dict[str, Decimal] = {
    "Eating out / coffee": Decimal("260"),
    "Shopping": Decimal("1200"),
}
print("CATEGORY | MONTH | NET | TARGET | NET MINUS TARGET")
for category, target in targets.items():
    for month in months:
        print(category, month, totals[category, month], target, totals[category, month] - target, sep=" | ")

changes: list[tuple[Decimal, str, str]] = []
for category in groups:
    for index in (1, 2):
        delta: Decimal = totals[category, months[index]] - totals[category, months[index - 1]]
        changes.append((delta, category, months[index]))

print("Largest absolute category changes:", sorted(changes, key=lambda item: abs(item[0]), reverse=True)[:5])
print("Total monthly changes:", monthly[1] - monthly[0], monthly[2] - monthly[1])
print("Parse failures:", failures)
print("Non-transaction metadata:", metadata)
print("Duplicate lines (excluded, retained):", duplicates)

# Print every parsed transaction, including the flagged duplicate.
print("LINE | DATE | MERCHANT | SIGNED AMOUNT | CATEGORY")
for transaction in sorted(parsed, key=lambda item: (item.day, item.line)):
    print(transaction.line, transaction.day, transaction.merchant, transaction.amount, transaction.category, sep=" | ")

# Independent extraction verifies no signed amounts were lost.
raw_amounts: list[Decimal] = [Decimal(match.group().replace("$", "")) for match in re.finditer(amount_pattern, source)]
assert not failures
assert len(raw_amounts) == len(parsed) == 198
assert len(clean) == 197
assert sum(raw_amounts) - Decimal("54.12") == sum(totals.values()) == Decimal("11758.68")
```

</details>

**The three things I’d most want you to know**

1. **Eating out / coffee is the clearest budget issue.** August’s **$398.69** exceeded your **$260** threshold by **$138.69**, after June and July stayed below it. The July-to-August increase was **$233.55**.

2. **Shopping is your largest category across this period, but August was only slightly above your stated comfort level.** Its period total was **$2,995.80**. August reached **$1,218.31**, or **$18.31** above your approximate **$1,200** monthly target; June and July were below it.

3. **Travel accounts for the largest monthly category change.** It rose from **$0.00** in July to **$1,631.82** in August. That interpretation remains provisional because both flagged Delta entries are included. Confirming those entries will make the August picture more reliable.