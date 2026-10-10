| Month | Eating out / coffee | Shopping | Groceries | Gas/auto | Subscriptions | Utilities | Fitness | Health | Transport | Entertainment | Travel | Uncategorized |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jun 2026 | $212.74 | $1,113.31 | $624.34 | $133.63 | $45.46 | $143.13 | $77.81 | $183.89 | $327.78 | $143.42 | $0.00 | $271.20 |
| Jul 2026 | $165.14 | $828.82 | $829.20 | $274.59 | $45.46 | $143.13 | $142.80 | $66.26 | $99.08 | $135.51 | $0.00 | $105.79 |
| Aug 2026 | $398.69 | $1,232.08 | $982.79 | $426.99 | $45.46 | $143.13 | $64.18 | $154.84 | $417.94 | $160.88 | $1,349.47 | $269.74 |

| Budget target | Jun 2026 | Jul 2026 | Aug 2026 |
|---|---:|---:|---:|
| Eating out / coffee — under $260/month | $212.74 — under by $47.26 | $165.14 — under by $94.86 | $398.69 — over by $138.69 |
| Amazon/shopping — roughly $1,200/month is fine | $1,113.31 — $86.69 below | $828.82 — $371.18 below | $1,232.08 — $32.08 above |

## Data-cleaning notes

- Parsed all 198 transaction lines into date, merchant/description, and amount. **No transaction lines were unparseable.** Years omitted in dates were read as 2026, consistent with the log’s June–August period.
- Left these eight entries uncategorized because the log doesn’t say what they paid for:
  - June 20: Zelle Payment, $102.66
  - June 21: ATM Cash Withdrawal, $100.00
  - June 25: Venmo - Sam, $68.54
  - July 9: Venmo - Sam, $75.00
  - July 29: ATM Cash Withdrawal, $30.79
  - August 2: Zelle Payment, $120.00
  - August 7: PayPal Transfer, $69.90
  - August 13: ATM Cash Withdrawal, $79.84
- Removed one likely duplicate: the second identical Trader Joe’s entry on July 22 ($54.12; line 112).
- Treated the July 18 REI return (−$68.00) as a refund, reducing Shopping by $68.00.

I used Python to extract the transactions, remove the exact duplicate, retain the refund as a negative amount, and sum by month and category. The key calculation was:

```python
from collections import defaultdict

monthly = defaultdict(float)
seen = set()

for date, merchant, amount, category in transactions:
    key = (date, merchant, amount)
    if key in seen:
        continue
    seen.add(key)
    monthly[(date.strftime("%Y-%m"), category)] += amount

for month in sorted({month for month, _ in monthly}):
    for category in categories:
        print(month, category, f"{monthly[(month, category)]:.2f}")
```

## Three things to know this quarter

1. Eating out / coffee was under its $260 target in June and July, then reached $398.69 in August—$138.69 over target. Its largest month-over-month increase was $233.55, from July to August.
2. Shopping was below the roughly $1,200 monthly guide in June and July. August reached $1,232.08, or $32.08 above it; the increase from July was $403.26.
3. Travel rose by $1,349.47 from July to August, the largest month-over-month category increase. August included two Delta Air Lines charges, a Marriott charge, and a Hertz rental car charge.