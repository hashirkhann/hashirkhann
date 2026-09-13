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

    if not worksheet.row_values(1):
        worksheet.append_row(HEADER)

    return worksheet


def existing_references(worksheet) -> Set[str]:
    header = worksheet.row_values(1)
    if "Reference" not in header:
        return set()
    col_index = header.index("Reference") + 1
    values = worksheet.col_values(col_index)[1:]  # skip header
    return set(values)


def append_transactions(worksheet, transactions: List[Transaction]) -> int:
    seen_refs = existing_references(worksheet)
    rows = []

    for txn in transactions:
        if txn.reference in seen_refs:
            continue
        seen_refs.add(txn.reference)

        debit = txn.amount if txn.txn_type == "debit" else ""
        credit = txn.amount if txn.txn_type == "credit" else ""

        rows.append([
            txn.date.strftime("%Y-%m-%d"),
            debit,
            credit,
            txn.currency,
            txn.bank,
            txn.own_account,
            txn.counter_account,
            txn.reference,
            txn.raw_subject,
        ])

    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    return len(rows)
