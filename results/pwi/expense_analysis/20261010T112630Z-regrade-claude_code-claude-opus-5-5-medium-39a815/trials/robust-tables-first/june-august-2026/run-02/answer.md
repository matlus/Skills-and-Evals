Totals were computed by a parsing script (`scratchpad/analyze.py`, plus `extra.py` for the supporting figures). Dates without a year are treated as 2026.

### Monthly totals by category

| Category | Jun | Jul | Aug | Q total |
|---|---:|---:|---:|---:|
| Shopping | $1,020.77 | $756.72 | $1,218.31 | $2,995.80 |
| Groceries | $624.34 | $829.20 | $982.79 | $2,436.33 |
| Travel | $0.00 | $0.00 | $1,631.82 | $1,631.82 |
| Health & fitness | $344.25 | $271.17 | $222.80 | $838.22 |
| Gas | $133.63 | $236.22 | $426.99 | $796.84 |
| Dining & coffee | $212.74 | $165.14 | $398.69 | $776.57 |
| Transport & parking | $327.78 | $137.45 | $135.59 | $600.82 |
| Entertainment | $143.42 | $135.51 | $160.88 | $439.81 |
| Phone & internet | $143.13 | $143.13 | $143.13 | $429.39 |
| Subscriptions | $55.45 | $55.45 | $55.45 | $166.35 |
| *Uncategorized (transfers/cash)* | $271.20 | $105.79 | $269.74 | $646.73 |
| **All spending** | **$3,276.71** | **$2,835.78** | **$5,646.19** | **$11,758.68** |
| All spending except travel | $3,276.71 | $2,835.78 | $4,014.37 | |

### Budget comparison

| Budget | Month | Spent | Target | Over / (under) | % of target |
|---|---|---:|---:|---:|---:|
| Eating out / coffee | Jun | $212.74 | $260 | ($47.26) | 82% |
| Eating out / coffee | Jul | $165.14 | $260 | ($94.86) | 64% |
| Eating out / coffee | **Aug** | **$398.69** | $260 | **+$138.69** | **153%** |
| Shopping | Jun | $1,020.77 | $1,200 | ($179.23) | 85% |
| Shopping | Jul | $756.72 | $1,200 | ($443.28) | 63% |
| Shopping | **Aug** | **$1,218.31** | $1,200 | **+$18.31** | **102%** |

### Largest month-over-month changes

| Category | Period | From | To | Change |
|---|---|---:|---:|---:|
| Travel | Jul→Aug | $0.00 | $1,631.82 | +$1,631.82 |
| Shopping | Jul→Aug | $756.72 | $1,218.31 | +$461.59 (+61%) |
| Shopping | Jun→Jul | $1,020.77 | $756.72 | −$264.05 (−26%) |
| Dining & coffee | Jul→Aug | $165.14 | $398.69 | +$233.55 (+141%) |
| Groceries | Jun→Jul | $624.34 | $829.20 | +$204.86 (+33%) |
| Gas | Jul→Aug | $236.22 | $426.99 | +$190.77 (+81%) |
| Transport & parking | Jun→Jul | $327.78 | $137.45 | −$190.33 (−58%) |

---

## Data-cleaning notes

**Lines I couldn't parse:** None of the transactions. All 198 transaction lines produced a date, merchant and amount. Only the two header lines (1–2) were skipped. The script rejects any line with zero or more than one amount, so nothing was guessed. Two parsing rules to know about:
- Dates like `06-01` are read as month-day.
- Lines are sorted by the date written on them, not by where they sit in the file. For example, line 59 (Sushi Kame, Jun 28) sits among Jun 25 entries.

**Uncategorized (8 entries, $646.73).** I didn't force these into a category:

| Line | Date | Entry | Amount | What it is |
|---|---|---|---:|---|
| 47 | Jun 20 | Zelle Payment | $102.66 | Transfer to a person, no payee or purpose |
| 51 | Jun 21 | ATM Cash Withdrawal | $100.00 | Cash, use unknown |
| 60 | Jun 25 | Venmo – Sam | $68.54 | Payment to Sam, purpose unknown (could be splitting a meal, rent, etc.) |
| 91 | Jul 9 | Venmo – Sam | $75.00 | Same as above |
| 117 | Jul 29 | ATM Cash Withdrawal | $30.79 | Cash. The odd amount suggests a fee or a cash-back purchase |
| 125 | Aug 2 | Zelle Payment | $120.00 | Transfer, no payee |
| 141 | Aug 7 | PayPal Transfer | $69.90 | Could be a purchase or a person-to-person payment |
| 161 | Aug 13 | ATM Cash Withdrawal | $79.84 | Cash, odd amount |

If any of the Venmo or Zelle payments were you covering shared meals, your dining numbers are understated.

**Duplicates:**
- **Removed:** line 112, Trader Joe's, Jul 22, $54.12. It's identical to line 111, which sits right above it.
- **Kept but flagged:** Delta Air Lines on Aug 14, $412.60 (line 167) and $450.60 (line 168). These could be two tickets, or a rebooking where the first fare should have been refunded. If it was a rebooking, Travel and August are both overstated by $412.60.
- **Kept but flagged:** Kroger Jun 6 $114.37 (line 22) and Jun 8 $112.18 (line 23). The amounts are close and two days apart, and your note says some entries were logged late from memory. If it's the same trip, June groceries drop by about $112.
- The script found other same-merchant charges within two days, such as Panera, IKEA and parking. Their amounts are clearly different, so I treated them as real.

**Refunds:** Line 108, an REI return of **−$68.00** on Jul 18, is subtracted from July Shopping rather than treated as a purchase. No other negative amounts appear in the log.

**Category calls you may want to change:**
- **Costco:** counted as Groceries.
- **Target:** counted as Shopping.
- **Amazon Prime:** counted as a subscription, not shopping.
- **Steam and "Spotify Concert":** counted as Entertainment. The concert charges vary in amount, so they look like ticket purchases, not a subscription.
- **Airport Parking:** counted as Travel.

---

## Three things you should know

1. **August's jump is about half the trip and half not.** August spending was $5,646.19, roughly twice July's $2,835.78.
   - The Aug 14–15 trip (Delta ×2, Marriott, Hertz, airport parking) accounts for $1,631.82.
   - Even without the trip, August was **$4,014.37**, still well above June ($3,276.71) and July ($2,835.78).
   - The rest of the jump came from dining, shopping, groceries and gas all rising together.

2. **Eating out went over budget because you went out more often.** You were comfortably under $260 in June and July, then hit **$398.69 (153%)** in August.
   - The number of dining and coffee charges doubled, from 9 in July to 18 in August.
   - The average charge only rose from $18.35 to $22.15.
   - Only $8.05 of it happened during the trip.
   - This matches the worry in your note: lots of small charges adding up without you noticing.

3. **Shopping just crossed $1,200, and gas is growing fastest.**
   - **Shopping:** August reached $1,218.31, just over budget. Best Buy alone was $535.80 across July and August ($340.20 of it in August, in two purchases). Your quarterly average of $998.60/month is still under target, so this is an early warning, not a trend yet.
   - **Gas:** it went from $133.63 to $236.22 to $426.99, roughly tripling over the quarter. Fill-ups went from 5 per month to 11 in August. Since you aren't budgeting gas, it's the increase you're least likely to notice.

Smaller finding: Planet Fitness bills you a $9.99 app fee every month plus separate charges of $54–$74 a month at the club, including two in July ($132.81 total). Check whether you're being billed twice.