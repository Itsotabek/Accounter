# Accounter — Telegram Accounting Bot

A runnable, button-driven bookkeeping system for Telegram. Version 0.5 simplifies the main menu, completes multilingual financial screens, and adds language-aware catalog labels around the double-entry ledger and FIFO inventory engine.

The service layer has no Telegram dependency. Telegram is the user interface; the same accounting services can later power a web app, API, desktop client, or country-specific compliance module.

## What it does

- Keeps every Telegram user's books, contacts, documents, and inventory separate.
- Offers Uzbek, Turkish, Italian, English, and Russian with a first-run language chooser and persistent per-user preference.
- Shows common product names and units in the selected language while preserving stable SKUs and accounting history. Unknown brand names stay unchanged instead of being mistranslated.
- Provides a persistent button menu and guided step-by-step forms, so normal use does not require slash commands.
- Creates a standard chart of accounts automatically for each user.
- Posts every new accounting operation using equal debits and credits.
- Records received income and paid expenses by category.
- Maintains customer and supplier contacts.
- Creates customer invoices and supplier bills with an optional percentage tax amount.
- Supports partial or full invoice receipts and supplier-bill payments.
- Tracks accounts receivable, accounts payable, due dates, and overdue documents.
- Shows Cash and Bank balances and records transfers between them.
- Supports controlled manual journals for opening balances and accountant adjustments.
- Corrects quick entries through auditable reversing entries instead of deleting history.
- Produces a current-month profit and loss statement, balance sheet, trial balance, receivables report, payables report, and general ledger activity.
- Provides a business dashboard combining cash, receivables, payables, FIFO inventory value, monthly income, expenses, and net profit.
- Includes Settings with language, on-demand AI enable/disable state, and a visible User/Owner role.
- Includes Help & AI with a usage guide, privacy/legal notice, ownership/support details, and release version.
- Provides an optional, read-only AI explanation panel. It is never called during normal accounting actions.
- Gives the configured owner a hidden, server-protected panel with user and health summaries.
- Safely removes zero-stock products from active inventory while preserving purchases, sales, allocations, and journal history.
- Includes smart last-cost/last-price suggestions, immediate oversell checks, and confirmation screens.
- Scans QR photos and accepts compact `fifo://` data, pasted JSON, or `.json` files to prefill products and transactions safely.
- Consumes purchase batches by `purchased_on`, then by batch ID for same-day purchases.
- Refuses an oversale and rolls the whole transaction back.
- Stores the exact purchase layers used by every sale.
- Calculates current quantity, FIFO inventory value, sale COGS, revenue, and gross profit.
- Preserves and imports the original FIFO journal history into the new general ledger automatically:
  - Purchase: Debit Inventory / Credit Accounts Payable.
  - Sale cost: Debit Cost of Goods Sold / Credit Inventory.
  - Sale revenue, when a price is supplied: Debit Cash / Accounts Receivable / Credit Sales Revenue.
- Uses SQLite by default and supports PostgreSQL through the same SQLAlchemy models and service layer.
- Optionally restricts access to a list of Telegram user IDs.

> This is an operational bookkeeping and management-reporting tool, not a substitute for a qualified accountant. Payroll, statutory tax returns, electronic invoicing, depreciation methods, bank feeds, and government filing rules vary by country and must be implemented as reviewed compliance modules. Do not treat the generic tax-rate field as a tax return.

## Project layout

```text
src/fifo_accounting_bot/
├── bot/
│   ├── app.py           # Telegram application assembly
│   ├── accounting_menu.py # General-accounting panels and guided forms
│   ├── handlers.py      # Command adapter
│   ├── menu.py          # Inventory menu and guided FIFO forms
│   ├── i18n.py          # Five-language buttons and information text
│   ├── parsers.py       # Command validation/parsing
│   ├── smart_import.py  # QR decoding and structured data import
│   └── formatters.py    # User-facing output
├── services/
│   ├── accounting.py    # Double-entry ledger, documents, payments, reports
│   ├── inventory.py     # Transactional FIFO inventory rules
│   ├── users.py         # Language, AI preference, and access state
│   └── ai_helper.py     # Optional read-only OpenAI Responses integration
├── config.py            # Environment configuration
├── database.py          # SQLAlchemy engine/session setup
├── localization.py      # Product, unit, and chart-of-account display labels
├── models.py            # Ledger, accounts, contacts, documents, FIFO records
├── accounting_schemas.py # General-accounting report objects
├── schemas.py           # FIFO service result objects
└── main.py              # Process entry point
tests/                   # Ledger, invoices, FIFO, rollback, UI, and validation tests
```

