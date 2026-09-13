"""Orchestrates: fetch new bank alert emails -> parse -> append to Google Sheet."""
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email_fetcher import fetch_new_emails, load_last_uid, save_last_uid
from src.parser import parse_email
from src.sheets import append_transactions, get_worksheet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("expense-tracker")


def main():
    load_dotenv()

    host = os.environ["EMAIL_HOST"]
    port = int(os.environ.get("EMAIL_PORT", "993"))
    user = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    folder = os.environ.get("EMAIL_FOLDER", "INBOX")
    senders = [s.strip() for s in os.environ["BANK_SENDERS"].split(",") if s.strip()]

    service_account_file = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    worksheet_name = os.environ.get("GOOGLE_WORKSHEET_NAME", "Transactions")

    state_file = os.environ.get("STATE_FILE", "state.json")

    since_date = None
    since_date_raw = os.environ.get("SINCE_DATE")
    if since_date_raw:
        since_date = datetime.strptime(since_date_raw, "%Y-%m-%d").strftime("%d-%b-%Y")

    last_uid = load_last_uid(state_file)
    log.info("Checking for emails newer than UID %s", last_uid)

    raw_emails = fetch_new_emails(
        host, port, user, password, folder, senders, last_uid, since_date=since_date
    )
    log.info("Fetched %d new email(s)", len(raw_emails))

    if not raw_emails:
        return

    transactions = []
    max_uid = last_uid
    for raw in raw_emails:
        max_uid = max(max_uid, raw.uid)
        txn = parse_email(raw.sender, raw.body, raw.subject)
        if txn is None:
            log.warning("Could not parse email from %s: %s", raw.sender, raw.subject)
            continue
        transactions.append(txn)

    log.info("Parsed %d transaction(s)", len(transactions))

    if transactions:
        worksheet = get_worksheet(service_account_file, sheet_id, worksheet_name)
        added = append_transactions(worksheet, transactions)
        log.info("Appended %d new row(s) to sheet (duplicates skipped)", added)

    save_last_uid(state_file, max_uid)


if __name__ == "__main__":
    main()
