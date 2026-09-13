"""Fetches new bank alert emails over IMAP."""
import email
import imaplib
import json
import os
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from typing import List


@dataclass
class RawEmail:
    uid: int
    sender: str
    subject: str
    body: str


def _decode(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = ""
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded += text.decode(charset or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/plain" and "attachment" not in disposition:
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    charset = msg.get_content_charset() or "utf-8"
    payload = msg.get_payload(decode=True)
    return payload.decode(charset, errors="replace") if payload else ""


def load_last_uid(state_file: str) -> int:
    if not os.path.exists(state_file):
        return 0
    with open(state_file, "r") as f:
        return json.load(f).get("last_uid", 0)


def save_last_uid(state_file: str, uid: int) -> None:
    with open(state_file, "w") as f:
        json.dump({"last_uid": uid}, f)


def fetch_new_emails(
    host: str,
    port: int,
    user: str,
    password: str,
    folder: str,
    senders: List[str],
    last_uid: int,
) -> List[RawEmail]:
    """Fetch emails from the given senders with UID greater than last_uid."""
    results: List[RawEmail] = []

    conn = imaplib.IMAP4_SSL(host, port)
    try:
        conn.login(user, password)
        conn.select(folder)

        sender_criteria = " ".join(f'FROM "{s}"' for s in senders)
        if len(senders) > 1:
            # (OR FROM "a" (OR FROM "b" FROM "c")) style nesting
            search_expr = senders[0]
            or_expr = f'FROM "{senders[0]}"'
            for s in senders[1:]:
                or_expr = f'(OR {or_expr} FROM "{s}")'
            criteria = f"UID {last_uid + 1}:* {or_expr}"
        else:
            criteria = f'UID {last_uid + 1}:* FROM "{senders[0]}"'

        status, data = conn.uid("search", None, criteria)
        if status != "OK" or not data or not data[0]:
            return results

        uids = [int(u) for u in data[0].split()]
        uids = [u for u in uids if u > last_uid]

        for uid in uids:
            status, msg_data = conn.uid("fetch", str(uid), "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw_msg = msg_data[0][1]
            msg = email.message_from_bytes(raw_msg)

            sender_header = _decode(msg.get("From", ""))
            # Extract bare email address from "Name <addr>" form
            if "<" in sender_header and ">" in sender_header:
                sender = sender_header.split("<")[1].split(">")[0].strip()
            else:
                sender = sender_header.strip()

            subject = _decode(msg.get("Subject", ""))
            body = _extract_body(msg)

            results.append(RawEmail(uid=uid, sender=sender, subject=subject, body=body))

        return results
    finally:
        try:
            conn.logout()
        except Exception:
            pass