The dependency direction is `Telegram -> services -> database/models`. The accounting and inventory services can also be called from an API, CLI, web app, or another interface without changing their posting rules.

## Requirements

- Python 3.11 or newer
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- SQLite (included with Python), or PostgreSQL for deployment
- Optional: an OpenAI API key for the explicitly invoked AI helper

## Quick start with SQLite

1. Extract the ZIP and open a terminal in this project folder.

2. Create and activate a virtual environment.

   Windows PowerShell:

   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the project.

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

4. Copy `.env.example` to `.env`, then replace the token value.

   ```dotenv
   TELEGRAM_BOT_TOKEN=123456789:replace_with_real_token
   DATABASE_URL=sqlite:///./fifo_bot.db
   LOG_LEVEL=INFO
   ALLOWED_TELEGRAM_USER_IDS=
   OWNER_TELEGRAM_USER_IDS=123456789
   BOT_OWNER_NAME=Your name or business
   SUPPORT_CONTACT=@your_username
   OPENAI_API_KEY=
   OPENAI_MODEL=gpt-5.6-luna
   AI_MAX_OUTPUT_TOKENS=450
   ```

   To make the bot private, put one or more numeric Telegram user IDs in `ALLOWED_TELEGRAM_USER_IDS`, separated by commas. Put only trusted administrator IDs in `OWNER_TELEGRAM_USER_IDS`. Owner authorization is checked on the server for every owner action; hiding the button is not the security boundary.

   `OPENAI_API_KEY` is optional. With no key, the bot works normally and shows AI as not connected. An API request is made only after a user enables AI and taps **Ask AI** or **Explain my report**. Requests use `store=False`, include no Telegram ID, and give the model no database-write tools.

5. Run it.

   ```bash
   fifo-accounting-bot
   ```

   This equivalent command also works:

   ```bash
   python -m fifo_accounting_bot
   ```

Database tables are created automatically. Existing FIFO databases are upgraded non-destructively: the new tables are added and prior FIFO journal entries are synchronized into the general ledger when financial reports are first used. Stop the bot with `Ctrl+C`.

## Telegram button menu

Open the bot and tap **START** once. First choose Uzbek, Turkish, Italian, English, or Russian. The choice is remembered. The main menu then appears:

```text
🏠 Dashboard
💰 Sales & income       💸 Bills & expenses
📦 Inventory            📈 Financial reports
☰ More
```

The **☰ More** panel contains Cash & banking, Customers & suppliers, Activity, QR / Smart import, Help & AI, and Settings. This keeps the daily actions visible without crowding the home screen.

The configured owner sees **🛡 Owner panel** inside Settings; ordinary users cannot see or open it. Settings displays the current role but cannot promote a user. Owner IDs are controlled only through the private `OWNER_TELEGRAM_USER_IDS` environment variable. On Railway, add that variable to the **Accounter bot service**, not the PostgreSQL service, then deploy the pending change.

Product localization is display-only. For example, a product entered as `Pencil` remains tied to the same SKU and FIFO batches, but is displayed as `Qalam` in Uzbek, `Kurşun kalem` in Turkish, `Matita` in Italian, and `Карандаш` in Russian. Common catalog terms use the built-in glossary and a dedicated `product_translations` table. Custom names and brands are preserved as entered; more glossary entries or a reviewed translation provider can be added later without changing transactions.

