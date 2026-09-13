"""Writes parsed transactions to a Google Sheet, skipping duplicates."""
from typing import List, Set

import gspread
from google.oauth2.service_account import Credentials

from .parser import Transaction

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

HEADER = [
    "Date",
    "Debit",
    "Credit",
    "Currency",
    "Bank",
    "Account",
    "Counterparty Account",
    "Reference",
    "Subject",
    "Message ID",
]


def get_worksheet(service_account_file: str, sheet_id: str, worksheet_name: str):
    creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=len(HEADER))
        worksheet.append_row(HEADER)

    header = worksheet.row_values(1)
    if not header:
        worksheet.append_row(HEADER)
    elif "Message ID" not in header:
        # Migrate sheets created before de-dup switched from bank reference
        # (not every transaction type has one) to the email's Message ID.
        worksheet.update_cell(1, len(header) + 1, "Message ID")

    return worksheet


def existing_message_ids(worksheet) -> Set[str]:
    header = worksheet.row_values(1)
    if "Message ID" not in header:
        return set()
    col_index = header.index("Message ID") + 1
    values = worksheet.col_values(col_index)[1:]  # skip header
    return {v for v in values if v}


def append_transactions(worksheet, transactions: List[Transaction]) -> int:
    header = worksheet.row_values(1)
    seen_ids = existing_message_ids(worksheet)
    rows = []

    for txn in transactions:
        if txn.message_id and txn.message_id in seen_ids:
            continue
        if txn.message_id:
            seen_ids.add(txn.message_id)

        debit = txn.amount if txn.txn_type == "debit" else ""
        credit = txn.amount if txn.txn_type == "credit" else ""

        mapping = {
            "Date": txn.date.strftime("%Y-%m-%d"),
            "Debit": debit,
            "Credit": credit,
            "Currency": txn.currency,
            "Bank": txn.bank,
            "Account": txn.own_account,
            "Counterparty Account": txn.counterparty,
            "Reference": txn.reference,
            "Subject": txn.raw_subject,
            "Message ID": txn.message_id,
        }
        rows.append([mapping.get(col, "") for col in header])

    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    return len(rows)
