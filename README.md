# Mamaearth Returns & Growth Intelligence Pipeline

## What this project is about

An online beauty brand sells products to customers in different cities and gets paid in different ways (Card, UPI, or Cash on Delivery). Some orders are returned. Returns cost money, so the business wants to know **where the returns are coming from**.

This project takes three small raw data files (customers, products, orders) and answers that question in three steps:

1. **SQL layer:** builds a small database and asks business questions with SQL.
2. **Analysis layer:** cleans the raw data with Python (pandas), finds patterns, draws two charts, and saves the key numbers in a file.
3. **Narrator layer:** turns those key numbers into a short written report (Situation, Complication, Resolution) that a manager can read.

Everything is rebuilt from the raw CSV files every time you run it, so the numbers can never drift away from the data.

## What we found

| Question | Answer |
|---|---|
| Total revenue after cleaning | INR 97,358.30 |
| Total revenue before cleaning | INR 99,860.20 |
| Revenue wrongly counted because of 5 duplicate orders | INR 2,501.90 |
| Return rate for Cash on Delivery (COD) | 44.4% |
| Return rate for UPI | 18.9% |
| Return rate for Card | 14.7% |
| Riskiest group | COD orders in Tier-2 cities: 54.5% returned (COD in Tier-1 cities: 37.5%) |
| Best sales month | March 2026 (INR 20,318.90) |
| January looked like the best month (INR 29,582.10) | It was inflated by two huge bulk orders. Without them January is INR 11,637.10 |
| Do bigger discounts reduce returns? | No. The link is negligible (correlation about -0.09) |

In short: COD has by far the highest return rate, and the problem is concentrated in Tier-2 cities. A single overall COD number would hide that.

## Repository structure

```
<repo>/
├── README.md
├── sql/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── reports.sql
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
├── analysis/
│   ├── clean_and_eda.py
│   └── visualize.py
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json
    ├── generate_narrative.py
    └── sample_output.txt
```

| File | What it does |
|---|---|
| `data/customers.csv` | 45 customers (city, city tier, signup date, how they found us) |
| `data/products.csv` | 16 products (name, category, price) |
| `data/orders.csv` | 180 raw orders (9 columns: who bought what, when, discount, payment method, rating, returned or not) |
| `sql/schema.sql` | Creates the three empty tables with rules (keys and checks) |
| `sql/seed_data.sql` | Fills the tables with the same rows as the CSV files |
| `sql/reports.sql` | The business questions written as SQL queries |
| `analysis/clean_and_eda.py` | Cleans the data, explores it, prints every result, and writes `narrator/findings.json` |
| `analysis/visualize.py` | Rebuilds the cleaned data and saves the two charts |
| `narrator/findings.json` | The key numbers, written by `clean_and_eda.py` (never typed by hand) |
| `narrator/generate_narrative.py` | Reads `findings.json` and writes the Situation / Complication / Resolution report |
| `narrator/sample_output.txt` | A saved example of the report written by the Gemini AI model |

## How the three layers fit together

```
data/*.csv  (the only source of truth)
   |
   |-----> SQL layer:      sql/*.sql  ->  shop.db  ->  report queries
   |
   |-----> Analysis layer: analysis/clean_and_eda.py  ->  narrator/findings.json
                           analysis/visualize.py      ->  visualizations/*.png
                                                              |
                                                              v
                           Narrator layer: narrator/generate_narrative.py
                           (reads ONLY narrator/findings.json)  ->  written report
```

In plain words:

- The three CSV files are the single source of truth.
- The **SQL layer** and the **analysis layer** each read the same raw data on their own. They do not depend on each other, and they are meant to give matching numbers, so each one double-checks the other.
- The **analysis layer** writes its key numbers into `narrator/findings.json`.
- The **narrator layer** reads only `findings.json`. It never opens the CSV files or the database. This means the written report always matches the numbers the analysis produced.

## Setup

You need:

