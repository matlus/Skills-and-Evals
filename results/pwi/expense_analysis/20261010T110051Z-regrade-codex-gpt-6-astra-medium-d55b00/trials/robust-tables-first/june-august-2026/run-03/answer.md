| Category (USD, net of refunds) | June 2026 | July 2026 | August 2026 | July − June | August − July |
|---|---:|---:|---:|---:|---:|
| Eating out / coffee | $212.74 | $165.14 | $398.69 | −$47.60 | +$233.55 |
| Shopping | $1,020.77 | $756.72 | $1,218.31 | −$264.05 | +$461.59 |
| Groceries | $624.34 | $829.20 | $982.79 | +$204.86 | +$153.59 |
| Gas | $133.63 | $236.22 | $426.99 | +$102.59 | +$190.77 |
| Subscriptions | $55.45 | $55.45 | $55.45 | $0.00 | $0.00 |
| Internet / phone | $143.13 | $143.13 | $143.13 | $0.00 | $0.00 |
| Fitness | $67.82 | $132.81 | $54.19 | +$64.99 | −$78.62 |
| Entertainment | $143.42 | $135.51 | $160.88 | −$7.91 | +$25.37 |
| Healthcare / pharmacy | $276.43 | $138.36 | $168.61 | −$138.07 | +$30.25 |
| Local transport / auto | $327.78 | $137.45 | $135.59 | −$190.33 | −$1.86 |
| Travel | $0.00 | $0.00 | $1,631.82 | $0.00 | +$1,631.82 |
| **Categorized subtotal** | **$3,005.51** | **$2,729.99** | **$5,376.45** | | |
| Uncategorized transfers / cash* | $271.20 | $105.79 | $269.74 | −$165.41 | +$163.95 |
| **Total recorded net outflows*** | **$3,276.71** | **$2,835.78** | **$5,646.19** | | |

| Budget target | June | July | August |
|---|---:|---:|---:|
| Eating out / coffee: under $260/month | $47.26 below | $94.86 below | **$138.69 over** |
| Shopping: roughly $1,200/month | $179.23 below | $443.28 below | **$18.31 above** |

*Transfers and cash withdrawals are recorded outflows, but their ultimate spending purpose is unknown. They are excluded from the categorized subtotal and budget comparisons.*

**Data-cleaning notes**

- **Parsing:** All 198 transaction lines parsed successfully; no transaction lines were unreadable. The title, explanatory note, and blank lines are metadata. Dates without a year were assigned **2026**, consistent with the explicit dates. Transactions were grouped by parsed date, regardless of their position in the file.
- **Exact likely duplicate:** Lines **111–112** both record Trader Joe’s, **July 22, $54.12**. I retained one and excluded the second, leaving **197 records**. This is a provisional duplicate decision; two separate identical purchases remain possible.
- **Possible duplicate requiring confirmation:** Lines **167–168** record Delta Air Lines on **August 14**, for **$412.60** and **$450.60**. I retained both because the amounts differ and the descriptions do not establish whether these are separate tickets or a corrected entry.
- **Refund:** Line **108**, REI on **July 18, −$68.00**, reduces July shopping. It is not treated as a purchase or removed as a duplicate.
- **Merchant-based assumptions:** Costco is groceries; Target, Amazon purchases, Home Depot, and IKEA are shopping. Amazon Prime and Planet Fitness App are subscriptions; Planet Fitness is fitness. Breweries are eating out; Spotify Concert is entertainment. Pharmacy merchants are healthcare / pharmacy. Receipts could change these assignments.

These entries remain **uncategorized**:

| Source line | Date | Description | Amount | What is unknown |
|---|---|---|---:|---|
| 47 | 2026-06-20 | Zelle Payment | $102.66 | Recipient and purpose |
| 51 | 2026-06-21 | ATM Cash Withdrawal | $100.00 | How the cash was spent |
| 60 | 2026-06-25 | Venmo - Sam | $68.54 | Payment purpose |
| 91 | 2026-07-09 | Venmo - Sam | $75.00 | Payment purpose |
| 117 | 2026-07-29 | ATM Cash Withdrawal | $30.79 | How the cash was spent |
| 125 | 2026-08-02 | Zelle Payment | $120.00 | Recipient and purpose |
| 141 | 2026-08-07 | PayPal Transfer | $69.90 | Destination and purpose |
| 161 | 2026-08-13 | ATM Cash Withdrawal | $79.84 | How the cash was spent |

The calculations used Python `Decimal` arithmetic. This reproduces the parsing, duplicate handling, category totals, target differences, and ranking of monthly changes; it also prints every retained transaction for inspection.