Inside **💰 Sales & income**, record received income, create a customer invoice, receive an invoice payment, or open the FIFO sale flow. Inside **💸 Bills & expenses**, record a paid expense, create a supplier bill, pay it, or record a FIFO stock purchase.

Inside **🏦 Cash & banking**, view balances, transfer funds between Cash and Bank, create a manual journal, inspect the general ledger, or correct supported entries with a reversal. Inventory and invoice corrections deliberately require their own specialized workflow so the ledger cannot silently disagree with stock or document status.

Inside **📦 Inventory**, add products, record purchases and sales, view stock, or safely remove a zero-stock product. Removal is permitted only when remaining stock is zero. The product disappears from active workflows while its accounting history remains intact.

Tap an action and the bot asks for one value at a time, then shows a review card before writing. **❌ Cancel** and **⬅️ Main menu** are reserved controls and can never become accounting data. **↩️ Start over** clears the current draft and safely restarts its form. The general financial statements use the double-entry ledger; the separate FIFO performance report retains its preset and custom date ranges.

## QR scanner and smart import

Tap **📷 QR / Smart import**, then send one of these:

- A Telegram photo containing a QR code.
- A plain SKU such as `COFFEE-1`, or a QR containing `fifo://product/COFFEE-1`, to open quick Purchase/Sale actions.
- A pasted JSON transaction or a UTF-8 `.json` file up to 64 KB.
- A compact `fifo://purchase/...` or `fifo://sale/...` value generated by a label printer, scanner, POS export, or another trusted system.

Purchase JSON:

```json
{
  "type": "purchase",
  "sku": "COFFEE-1",
  "quantity": 10,
  "unit_cost": 8.5,
  "date": "2026-08-31"
}
```

Sale JSON:

```json
{
  "type": "sale",
  "sku": "COFFEE-1",
  "quantity": 2,
  "unit_price": 14,
  "date": "2026-08-31"
}
```

Compact QR equivalents:

```text
fifo://purchase/COFFEE-1?quantity=10&unit_cost=8.5&date=2026-08-31
fifo://sale/COFFEE-1?quantity=2&unit_price=14&date=2026-08-31
```

Product creation can also be imported with `type`, `sku`, `name`, and `unit`. Imported data never bypasses accounting controls: the SKU must exist for purchases/sales, quantities and dates are validated, oversales are rejected, and the user must tap **✅ Confirm** before anything is saved.

For automation and existing integrations, these slash commands remain available as a compatibility interface:

```text
/start
/addproduct SKU | Product name | unit
/purchase SKU QUANTITY UNIT_COST [YYYY-MM-DD]
/sale SKU QUANTITY [UNIT_PRICE] [YYYY-MM-DD]
/stock [SKU]
/report [START_DATE END_DATE]
```

Equivalent command example:

```text
/addproduct COFFEE-1 | Arabica beans | kg
/purchase COFFEE-1 10 8.50 2026-08-01
/purchase COFFEE-1 5 9.25 2026-08-10
/sale COFFEE-1 12 14.00 2026-08-20
/stock COFFEE-1
/report 2026-08-01 2026-08-31
```

In the guided menu, tap **📅 Today** to use today's date. The sale price is optional. If omitted, the bot still records the sale and COGS, but gross profit reports exclude that unpriced sale and its COGS. Use a dot for decimal values. Quantities and monetary source values are stored to four decimal places; displayed totals are rounded to two.

## How FIFO is calculated

If the database contains:

| Batch | Date | Remaining before sale | Unit cost |
|---|---:|---:|---:|
| 1 | 2026-08-01 | 10 | 8.50 |
| 2 | 2026-08-10 | 5 | 9.25 |

A sale of 12 consumes 10 from batch 1 and 2 from batch 2:

```text
COGS = (10 × 8.50) + (2 × 9.25) = 103.50
Remaining stock = 3 × 9.25 = 27.75
```

The sale, both allocations, reduced batch balances, and journal entries are committed in one database transaction. An error rolls them all back. PostgreSQL also applies row locks to open FIFO batches during a sale; SQLite is suitable for a single local bot process.

## Run the tests

