"""Parsers that turn bank alert email bodies into transaction records."""
import html
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    date: datetime
    txn_type: str  # "credit" or "debit"
    amount: float
    currency: str
    own_account: str
    counterparty: str
    reference: str
    bank: str
    raw_subject: str
    message_id: str = ""


def _clean_body(body: str) -> str:
    """Strip HTML tags/entities so regexes see plain, contiguous text.

    Bank alert emails are usually sent as HTML; a tag sitting between two
    words (e.g. "account</span> <b>01-73...") would otherwise break a
    pattern that expects them adjacent.
    """
    text = re.sub(r"<[^>]+>", " ", body)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# Every Standard Chartered alert carries this header line regardless of
# transaction type, and it's more reliable than the per-template date
# formats buried in the body (which vary: DD/MM/YY, DD-MM-YY, or absent).
_HEADER_DATE_PATTERN = re.compile(
    r"Alerts\s+(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2})\s+(?P<year>\d{4}),\s*"
    r"(?P<time>\d{1,2}:\d{2}\s*[AP]M)",
    re.IGNORECASE,
)


def _extract_alert_datetime(text: str) -> Optional[datetime]:
    match = _HEADER_DATE_PATTERN.search(text)
    if not match:
        return None
    raw = f"{match['month']} {match['day']} {match['year']} {match['time'].upper()}"
    try:
        return datetime.strptime(raw, "%B %d %Y %I:%M %p")
    except ValueError:
        return None


# 1. Account-to-account transfer, explicit credited/debited wording:
# "Your account 01-73***67-01 has been credited with amount PKR 3,000.00
#  from account ****7537 SADAPKKA202609121889170233706254 on 12/09/26."
_ACCOUNT_TRANSFER_PATTERN = re.compile(
    r"account\s+(?P<own_account>\S+)\s+has been\s+"
    r"(?P<txn_type>credited|debited)\s+with amount\s+"
    r"(?P<currency>[A-Z]{3})\s*(?P<amount>[\d,]+\.\d{2})\s+"
    r"(?:from|to)\s+account\s+(?P<counterparty>\S+)\s+"
    r"(?P<reference>\S+)\s+on\s+\d{2}/\d{2}/\d{2}",
    re.IGNORECASE,
)

# 2. Raast / online banking transfer, no explicit credit/debit word — "to X"
# always means money left the account, so it's a debit:
# "A transaction of PKR 8,000.00 has been completed on Acc. Number
#  01-73***67-01 to ****7537 on 08/09/26 through SC Raast Online Banking."
_ONLINE_TRANSFER_PATTERN = re.compile(
    r"transaction of\s+(?P<currency>[A-Z]{3})\s*(?P<amount>[\d,]+\.\d{2})\s+"
    r"has been completed on Acc\.?\s*Number\s+(?P<own_account>\S+)\s+to\s+"
    r"(?P<counterparty>\S+)\s+on\s+\d{2}/\d{2}/\d{2}",
    re.IGNORECASE,
)

# 3. Card purchase (in-person):
# "SCBPL: PKR 609.00 have been paid at SWEET CREME LAHORE PAK using
#  MasterCard Platinum 1738 on 07-09-26."
_CARD_PAYMENT_PATTERN = re.compile(
    r"(?P<currency>[A-Z]{3})\s*(?P<amount>[\d,]+\.\d{2})\s+have been paid at\s+"
    r"(?P<merchant>.+?)\s+using\s+.+?\s+(?P<card_last4>\d{4})\s+on\s+\d{2}-\d{2}-\d{2}",
    re.IGNORECASE,
)

# 4. Card purchase (online):
# "An online transaction has been made from your card no. ending with 1738
#  for PKR 1,017.98 at FOOD PANDA KARACHI PAK."
_ONLINE_CARD_PATTERN = re.compile(
    r"card no\.?\s+ending with\s+(?P<card_last4>\d{4})\s+for\s+"
    r"(?P<currency>[A-Z]{3})\s*(?P<amount>[\d,]+\.\d{2})\s+at\s+(?P<merchant>.+?)\.",
    re.IGNORECASE,
)


def parse_standard_chartered(body: str, subject: str) -> Optional[Transaction]:
    text = _clean_body(body)
    alert_dt = _extract_alert_datetime(text) or datetime.now()

    match = _ACCOUNT_TRANSFER_PATTERN.search(text)
    if match:
        fields = match.groupdict()
        txn_type = "credit" if fields["txn_type"].lower() == "credited" else "debit"
        return Transaction(
            date=alert_dt,
            txn_type=txn_type,
            amount=float(fields["amount"].replace(",", "")),
            currency=fields["currency"],
            own_account=fields["own_account"],
            counterparty=fields["counterparty"],
            reference=fields["reference"],
            bank="Standard Chartered",
            raw_subject=subject,
        )

    match = _ONLINE_TRANSFER_PATTERN.search(text)
    if match:
        fields = match.groupdict()
        return Transaction(
            date=alert_dt,
            txn_type="debit",
            amount=float(fields["amount"].replace(",", "")),
            currency=fields["currency"],
            own_account=fields["own_account"],
            counterparty=fields["counterparty"],
            reference="",
            bank="Standard Chartered",
            raw_subject=subject,
        )

    match = _CARD_PAYMENT_PATTERN.search(text)
    if match:
        fields = match.groupdict()
        return Transaction(
            date=alert_dt,
            txn_type="debit",
            amount=float(fields["amount"].replace(",", "")),
            currency=fields["currency"],
            own_account=f"Card •{fields['card_last4']}",
            counterparty=fields["merchant"].strip(),
            reference="",
            bank="Standard Chartered",
            raw_subject=subject,
        )

    match = _ONLINE_CARD_PATTERN.search(text)
    if match:
        fields = match.groupdict()
        return Transaction(
            date=alert_dt,
            txn_type="debit",
            amount=float(fields["amount"].replace(",", "")),
            currency=fields["currency"],
            own_account=f"Card •{fields['card_last4']}",
            counterparty=fields["merchant"].strip(),
            reference="",
            bank="Standard Chartered",
            raw_subject=subject,
        )

    return None


# Map sender address -> parser function. Add more banks here as needed.
BANK_PARSERS = {
    "alerts.pk@sc.com": parse_standard_chartered,
}


def parse_email(sender: str, body: str, subject: str) -> Optional[Transaction]:
    parser = BANK_PARSERS.get(sender.lower())
    if parser is None:
        return None
    return parser(body, subject)
