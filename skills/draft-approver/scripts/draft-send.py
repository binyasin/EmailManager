#!/usr/bin/env python3
"""
Draft Approver — Send Gmail drafts via SMTP.
Usage:
  python draft-send.py list
  python draft-send.py send --uid <IMAP_UID>
  python draft-send.py send --to <recipient_name>
  python draft-send.py send --latest
  python draft-send.py delete --uid <IMAP_UID>
"""

import imaplib
import smtplib
import email
import sqlite3
import json
import sys
import os
import io

# Fix Unicode output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Paths ---
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.dirname(os.path.dirname(SKILL_DIR))  # up to workspace root
SMART_EMAIL_DB = os.path.join(WORKSPACE, "skills", "smart-email", "data", "email.db")

# --- Gmail IMAP/SMTP ---
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
DRAFTS_FOLDER = "[Gmail]/Drafts"
TRASH_FOLDER = "[Gmail]/Trash"


def get_credentials():
    """Read email credentials from smart-email's SQLite DB."""
    conn = sqlite3.connect(SMART_EMAIL_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT email, password FROM accounts LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        print(json.dumps({"error": "No email account configured in smart-email"}))
        sys.exit(1)
    return row[0], row[1]


def imap_connect():
    """Connect to Gmail IMAP."""
    email_addr, app_password = get_credentials()
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(email_addr, app_password)
    return mail, email_addr, app_password


def list_drafts():
    """List all drafts in Gmail."""
    mail, _, _ = imap_connect()
    mail.select(DRAFTS_FOLDER, readonly=True)
    
    result, data = mail.search(None, "ALL")
    if result != "OK" or not data[0]:
        mail.logout()
        return {"drafts": []}
    
    uids = data[0].split()
    drafts = []
    
    for uid in reversed(uids[-20:]):  # last 20, newest first
        result, msg_data = mail.fetch(uid, "(RFC822)")
        if result != "OK":
            continue
        
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except:
                        body_text = str(part.get_payload())[:300]
                    break
        else:
            try:
                body_text = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except:
                body_text = str(msg.get_payload())[:300]
        
        drafts.append({
            "uid": uid.decode(),
            "to": msg.get("To", "(no recipient)"),
            "subject": msg.get("Subject", "(no subject)"),
            "date": msg.get("Date", ""),
            "body_preview": body_text[:200].strip()
        })
    
    mail.logout()
    return {"drafts": drafts}


def get_draft_by_uid(mail, uid):
    """Fetch a specific draft by UID."""
    result, msg_data = mail.fetch(uid.encode(), "(RFC822)")
    if result != "OK":
        return None
    raw = msg_data[0][1]
    return email.message_from_bytes(raw)


def resolve_address(mail, to_field):
    """If To is just a bare name (no email), search inbox for the sender's address."""
    parsed = email.utils.parseaddr(to_field)
    name, addr = parsed
    # If we already have a valid email, return it
    if addr and '@' in addr:
        return to_field
    # Otherwise, search inbox for this name
    name_lower = (name or to_field).strip().lower()
    if not name_lower or len(name_lower) < 2:
        return to_field
    mail.select("INBOX", readonly=True)
    result, data = mail.search(None, f'(FROM "{name_lower}")')
    if result == "OK" and data[0]:
        uids = data[0].split()
        result, msg_data = mail.fetch(uids[-1], "(BODY.PEEK[HEADER.FIELDS (FROM)])")
        if result == "OK":
            raw = msg_data[0][1]
            hdr_msg = email.message_from_bytes(raw)
            from_field = hdr_msg.get("From", "")
            parsed2 = email.utils.parseaddr(from_field)
            if parsed2[1] and '@' in parsed2[1]:
                return f"{name} <{parsed2[1]}>" if name else from_field
    mail.select(DRAFTS_FOLDER)  # Switch back to drafts
    return to_field

def send_draft(msg, email_addr, app_password, mail=None):
    """Send an email via SMTP."""
    to_addr = msg.get("To", "")
    subject = msg.get("Subject", "")
    
    # Resolve bare-name To fields
    if mail and ('@' not in (email.utils.parseaddr(to_addr)[1] or '')):
        to_addr = resolve_address(mail, to_addr)
    
    # Build a fresh message for sending
    send_msg = MIMEMultipart()
    send_msg["From"] = email_addr
    send_msg["To"] = to_addr
    send_msg["Subject"] = subject
    send_msg["Date"] = email.utils.formatdate(localtime=True)
    
    # Copy In-Reply-To and References if present
    if msg.get("In-Reply-To"):
        send_msg["In-Reply-To"] = msg["In-Reply-To"]
    if msg.get("References"):
        send_msg["References"] = msg["References"]
    
    # Extract body
    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                except:
                    body_text = str(part.get_payload())
                break
    else:
        try:
            body_text = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except:
            body_text = str(msg.get_payload())
    
    send_msg.attach(MIMEText(body_text, "plain", "utf-8"))
    
    # Send via SMTP
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(email_addr, app_password)
        smtp.send_message(send_msg)
    
    return to_addr, subject


def delete_draft(mail, uid):
    """Move a draft to Trash."""
    mail.copy(uid.encode(), TRASH_FOLDER)
    mail.store(uid.encode(), "+FLAGS", "\\Deleted")
    mail.expunge()


def cmd_list():
    result = list_drafts()
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_send(uid=None, to_match=None, latest=False):
    mail, email_addr, app_password = imap_connect()
    mail.select(DRAFTS_FOLDER)
    
    target_uid = None
    
    if uid:
        target_uid = uid
    elif latest or to_match:
        # Search all drafts
        result, data = mail.search(None, "ALL")
        if result != "OK" or not data[0]:
            print(json.dumps({"error": "No drafts found"}))
            mail.logout()
            sys.exit(1)
        
        uids = list(reversed(data[0].split()))
        
        if to_match:
            to_lower = to_match.lower()
            for uid_bytes in uids:
                msg = get_draft_by_uid(mail, uid_bytes.decode())
                if msg and to_lower in (msg.get("To", "") or "").lower():
                    target_uid = uid_bytes.decode()
                    break
            if not target_uid:
                print(json.dumps({"error": f"No draft matching recipient '{to_match}' found"}))
                mail.logout()
                sys.exit(1)
        elif latest:
            target_uid = uids[0].decode()
    else:
        print(json.dumps({"error": "Specify --uid, --to, or --latest"}))
        mail.logout()
        sys.exit(1)
    
    # Fetch and send
    msg = get_draft_by_uid(mail, target_uid)
    if not msg:
        print(json.dumps({"error": f"Draft {target_uid} not found"}))
        mail.logout()
        sys.exit(1)
    
    try:
        to_addr, subject = send_draft(msg, email_addr, app_password, mail=mail)
        delete_draft(mail, target_uid)
        mail.logout()
        print(json.dumps({
            "sent": True,
            "to": to_addr,
            "subject": subject
        }, ensure_ascii=False))
    except Exception as e:
        mail.logout()
        print(json.dumps({"error": f"Failed to send: {str(e)}"}))
        sys.exit(1)


def cmd_delete(uid):
    mail, _, _ = imap_connect()
    mail.select(DRAFTS_FOLDER)
    delete_draft(mail, uid)
    mail.logout()
    print(json.dumps({"deleted": True, "uid": uid}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: draft-send.py [list|send|delete] [--uid ID] [--to NAME] [--latest]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    args = {}
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--uid" and i + 1 < len(sys.argv):
            args["uid"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--to" and i + 1 < len(sys.argv):
            args["to_match"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--latest":
            args["latest"] = True
            i += 1
        else:
            i += 1
    
    if cmd == "list":
        cmd_list()
    elif cmd == "send":
        cmd_send(**args)
    elif cmd == "delete":
        cmd_delete(**args)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
