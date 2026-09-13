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

SENDER = "alerts.pk@sc.com"
SUBJECT = "Standard Chartered: Transaction Alert"


def test_parses_credit_transaction():
    txn = parse_email(SENDER, CREDIT_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "credit"
    assert txn.amount == 3000.00
    assert txn.currency == "PKR"
    assert txn.own_account == "01-73***67-01"
    assert txn.counter_account == "****7537"
    assert txn.reference == "SADAPKKA202609121889170233706254"
    assert txn.date.strftime("%Y-%m-%d") == "2026-09-12"
    assert txn.bank == "Standard Chartered"


def test_parses_debit_transaction():
    txn = parse_email(SENDER, DEBIT_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "debit"
    assert txn.amount == 1250.50
    assert txn.counter_account == "****9981"
    assert txn.reference == "SADAPKKA202609121889170233706999"


def test_parses_html_body():
    txn = parse_email(SENDER, HTML_CREDIT_BODY, SUBJECT)
    assert txn is not None
    assert txn.txn_type == "credit"
    assert txn.amount == 3000.00
    assert txn.counter_account == "****7537"
    assert txn.reference == "SADAPKKA202609121889170233706254"


def test_unknown_sender_returns_none():
    txn = parse_email("someone@random.com", CREDIT_BODY, SUBJECT)
    assert txn is None


def test_unparseable_body_returns_none():
    txn = parse_email(SENDER, "This is not a transaction alert.", SUBJECT)
    assert txn is None