```bash
python -m pip install -e ".[dev]"
pytest
```

The test suite covers balanced quick entries, profit and loss, balance sheet equality, invoices, bills, partial payments, receivables/payables, auditable reversals, legacy FIFO-ledger synchronization, chronological FIFO consumption, rollback on insufficient stock, per-user isolation, menu safety, smart-import validation, and a real QR encode/decode round trip.

## Move to PostgreSQL

The PostgreSQL driver is already included. Start the optional local database:

```bash
docker compose up -d postgres
```

Then change `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://fifo_bot:fifo_bot@localhost:5432/fifo_bot
```

Restart the bot; it creates the initial schema. For an evolving production deployment, add Alembic migrations before changing models, use managed secrets instead of a committed `.env`, back up the database, and run only one schema migration job during deployment.

SQLite data is not copied automatically. For a real migration, export and import each table while preserving primary keys and foreign-key order, or write a one-time SQLAlchemy transfer script and reconcile total quantities, inventory value, COGS, and journal entry counts afterward.

## Deploy on Railway

Railway must build from the directory that directly contains `Dockerfile`,
`pyproject.toml`, `requirements.txt`, and `src`. Do not upload the ZIP itself as
the repository contents. Extract it, then place the files inside the extracted
project directory at the top level of the GitHub repository. If the repository
already contains a wrapper directory named `fifo-telegram-accounting-bot`, set
the Railway service **Root Directory** to `/fifo-telegram-accounting-bot`.

1. In Railway, choose **New Project -> Deploy from GitHub repo**.
2. Add **PostgreSQL** from the project's **+ New** menu.
3. In the bot service's **Variables** tab, add:

   ```dotenv
   TELEGRAM_BOT_TOKEN=your-token-from-BotFather
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   LOG_LEVEL=INFO
   OWNER_TELEGRAM_USER_IDS=your-numeric-telegram-user-id
   ALLOWED_TELEGRAM_USER_IDS=
   BOT_OWNER_NAME=Your name or company
   SUPPORT_CONTACT=@your_bot_username
   ```

   Use the actual PostgreSQL service name if Railway did not name it `Postgres`.
   Leave `OPENAI_API_KEY` unset when AI is not required. Seal the Telegram token
   after saving it.

4. Railway automatically detects the included `Dockerfile`. Clear any old custom
   command such as `start.sh`. If a Start Command override is present, set it to
   the stable `src`-layout launcher:

   ```text
   python run.py
   ```

5. Deploy as one persistent service. The bot uses Telegram long polling, so it
   does not need a generated public domain or an HTTP port.

The first run creates the database schema. When the Railway deployment is
healthy, stop the local copy of the bot: Telegram permits only one polling
process per bot token. The local SQLite database is not transferred to Railway
automatically.

## Add another accounting service

1. Put its business rules in a new module under `services/`; accept the shared session factory and keep Telegram types out.
2. Add its database entities to `models.py` (or split models into a package as the project grows).
3. Add a handler module under `bot/` with a `register(application)` method.
4. Register that module in `bot/app.py`.
5. Cover business rules with service-level tests; handler tests should focus only on parsing and responses.

The next useful modules are bank-statement import/reconciliation, attachments and receipt OCR, fixed-asset schedules, recurring entries, multi-currency revaluation, document PDFs, and country-reviewed payroll/tax/e-invoicing adapters. The core already uses a journal header plus multiple ledger lines and rejects unbalanced postings before commit.

## Production checklist

- Set `ALLOWED_TELEGRAM_USER_IDS` unless this is intentionally a public service.
- Use PostgreSQL for multiple processes or meaningful concurrent traffic.
- Add Alembic migrations and automated database backups.
- Use a secret manager for the Telegram token and database credentials.
- Add currency and organization models before supporting multiple currencies or companies per user.
- Decide how returns, batch corrections, taxes, discounts, landed cost, and negative inventory should work; this starter intentionally rejects negative inventory.
- Configure centralized logging and monitoring without logging Telegram tokens or sensitive message contents.

## License

MIT
