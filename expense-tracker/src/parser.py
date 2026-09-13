"""Parsers that turn bank alert email bodies into transaction records."""
import html
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


def _clean_body(body: str) -> str:
    """Strip HTML tags/entities so regexes see plain, contiguous text.

    Bank alert emails are usually sent as HTML; a tag sitting between two
    words (e.g. "account</span> <b>01-73...") would otherwise break a
    pattern that expects them adjacent.
    """
    text = re.sub(r"<[^>]+>", " ", body)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Transaction:
    date: datetime
    txn_type: str  # "credit" or "debit"
    amount: float
    currency: str
    own_account: str
    counter_account: str
    reference: str
    bank: str
    raw_subject: str


# Standard Chartered PK sends alerts like:
# "Your account 01-73***67-01 has been credited with amount PKR 3,000.00
#  from account ****7537 SADAPKKA202609121889170233706254 on 12/09/26."
# (or "debited ... to account ...")
_SC_PATTERN = re.compile(
    r"account\s+(?P<own_account>\S+)\s+has been\s+"
    r"(?P<txn_type>credited|debited)\s+with amount\s+"
    r"(?P<currency>[A-Z]{3})\s*(?P<amount>[\d,]+\.\d{2})\s+"
    r"(?:from|to)\s+account\s+(?P<counter_account>\S+)\s+"
    r"(?P<reference>\S+)\s+on\s+(?P<date>\d{2}/\d{2}/\d{2})",
    re.IGNORECASE,
)


def parse_standard_chartered(body: str, subject: str) -> Optional[Transaction]:
    text = _clean_body(body)
    match = _SC_PATTERN.search(text)
    if not match:
        return None

    fields = match.groupdict()
    txn_type = "credit" if fields["txn_type"].lower() == "credited" else "debit"

    return Transaction(
        date=datetime.strptime(fields["date"], "%d/%m/%y"),
        txn_type=txn_type,
        amount=float(fields["amount"].replace(",", "")),
        currency=fields["currency"],
        own_account=fields["own_account"],
        counter_account=fields["counter_account"],
        reference=fields["reference"],
        bank="Standard Chartered",
        raw_subject=subject,
    )


# Map sender address -> parser function. Add more banks here as needed.
BANK_PARSERS = {
    "alerts.pk@sc.com": parse_standard_chartered,
}


def parse_email(sender: str, body: str, subject: str) -> Optional[Transaction]:
    parser = BANK_PARSERS.get(sender.lower())
    if parser is None:
        return None
    return parser(body, subject)
