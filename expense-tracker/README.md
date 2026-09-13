# Expense Tracker

Automatically reads bank transaction alert emails, parses the amount and
credit/debit type, and appends them as rows in a Google Sheet.

Currently supports **Standard Chartered Pakistan** (`alerts.pk@sc.com`)
transaction alert emails. More banks can be added in `src/parser.py`.

## How it works

1. Connects to your mailbox over IMAP and fetches new emails from the
   configured bank sender address(es).
2. Parses each email body with a regex tuned to that bank's format,
   extracting: date, amount, currency, credit/debit type, your account,
   the counterparty account, and the transaction reference.
3. Appends a row to a Google Sheet with the amount placed in the **Debit**
   or **Credit** column automatically, based on the transaction type.
4. Skips transactions it has already added, by checking the transaction
   reference already in the sheet, and also tracks the last processed
   email UID in `state.json` so re-runs don't reprocess old mail.

## Setup

### 1. Email access (IMAP)

If using Gmail, enable IMAP and create an
[App Password](https://myaccount.google.com/apppasswords) (regular login
passwords won't work with IMAP). Any other IMAP-capable provider works too.

### 2. Google Sheet + service account

1. Create a Google Cloud project, enable the **Google Sheets API**.
2. Create a **Service Account**, download its JSON key, save it as
   `credentials.json` in this folder (or point `GOOGLE_SERVICE_ACCOUNT_FILE`
   at it).
3. Create a Google Sheet and share it with the service account's email
   address (found in the JSON key, `client_email` field) with Editor access.
4. Copy the Sheet ID from its URL:
   `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

### 3. Configure

```bash
cp .env.example .env
# edit .env with your IMAP credentials, bank sender, and sheet ID
```

### 4. Install dependencies and run

```bash
pip install -r requirements.txt
python3 -m src.main
```

Run it again any time — it only appends new, unseen transactions.

## Scheduling it automatically

**Cron (simplest, runs on your own machine/server):**

```cron
*/15 * * * * cd /path/to/expense-tracker && /usr/bin/python3 -m src.main >> run.log 2>&1
```

**GitHub Actions:** see `.github/workflows/run.yml` for a scheduled workflow
you can adapt — store `.env` values and `credentials.json` contents as
repository secrets rather than committing them (add secrets under
`GOOGLE_CREDENTIALS_JSON`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`,
`EMAIL_PASS`, `EMAIL_FOLDER`, `BANK_SENDERS`, `GOOGLE_SHEET_ID`,
`GOOGLE_WORKSHEET_NAME`). The workflow commits the updated `state.json`
back to the repo after each run so it doesn't reprocess old emails —
that's why `state.json` is tracked in git rather than ignored, and it
will get rewritten by local runs too.

## Adding another bank

Add a new parser function in `src/parser.py` following the pattern of
`parse_standard_chartered`, then register it in `BANK_PARSERS` keyed by the
sender's email address. Add a test in `tests/test_parser.py` with a sample
(sanitized) email body.

## Testing

```bash
pip install pytest
python3 -m pytest tests/ -v
```