```python
import calendar
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Transaction:
    line: int
    date: date
    merchant: str
    amount: Decimal
    category: str


groups: dict[str, str] = {
    "Eating out / coffee": "Local Coffee Co|Chipotle|McDonald's|Rustic Tap Brewery|Panera Bread|"
    "Starbucks|Sushi Kame|Thai Orchid|Bagel Corner|Luigi's Pizza",
    "Shopping": "Amazon|Best Buy|Home Depot|Target|REI|Barnes & Noble|Old Navy|IKEA",
    "Groceries": "Trader Joe's|Aldi|Kroger|Costco|Whole Foods",
    "Gas": "Shell|Chevron|BP Gas",
    "Subscriptions": "iCloud+ 200GB|Amazon Prime|Netflix|Planet Fitness App|Spotify Premium",
    "Internet / phone": "Xfinity Internet|Verizon Wireless",
    "Fitness": "Planet Fitness",
    "Entertainment": "Steam|Spotify Concert|AMC Theatres|Bowl-O-Rama|Ticketmaster",
    "Healthcare / pharmacy": "Riverside Physical Therapy|Walgreens|CVS Pharmacy|Dr. Hensley Dental Copay",
    "Local transport / auto": "Lyft|Uber|City Parking Authority|Jiffy Lube",
    "Travel": "Delta Air Lines|Airport Parking|Marriott|Hertz Rental Car",
    "Uncategorized": "Zelle Payment|ATM Cash Withdrawal|Venmo - Sam|PayPal Transfer",
}
lookup: dict[str, str] = {merchant: category for category, merchants in groups.items() for merchant in merchants.split("|")}
date_pattern: re.Pattern[str] = re.compile(
    r"2026-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/26)?|\d{2}-\d{2}|"
    r"(?:June|Jun\.?|July|Jul\.?|August|Aug\.?) \d{1,2}"
)


def parse_date(token: str) -> date:
    if token.startswith("2026-"):
        return date.fromisoformat(token)
    if token[0].isdigit():
        parts: list[str] = re.split(r"[-/]", token)
        return date(2026, int(parts[0]), int(parts[1]))
    month, day = token.split()
    return date(2026, list(calendar.month_abbr).index(month[:3]), int(day))


def parse_line(line_number: int, raw: str) -> Transaction:
    dates: list[re.Match[str]] = list(date_pattern.finditer(raw))
    if len(dates) != 1:
        raise ValueError("Missing or multiple dates")
    match: re.Match[str] = dates[0]
    rest: str = raw[: match.start()] + raw[match.end() :]
    amounts: list[re.Match[str]] = list(re.finditer(r"-?\$?\d+\.\d{2}", rest))
    if len(amounts) != 1:
        raise ValueError("Missing or multiple amounts")
    amount_match: re.Match[str] = amounts[0]
    amount: Decimal = Decimal(amount_match.group().replace("$", ""))
    merchant: str = (rest[: amount_match.start()] + rest[amount_match.end() :]).strip(" -|:,()")
    merchant = merchant.removeprefix("Return processed - ").strip(" -|:,()")
    return Transaction(line_number, parse_date(match.group()), merchant, amount, lookup.get(merchant, "Uncategorized"))


rows: list[Transaction] = []
seen: dict[tuple[date, str, Decimal], Transaction] = {}
failures: list[tuple[int, str, str]] = []
duplicates: list[tuple[int, int]] = []
lines: list[str] = Path("personal_expenses.txt").read_text().splitlines()

for line_number, raw in enumerate(lines, 1):
    if not raw.strip() or raw.startswith(("misc expenses", "(started keeping")):
        continue
    try:
        transaction: Transaction = parse_line(line_number, raw)
    except ValueError as error:
        failures.append((line_number, raw, str(error)))
        continue
    key: tuple[date, str, Decimal] = (transaction.date, transaction.merchant, transaction.amount)
    if key in seen:
        duplicates.append((seen[key].line, line_number))
        continue
    seen[key] = transaction
    rows.append(transaction)

totals: defaultdict[tuple[str, int], Decimal] = defaultdict(Decimal)
for transaction in rows:
    totals[transaction.category, transaction.date.month] += transaction.amount

print("Parse failures:", failures)
print("Excluded duplicate line pairs:", duplicates)
for transaction in sorted(rows, key=lambda item: (item.date, item.line)):
    print(transaction)

print("Category, June, July, August, July-June, August-July")
for category in groups:
    values: list[Decimal] = [totals[category, month] for month in (6, 7, 8)]
    print(category, *values, values[1] - values[0], values[2] - values[1])

for month in (6, 7, 8):
    categorized: Decimal = sum((totals[category, month] for category in groups if category != "Uncategorized"), Decimal("0"))
    print(month, "categorized:", categorized, "all outflows:", categorized + totals["Uncategorized", month])

targets: dict[str, Decimal] = {
    "Eating out / coffee": Decimal("260"),
    "Shopping": Decimal("1200"),
}
for category, target in targets.items():
    for month in (6, 7, 8):
        print(category, month, "actual:", totals[category, month], "actual minus target:", totals[category, month] - target)

changes: list[tuple[Decimal, str, int]] = [
    (totals[category, month] - totals[category, month - 1], category, month) for category in groups for month in (7, 8)
]
print("Changes ranked by absolute size:")
for change in sorted(changes, key=lambda item: abs(item[0]), reverse=True):
    print(change)
```

**The three things I’d most want you to know**

1. **Eating out / coffee is the clearest departure from your stated goal.** August reached **$398.69**, **$138.69 over** your $260 limit, after June and July stayed below it. The July-to-August increase was **$233.55**.
2. **Shopping rose sharply in August, but remained close to your flexible target.** It reached **$1,218.31**, just **$18.31 above** your roughly $1,200 allowance. Its **$461.59** increase was the second-largest category change; July’s **$264.05 decline** was the third-largest change by absolute amount.
3. **Travel explains the largest monthly category change.** It went from **$0.00 in July to $1,631.82 in August**. That total includes both flagged Delta entries, so confirming them matters before treating the travel total as settled. You have no stated travel budget, so this is an explanation of the change, not a budget judgment.