| Month (2026) | Amazon/shopping | Eating out / coffee | Entertainment | Groceries | Health / fitness | Subscriptions / utilities | Transport: fuel/auto | Transport: parking/travel | Uncategorized |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| June | $1,232.66 | $221.99 | $134.17 | $427.44 | $354.24 | $173.60 | $133.63 | $327.78 | $271.20 |
| July | $996.34 | $165.14 | $135.51 | $604.57 | $281.16 | $173.60 | $274.59 | $99.08 | $105.79 |
| August | $1,638.99 | $398.69 | $160.88 | $577.10 | $232.79 | $173.60 | $426.99 | $1767.41 | $269.74 |

| Month (2026) | Eating out / coffee | Target | Difference | Amazon/shopping | Target | Difference |
|---|---:|---:|---:|---:|---:|---:|
| June | $221.99 | $260.00 | −$38.01 | $1,232.66 | $1,200.00 | +$32.66 |
| July | $165.14 | $260.00 | −$94.86 | $996.34 | $1,200.00 | −$203.66 |
| August | $398.69 | $260.00 | +$138.69 | $1,638.99 | $1,200.00 | +$438.99 |

### Data-cleaning notes

- **Unparsed transaction lines:** None. I treated dates without a year as 2026, based on the log’s June–August 2026 entries.
- **Uncategorized:** I left transfers and cash withdrawals uncategorized because the log doesn’t say what they paid for: Zelle, June 20 $102.66 and August 2 $120.00; Venmo to Sam, June 25 $68.54 and July 9 $75.00; ATM withdrawals, June 21 $100.00, July 29 $30.79, and August 13 $79.84; PayPal transfer, August 7 $69.90.
- **Duplicate:** The two Trader Joe’s entries on July 22 for $54.12 appear identical. I counted one and dropped the other.
- **Refund:** I treated the July 18 REI return of −$68.00 as a credit against Amazon/shopping, not as a purchase.
- **Categories:** Barnes & Noble is counted as shopping; AMC, Steam, Spotify Concert, and Ticketmaster are entertainment. Travel includes airfare, lodging, rental cars, rides, and parking.

### Three things I’d most want you to know this quarter

1. Eating out / coffee stayed under its $260 target in June and July, then exceeded it by $138.69 in August.
2. Amazon/shopping was above its $1,200 target in June and August; August was $438.99 over.
3. The largest month-over-month increase was transport: parking/travel, which rose by $1,668.33 from July to August. This category has no stated budget target.

**Calculation code:** The parser below reads each transaction’s date, recognized merchant, and final amount; flags rows it can’t parse; drops repeated date/merchant/amount entries; and totals amounts in cents so refunds reduce their category.

```python
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

# merchant_names contains the merchant names listed in the cleaning notes
merchant_names = sorted(MERCHANT_NAMES, key=len, reverse=True)
date_patterns = [
    r"20\d{2}-\d{2}-\d{2}",
    r"\d{1,2}[/-]\d{1,2}(?:/\d{2,4})?",
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2}(?:,?\s*20\d{2})?",
]

rows, unparsed = [], []
for line_no, line in enumerate(Path("personal_expenses.txt").read_text().splitlines(), 1):
    text = line.strip()
    if not text or text.lower().startswith("misc expenses") or text.startswith("("):
        continue

    merchants = [m for m in merchant_names if re.search(re.escape(m), text, re.I)]
    amounts = re.findall(r"-?\$?\d[\d,]*\.\d{2}", text)
    dates = [m for pattern in date_patterns for m in re.finditer(pattern, text, re.I)]
    if not merchants or not amounts or not dates:
        unparsed.append((line_no, text))
        continue

    # Normalize the matched date; dates lacking a year use 2026.
    transaction_date = parse_date(dates[0].group(), default_year=2026)
    amount_cents = round(float(amounts[-1].replace("$", "").replace(",", "")) * 100)
    rows.append((line_no, transaction_date, merchants[0], amount_cents))

# Remove repeated transactions with the same date, merchant, and amount.
seen, clean = set(), []
for row in rows:
    key = row[1:4]
    if key in seen:
        continue
    seen.add(key)
    clean.append(row)

totals = defaultdict(lambda: defaultdict(int))
for _, transaction_date, merchant, cents in clean:
    category = categorize(merchant)  # Uses the category assignments described above.
    totals[(transaction_date.year, transaction_date.month)][category] += cents

for month in sorted(totals):
    print(month, {category: cents / 100 for category, cents in totals[month].items()})
```

`MERCHANT_NAMES`, `parse_date`, and `categorize` stand for the explicit merchant list, date normalization, and category mappings applied to the log.