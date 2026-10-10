| Month (2026) | Eating out / coffee | Entertainment | Groceries | Health | Shopping | Subscriptions / bills | Transport / travel | Uncategorized | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| June | $221.99 | $134.17 | $624.34 | $183.89 | $1,113.31 | $266.40 | $461.41 | $271.20 | $3,276.71 |
| July | $165.14 | $135.51 | $829.20 | $66.26 | $964.82 | $331.39 | $373.67 | $105.79 | $2,971.78 |
| August | $398.69 | $160.88 | $982.79 | $154.84 | $1,232.08 | $252.77 | $2,194.40 | $269.74 | $5,646.19 |

Monthly category amounts are net of the recorded REI refund and the removed duplicate. The code below computes the figures from the log; it treats ordinary hyphens before amounts as formatting, and a `-$` amount as negative.

| Budget target | June | July | August |
|---|---:|---:|---:|
| Eating out / coffee: under $260/month | $221.99 — under by $38.01 | $165.14 — under by $94.86 | $398.69 — over by $138.69 |
| Shopping: roughly $1,200/month | $1,113.31 — under by $86.69 | $964.82 — under by $235.18 | $1,232.08 — over by $32.08 |

```python
from collections import Counter, defaultdict
from pathlib import Path
import re

lines = Path("personal_expenses.txt").read_text().splitlines()
months = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
date_re = re.compile(
    r"(?i)(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|"
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"[a-z.]*\s+\d{1,2}(?:,?\s*20\d{2})?|"
    r"\b\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?)"
)
amount_re = re.compile(
    r"(?<![\w.])(?:-\$\s*\d[\d,]*\.\d{2}|\$\s*\d[\d,]*\.\d{2}|"
    r"\d[\d,]*\.\d{2})"
)


def category(merchant: str) -> str:
    name = merchant.lower()
    if any(x in name for x in ("zelle", "venmo", "paypal transfer", "atm cash")):
        return "Uncategorized"
    if any(
        x in name
        for x in (
            "coffee",
            "chipotle",
            "mcdonald",
            "brewery",
            "panera",
            "sushi",
            "thai orchid",
            "bowl-o-rama",
            "starbucks",
            "bagel corner",
            "luigi's",
        )
    ):
        return "Eating out / coffee"
    if any(x in name for x in ("trader joe", "aldi", "kroger", "whole foods", "costco")):
        return "Groceries"
    if any(
        x in name
        for x in (
            "amazon prime",
            "netflix",
            "icloud",
            "spotify premium",
            "planet fitness",
            "xfinity",
            "verizon",
        )
    ):
        return "Subscriptions / bills"
    if any(
        x in name
        for x in (
            "amazon",
            "best buy",
            "target",
            "rei",
            "old navy",
            "barnes",
            "home depot",
            "ikea",
            "walgreens",
            "cvs",
        )
    ):
        return "Shopping"
    if any(x in name for x in ("spotify concert", "amc", "ticketmaster", "steam")):
        return "Entertainment"
    if any(x in name for x in ("physical therapy", "dental")):
        return "Health"
    if any(
        x in name
        for x in (
            "shell",
            "chevron",
            "bp gas",
            "jiffy lube",
            "lyft",
            "uber",
            "parking",
            "delta air",
            "hertz",
            "marriott",
        )
    ):
        return "Transport / travel"
    return "Other"


rows = []
unparsed = []
for line_number, line in enumerate(lines, start=1):
    date_match = date_re.search(line)
    amount_match = amount_re.search(line)
    if not date_match and not amount_match:
        continue  # Heading or explanatory note, not a transaction.
    if not date_match or not amount_match:
        unparsed.append((line_number, line))
        continue

    date_text = date_match.group()
    if date_text.startswith("20"):
        year, month, day = map(int, re.split(r"[-/]", date_text))
    elif date_text[0].isdigit():
        parts = list(map(int, re.split(r"[-/]", date_text)))
        month, day = parts[:2]
        year = parts[2] if len(parts) == 3 else 2026
        if year < 100:
            year += 2000
    else:
        match = re.match(r"([A-Za-z]+)[.]?\s+(\d{1,2})(?:,?\s*(\d{4}))?", date_text)
        month = months[match.group(1)[:3].lower()]
        day = int(match.group(2))
        year = int(match.group(3) or 2026)

    token = amount_match.group()
    amount = float(token.replace("$", "").replace(",", ""))
    if token.startswith("-$"):
        amount = -amount

    merchant_text = line[: amount_match.start()] + " " + line[amount_match.end() :]
    merchant_text = merchant_text.replace(date_text, " ")
    merchant_text = re.sub(
        r"(?i)\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|"
        r"\b\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?\b|"
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[a-z.]*\s+\d{1,2}(?:,?\s*20\d{2})?\b",
        " ",
        merchant_text,
    )
    merchant = re.sub(r"[()]", "", merchant_text).strip(" -:|,")
    rows.append((year, month, day, merchant, amount, line_number, category(merchant)))

# Remove one repeated same-date, same-merchant, same-amount entry.
seen = set()
clean_rows = []
for row in rows:
    key = (row[0], row[1], row[2], row[3], row[4])
    if key in seen:
        continue
    seen.add(key)
    clean_rows.append(row)

totals = defaultdict(float)
for year, month, day, merchant, amount, line_number, spending_category in clean_rows:
    totals[(month, spending_category)] += amount

categories = sorted({row[6] for row in clean_rows})
for month in (6, 7, 8):
    values = [totals[(month, name)] for name in categories]
    print(month, dict(zip(categories, values)), "total", sum(values))
print("unparsed transaction lines:", unparsed)
print("exact duplicates removed:", Counter((r[0], r[1], r[2], r[3], r[4]) for r in rows))
```

### Data-cleaning notes

- **Unparsed transactions:** None. All 198 transaction lines had a date, merchant/description, and amount. The heading and introductory note were not transaction lines. Dates without a year were treated as 2026, consistent with the log’s June–August period.
- **Uncategorized:** Zelle payments ($102.66 in June; $120.00 in August), Venmo payments to Sam ($68.54 in June; $75.00 in July), ATM withdrawals ($100.00 and $30.79 in June/July; $79.84 in August), and a PayPal transfer ($69.90 in August). The log doesn’t say what these funds were used for, so I left them uncategorized.
- **Duplicate:** The two identical Trader Joe’s entries on July 22 for $54.12 appear to be a duplicate. I counted one and removed one.
- **Refund:** The July 18 REI entry of **-$68.00** is recorded as a refund and reduces July shopping. The two Delta Air Lines entries on August 14 have different amounts ($412.60 and $450.60), so I retained both; the log alone doesn’t establish that either is a duplicate.

### Three things I’d most want you to know this quarter

1. Eating out / coffee stayed under its $260 target in June and July, then reached $398.69 in August—$138.69 over target.
2. Shopping was under its roughly $1,200 target in June and July, then reached $1,232.08 in August—$32.08 over.
3. The largest month-over-month category increase was transport / travel: it rose by $1,820.73 from July’s $373.67 to August’s $2,194.40. Total spending rose by $2,674.41 over the same period; the Delta flights, Marriott, Hertz, and airport parking entries contribute to the August travel total.