- Python 3.10 or newer (this project was built on Python 3.14)
- The `sqlite3` command-line tool
- Python libraries:

```
pip install pandas matplotlib google-genai
```

Optional: a Gemini API key, used only by the narrator (see "About the written report" below). The project runs fully without one.

## How to run (exact order)

Open a terminal in the **repo root folder** (the folder that contains `sql`, `data`, `analysis`, and `narrator`) and run these in order. Use `python3` instead of `python` if your computer needs it.

**Step 1: SQL layer** (creates `shop.db`, which is rebuilt from the SQL files and not stored in the repo)

```
sqlite3 shop.db ".read sql/schema.sql"
sqlite3 shop.db ".read sql/seed_data.sql"
sqlite3 -header -column shop.db ".read sql/reports.sql"
```

Check the counts if you like: 45 customers, 16 products, 180 orders.

If you want to run Step 1 again, delete `shop.db` first. `reports.sql` adds a new column to a table, which can only be done once per fresh database.

**Step 2: Analysis layer**

```
python analysis/clean_and_eda.py
python analysis/visualize.py
```

- `clean_and_eda.py` prints every intermediate result and writes `narrator/findings.json`.
- `visualize.py` saves the two charts in `visualizations/`.

**Step 3: Narrator layer**

```
python narrator/generate_narrative.py
```

This prints the written report and then checks that the important numbers appear in it.

Always run the scripts from the repo root. The scripts find their files by their own location, so they also work if started from another folder.

## What the cleaning does

The raw orders file is deliberately messy. These are the fixes and the reason for each:

| Problem in the raw data | What we do | Why |
|---|---|---|
| Payment method written 7 ways (`COD`, `cod`, `Card`, `card`, `CARD`, `UPI`, `upi`) | Trim spaces and make uppercase, leaving 3 values: CARD, UPI, COD | The same method must not be counted as several |
| 5 duplicate orders (O0176 to O0180 repeat earlier orders under new IDs) | Remove them, leaving 175 orders | Counting a sale twice overstates revenue (by INR 2,501.90) |
| 12 blank discounts | Set to 0 | Business rule: blank means no promo code was used |
| 15 blank ratings | Fill with the median rating (3.0) | Keeps those orders in the analysis without pulling the average |
| 2 huge orders (O0011 with 25 items, O0098 with 30 items) | Flag them as outliers but do not delete them | They are real orders, but they distort the monthly trend, so we show the trend both with and without them |

## About the written report

`generate_narrative.py` can write the report in two ways, and the output has the same shape either way:

- **With AI (online):** if a Gemini API key is set, the AI model writes the report. It is given strict rules: three sections, and every number must come from `findings.json` with the same value.
- **Without AI (offline):** if there is no key, or the AI call fails, the script automatically uses a fixed template filled in from `findings.json`. This needs no key, no internet, and no setup.

To use the AI path, set your key in the terminal before running (never write the key inside any file in this repo):

```
# Windows PowerShell
$env:GEMINI_API_KEY="your-key-here"

# Mac or Linux
export GEMINI_API_KEY="your-key-here"
```

The script also checks that the five main figures (cleaned revenue 97358.3, COD return rate 44.4, riskiest group 54.5, duplicate amount 2501.9, and March with 20318.9) appear in the report, and that no number was invented.

`narrator/sample_output.txt` is a saved example of a real AI-written report that passed these checks. To make a fresh one, run:

```
python narrator/generate_narrative.py --save-sample
```

The AI model name is set in one place, the `MODEL_NAME` line near the top of `generate_narrative.py`. If Google retires that model, change that one line.

## Troubleshooting

- **"No such file" errors:** you are probably not in the repo root folder. Move into it and run again.
- **The AI call fails (busy server, bad key, timeout):** nothing breaks. The script prints a short message and uses the offline report.
- **`shop.db` errors about an existing column:** delete `shop.db` and run Step 1 again from the start.