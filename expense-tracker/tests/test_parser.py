import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser import parse_email

CREDIT_BODY = """
Dear Client,
Alerts
September 12 2026, 01:17 PM

Your account 01-73***67-01 has been credited with amount PKR 3,000.00 from
account ****7537 SADAPKKA202609121889170233706254 on 12/09/26.

Don't miss out on the latest Standard Chartered promotions & benefits.
"""

DEBIT_BODY = """
Dear Client,
Alerts
September 12 2026, 02:45 PM

Your account 01-73***67-01 has been debited with amount PKR 1,250.50 to
account ****9981 SADAPKKA202609121889170233706999 on 12/09/26.

Don't miss out on the latest Standard Chartered promotions & benefits.
"""

HTML_CREDIT_BODY = """
<html><body>
<p>Dear Client,</p>
<p>Alerts<br>September 12 2026, 01:17&nbsp;PM</p>
<p>Your account <b>01-73***67-01</b> has been <b>credited</b> with amount
PKR&nbsp;3,000.00 from account <b>****7537</b>
SADAPKKA202609121889170233706254 on 12/09/26.</p>
<p>Don't miss out on the latest Standard Chartered promotions &amp; benefits.</p>
</body></html>
"""

ONLINE_TRANSFER_BODY = """
Dear Client,
Alerts
September 08 2026, 05:00 PM

A transaction of PKR 8,000.00 has been completed on Acc. Number 01-73***67-01
to ****7537 on 08/09/26 through SC Raast Online Banking. Thank you!

Don't miss out on the latest Standard Chartered promotions & benefits.
"""

CARD_PAYMENT_BODY = """
Dear Client,
Alerts
September 07 2026, 03:02 PM

SCBPL: PKR 609.00 have been paid at SWEET CREME LAHORE PAK using MasterCard
Platinum 1738 on 07-09-26. Avail Limit PKR20924.06. For assistance call
111-002-002. Happy shopping!
"""

ONLINE_CARD_BODY = """
Dear Client,
Alerts
September 07 2026, 01:33 AM

An online transaction has been made from your card no. ending with 1738 for
PKR 1,017.98 at FOOD PANDA KARACHI PAK. Avail Limit PKR21533.06. SCBPL
"""

SENDER = "alerts.pk@sc.com"
SUBJECT = "Standard Chartered: Transaction Alert"


def test_parses_credit_transaction():
    txn = parse_email(SENDER, CREDIT_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "credit"
    assert txn.amount == 3000.00
    assert txn.currency == "PKR"
    assert txn.own_account == "01-73***67-01"
    assert txn.counterparty == "****7537"
    assert txn.reference == "SADAPKKA202609121889170233706254"
    assert txn.date.strftime("%Y-%m-%d") == "2026-09-12"
    assert txn.bank == "Standard Chartered"


def test_parses_debit_transaction():
    txn = parse_email(SENDER, DEBIT_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "debit"
    assert txn.amount == 1250.50
    assert txn.counterparty == "****9981"
    assert txn.reference == "SADAPKKA202609121889170233706999"


def test_parses_html_body():
    txn = parse_email(SENDER, HTML_CREDIT_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "credit"
    assert txn.amount == 3000.00
    assert txn.counterparty == "****7537"
    assert txn.reference == "SADAPKKA202609121889170233706254"


def test_parses_online_transfer():
    txn = parse_email(SENDER, ONLINE_TRANSFER_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "debit"
    assert txn.amount == 8000.00
    assert txn.currency == "PKR"
    assert txn.own_account == "01-73***67-01"
    assert txn.counterparty == "****7537"
    assert txn.date.strftime("%Y-%m-%d") == "2026-09-08"


def test_parses_card_payment():
    txn = parse_email(SENDER, CARD_PAYMENT_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "debit"
    assert txn.amount == 609.00
    assert txn.currency == "PKR"
    assert txn.own_account == "Card •1738"
    assert txn.counterparty == "SWEET CREME LAHORE PAK"
    assert txn.date.strftime("%Y-%m-%d") == "2026-09-07"


def test_parses_online_card_transaction():
    txn = parse_email(SENDER, ONLINE_CARD_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "debit"
    assert txn.amount == 1017.98
    assert txn.currency == "PKR"
    assert txn.own_account == "Card •1738"
    assert txn.counterparty == "FOOD PANDA KARACHI PAK"
    assert txn.date.strftime("%Y-%m-%d %H:%M") == "2026-09-07 01:33"


def test_unknown_sender_returns_none():
    txn = parse_email("someone@random.com", CREDIT_BODY, SUBJECT)
    assert txn is None


def test_unparseable_body_returns_none():
    txn = parse_email(SENDER, "This is not a transaction alert.", SUBJECT)
    assert txn is None
