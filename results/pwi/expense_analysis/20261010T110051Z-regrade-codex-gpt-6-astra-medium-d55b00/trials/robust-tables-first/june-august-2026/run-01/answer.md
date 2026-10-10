| Category | June 2026 | July 2026 | August 2026 | Quarter |
|---|---:|---:|---:|---:|
| Eating out / coffee | $212.74 | $165.14 | $398.69 | $776.57 |
| Shopping | $1,068.35 | $756.72 | $1,218.31 | $3,043.38 |
| Groceries | $624.34 | $829.20 | $982.79 | $2,436.33 |
| Gas | $133.63 | $236.22 | $426.99 | $796.84 |
| Transport / vehicle | $327.78 | $137.45 | $135.59 | $600.82 |
| Travel | $0.00 | $0.00 | $1,631.82 | $1,631.82 |
| Health / pharmacy | $276.43 | $138.36 | $168.61 | $583.40 |
| Fitness | $67.82 | $132.81 | $54.19 | $254.82 |
| Subscriptions | $55.45 | $55.45 | $55.45 | $166.35 |
| Internet / phone | $143.13 | $143.13 | $143.13 | $429.39 |
| Entertainment | $95.84 | $135.51 | $160.88 | $392.23 |
| Uncategorized | $271.20 | $105.79 | $269.74 | $646.73 |
| **Net logged outflow** | **$3,276.71** | **$2,835.78** | **$5,646.19** | **$11,758.68** |

| Budget target | Month | Net spending | Monthly target | Actual − target |
|---|---|---:|---:|---:|
| Eating out / coffee | June | $212.74 | $260.00 | −$47.26 |
| Eating out / coffee | July | $165.14 | $260.00 | −$94.86 |
| Eating out / coffee | August | $398.69 | $260.00 | +$138.69 |
| Shopping | June | $1,068.35 | ~$1,200.00 | −$131.65 |
| Shopping | July | $756.72 | ~$1,200.00 | −$443.28 |
| Shopping | August | $1,218.31 | ~$1,200.00 | +$18.31 |

The largest category changes, ranked by absolute month-over-month difference:

| Category | Transition | Change |
|---|---|---:|
| Travel | July → August | +$1,631.82 |
| Shopping | July → August | +$461.59 |
| Shopping | June → July | −$311.63 |
| Eating out / coffee | July → August | +$233.55 |

**Data-cleaning notes**

All **198 transaction lines** parsed successfully into date, description, and signed amount. There were **no unparseable transaction lines**. Lines 1–2 are a heading and introductory note; blank lines were ignored. Dates without a year were assigned **2026**, consistent with the explicitly dated entries. Aggregation used transaction dates, regardless of line order.

These entries remain uncategorized because their purpose is unknown:

| File line | Date | Description | Amount | What it represents |
|---|---|---|---:|---|
| 47 | June 20 | Zelle Payment | $102.66 | Transfer; purpose unspecified |
| 51 | June 21 | ATM Cash Withdrawal | $100.00 | Cash withdrawn; subsequent use unknown |
| 60 | June 25 | Venmo - Sam | $68.54 | Payment to Sam; purpose unspecified |
| 91 | July 9 | Venmo - Sam | $75.00 | Payment to Sam; purpose unspecified |
| 117 | July 29 | ATM Cash Withdrawal | $30.79 | Cash withdrawn; subsequent use unknown |
| 125 | August 2 | Zelle Payment | $120.00 | Transfer; purpose unspecified |
| 141 | August 7 | PayPal Transfer | $69.90 | Transfer; purpose unspecified |
| 161 | August 13 | ATM Cash Withdrawal | $79.84 | Cash withdrawn; subsequent use unknown |

These remain in the totals as logged outflows. They are not necessarily purchases and could overlap with spending recorded elsewhere.

- **Likely duplicate removed:** lines 111–112 both say `Trader Joe's (Jul. 22) - $54.12`. I retained one, leaving **197 entries**. If these were separate purchases, July groceries and the overall total would each need another $54.12.
- **Possible duplicate retained:** Delta Air Lines appears twice on August 14, for **$412.60** and **$450.60**. Different amounts prevent confident deduplication; both remain in Travel pending clarification.
- **Refund handled:** line 108, `Return processed - REI (7/18/26) - -$68.00`, reduces July Shopping by **$68.00**.
- **Merchant assumptions:** Costco is Groceries; Target, Home Depot, IKEA, and Steam are Shopping. Pharmacy merchants are Health / pharmacy. These are merchant-based classifications, not receipt-level determinations. Amazon Prime and Planet Fitness App are Subscriptions; Spotify Concert is Entertainment. Airport Parking is Travel; ordinary parking, rideshares, and Jiffy Lube are Transport / vehicle.

The following is the calculation code used after parsing. `seen` contains retained `(date, merchant, signed_integer_cents)` keys; `lookup` maps each merchant to its category. Deduplication used that full key, and negative cents remained negative.

```python
from collections import defaultdict

monthly = defaultdict(lambda: defaultdict(int))

# Aggregate the parsed, deduplicated entries.
for when, merchant, cents in seen:
    monthly[when.strftime("%Y-%m")][lookup[merchant]] += cents

months = sorted(monthly)

# Monthly category totals and quarter totals.
for category in groups:
    values = [monthly[month][category] for month in months]
    print(category, values, sum(values))

# Overall monthly and quarter totals.
totals = [sum(monthly[month].values()) for month in months]
print("Net logged outflow", totals, sum(totals))

# Only the two targets in budget_notes.txt.
for month in months:
    for category, target in [
        ("Eating out / coffee", 26000),
        ("Shopping", 120000),
    ]:
        actual = monthly[month][category]
        print(month, category, actual, target, actual - target)

# Rank category changes by absolute size.
changes = [(monthly[b][category] - monthly[a][category], category, a, b) for a, b in zip(months, months[1:]) for category in groups]
for change in sorted(changes, key=lambda row: abs(row[0]), reverse=True):
    print(change)

print("Total monthly changes", [sum(monthly[b].values()) - sum(monthly[a].values()) for a, b in zip(months, months[1:])])
# All arithmetic above is in integer cents; divide by 100 for display.
```

**The three things I’d most want you to know**

1. **Eating out / coffee is the clearest budget concern.** August reached **$398.69**, exceeding your **$260** target by **$138.69**, after both June and July stayed under it. The July-to-August increase was **$233.55**.
2. **Shopping is your largest categorized quarterly expense, but its budget picture is different.** It totaled **$3,043.38** for the quarter. June and July were below your approximate monthly allowance; August’s **$1,218.31** was only **$18.31 above** it, despite a **$461.59** increase from July.
3. **Travel is the largest contributor to August’s jump.** Net logged outflow rose from **$2,835.78** in July to **$5,646.19** in August, with Travel contributing **$1,631.82** of the increase. That travel figure includes both Delta entries awaiting clarification; your notes set no travel budget against which to judge it.