from dataclasses import dataclass
from datetime import datetime
import logging
import traceback
import subprocess
import json
import sqlite3
import os
import re
import time
import imaplib
import requests
from dotenv import dotenv_values
from email.mime.text import MIMEText
from email.utils import parseaddr, formatdate, make_msgid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("EmailHeartbeat")

# --------------------------------------------------
# Configuration
# --------------------------------------------------

AUTO_TRASH = True
AUTO_DRAFT = True
SAVE_SUMMARY = True

SKILL_DIR = os.environ.get("EMAIL_SKILL_DIR", r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\skills\smart-email")
DB_PATH = os.path.join(SKILL_DIR, "data", "email.db")
CONFIG_PATH = os.path.join(SKILL_DIR, "data", "config.json")
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# --------------------------------------------------
# Email Object
# --------------------------------------------------

@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str

# --------------------------------------------------
# Gmail via smart-email CLI integration
# --------------------------------------------------

class GmailService:

    def fetch_unread(self):
        """
        Uses the smart-email CLI check command to query real unread emails.
        """
        try:
            cli_path = os.path.join(SKILL_DIR, "cli.js")
            # Pull unread emails from the last 1440 minutes (24 hours) up to 20 emails
            cmd = f'node "{cli_path}" check --since 1440 --max 20'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
            if result.returncode == 0:
                data = json.loads(result.stdout)
                emails = []
                for item in data.get("emails", []):
                    emails.append(Email(
                        id=item.get("uid"),
                        sender=item.get("from", "Unknown Sender"),
                        subject=item.get("subject", "No Subject"),
                        body=item.get("bodyPreview", "")
                    ))
                return emails
            else:
                logger.error(f"Failed to fetch emails via CLI: {result.stderr}")
        except Exception as e:
            logger.error(f"Error fetching unread emails: {e}")
        return []

    def __init__(self):
        self.imap = None

    def connect(self):
        """
        Opens one IMAP session for the whole run, reused for draft creation,
        mark-as-read, and trash operations so each email is only touched once.
        """
        env = dotenv_values(ENV_PATH)
        user = env.get("EMAIL_USER")
        app_password = env.get("EMAIL_APP_PASSWORD")
        imap_host = env.get("IMAP_HOST", "imap.gmail.com")
        imap_port = int(env.get("IMAP_PORT", 993))

        if not user or not app_password:
            logger.error("Missing EMAIL_USER/EMAIL_APP_PASSWORD in .env; cannot connect to Gmail")
            return

        self.imap = imaplib.IMAP4_SSL(imap_host, imap_port)
        self.imap.login(user, app_password)
        self.imap.select("INBOX")

    def close(self):
        if self.imap:
            try:
                self.imap.close()
            except Exception:
                pass
            try:
                self.imap.logout()
            except Exception:
                pass
            self.imap = None

    def mark_seen(self, email):
        """
        Flags the message \\Seen so it drops out of the unread set fetched next
        run, preventing the same email from being re-processed/re-drafted.
        """
        if not self.imap:
            return
        try:
            self.imap.uid("STORE", str(email.id), "+FLAGS", "(\\Seen)")
        except Exception as e:
            logger.error(f"Failed to mark '{email.subject}' as read: {e}")

    def trash(self, email):
        """
        Actually moves the message to Gmail's Trash (copy to Trash, flag
        \\Deleted on the original, expunge) instead of just logging locally -
        this both removes it from the inbox and keeps it out of future unread
        fetches.
        """
        self._log_trash_locally(email)
        if not self.imap:
            return
        try:
            trash_mailbox = self._find_special_mailbox("\\Trash") or "[Gmail]/Trash"
            self.imap.uid("COPY", str(email.id), trash_mailbox)
            self.imap.uid("STORE", str(email.id), "+FLAGS", "(\\Deleted)")
            self.imap.expunge()
            logger.info(f"Moved to Gmail Trash: {email.subject}")
        except Exception as e:
            logger.error(f"Failed to trash '{email.subject}': {e}")
            logger.error(traceback.format_exc())

    def save_draft(self, email, draft):
        """
        Creates a real Gmail draft (IMAP APPEND to the Drafts mailbox, never sent
        automatically) and logs it locally in the SQLite email.db.
        """
        self._log_draft_locally(email, draft)

        if not draft:
            logger.info(f"No draft_reply text for '{email.subject}'; skipping Gmail draft creation.")
            return

        try:
            self._create_gmail_draft(email, draft)
        except Exception as e:
            logger.error(f"Failed to create Gmail draft for '{email.subject}': {e}")
            logger.error(traceback.format_exc())

    def _log_draft_locally(self, email, draft):
        logger.info(f"Draft prepared for {email.subject}: '{draft[:60]}...'")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drafts (
                    email_uid TEXT PRIMARY KEY,
                    subject TEXT,
                    draft_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute(
                "INSERT OR REPLACE INTO drafts (email_uid, subject, draft_content) VALUES (?, ?, ?)",
                (email.id, email.subject, draft)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Database draft-saving error: {e}")

    def _create_gmail_draft(self, email, draft):
        """
        Builds a reply message and APPENDs it with the \\Draft flag directly to the
        account's Drafts mailbox over IMAP. This creates a real, visible Gmail draft
        that the user must open and send themselves - nothing is ever sent automatically.
        """
        if not self.imap:
            logger.error("No IMAP connection; cannot create Gmail draft")
            return

        env = dotenv_values(ENV_PATH)
        user = env.get("EMAIL_USER")

        _, to_addr = parseaddr(email.sender)
        if not to_addr:
            logger.error(f"Could not parse a reply address from sender: {email.sender!r}")
            return

        msg = MIMEText(draft, "plain", "utf-8")
        msg["Subject"] = f"Re: {email.subject}"
        msg["From"] = user
        msg["To"] = to_addr
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        drafts_mailbox = self._find_special_mailbox("\\Drafts") or "[Gmail]/Drafts"
        typ, _ = self.imap.append(
            drafts_mailbox,
            "(\\Draft)",
            imaplib.Time2Internaldate(time.time()),
            msg.as_bytes(),
        )
        if typ == "OK":
            logger.info(f"Gmail draft created in '{drafts_mailbox}' for: {email.subject}")
        else:
            logger.error(f"IMAP APPEND returned non-OK status for '{email.subject}': {typ}")

    def _find_special_mailbox(self, special_use_flag):
        """
        Looks up a mailbox by its special-use flag (e.g. \\Drafts, \\Trash), which
        works across locales instead of hardcoding an English folder name.
        """
        if not self.imap:
            return None
        try:
            typ, mailboxes = self.imap.list()
            if typ == "OK":
                for mb in mailboxes:
                    decoded = mb.decode("utf-8", "replace") if isinstance(mb, bytes) else mb
                    if special_use_flag in decoded:
                        parts = decoded.rsplit(' "/" ', 1)
                        if len(parts) == 2:
                            return parts[1].strip('"')
        except Exception:
            pass
        return None

    def _log_trash_locally(self, email):
        """
        Logs the trash action locally in the SQLite email.db, in addition to the
        real IMAP trash performed by trash().
        """
        logger.info(f"Trashing: {email.subject}")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trashed_emails (
                    email_uid TEXT PRIMARY KEY,
                    subject TEXT,
                    trashed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute(
                "INSERT OR REPLACE INTO trashed_emails (email_uid, subject) VALUES (?, ?)",
                (email.id, email.subject)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Database trashing error: {e}")

# --------------------------------------------------
# AI Analyzer
# --------------------------------------------------

ANALYZE_PROMPT = """You are an email triage assistant for Siraj Uddin binyasin.
Read the email below and respond with ONLY a JSON object (no markdown fences,
no extra text) with these exact keys:

- "category": one of "Careers", "Technology", "Personal", "Newsletter", "General"
- "priority": one of "High", "Medium", "Low"
- "summary": one concise sentence describing what the email is about
- "draft_reply": a short, polite reply written as Siraj Uddin binyasin, ready to send.
  If no reply is warranted (e.g. it's a pure notification/newsletter), use an empty string.
- "delete": true if this is a newsletter, marketing blast, or automated no-reply
  notification that is safe to discard; false otherwise.

From: {sender}
Subject: {subject}
Body:
{body}
"""


class AIAnalyzer:

    def __init__(self):
        self.api_key = None
        self.api_base = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        self._load_config()

    def _load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.api_key = cfg.get("ai_api_key") or None
            self.api_base = cfg.get("ai_api_base", self.api_base)
            self.model = cfg.get("ai_model", self.model)
        except Exception as e:
            logger.error(f"Could not load AI config, falling back to rules: {e}")

    def analyze(self, email):
        if self.api_key:
            try:
                return self._analyze_with_ai(email)
            except Exception:
                logger.error("AI analysis failed, falling back to rule-based analysis")
                logger.error(traceback.format_exc())
        return self._analyze_with_rules(email)

    def _analyze_with_ai(self, email):
        prompt = ANALYZE_PROMPT.format(
            sender=email.sender,
            subject=email.subject,
            body=(email.body or "")[:4000],
        )
        resp = requests.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Strip markdown code fences if the model added them anyway
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in AI response: {content!r}")
        data = json.loads(match.group(0))

        return {
            "category": data.get("category", "General"),
            "priority": data.get("priority", "Medium"),
            "summary": data.get("summary", email.subject),
            "draft_reply": data.get("draft_reply", ""),
            "delete": bool(data.get("delete", False)),
        }

    def _analyze_with_rules(self, email):
        sender = email.sender.lower()
        subject = email.subject.lower()
        body = email.body.lower()

        delete = (
            "noreply" in sender
            or "no-reply" in sender
            or "newsletter" in sender
            or "marketing" in sender
            or "alert" in subject
            or "unsubscribe" in body
        )

        category = "General"
        priority = "Medium"
        draft_reply = "Thank you for your email. I will review it and respond shortly."

        if "job" in subject or "apply" in subject or "developer" in subject or "career" in subject:
            category = "Careers"
            priority = "High"
            draft_reply = f"Thank you for contacting me regarding the '{email.subject}' opportunity. I am highly interested and would love to review the next steps. Best regards, Siraj Uddin binyasin."
        elif "google" in sender or "cloud" in sender or "ai studio" in subject:
            category = "Technology"
            priority = "Medium"
            draft_reply = "Hi Google Team, thank you for the update on AI Studio capabilities. I look forward to experimenting with this! Best, Siraj."

        return {
            "category": category,
            "priority": priority,
            "summary": email.subject,
            "draft_reply": draft_reply,
            "delete": delete
        }

# --------------------------------------------------
# Database
# --------------------------------------------------

class Database:

    def save_email(self, email, result):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    email_uid TEXT PRIMARY KEY,
                    sender TEXT,
                    subject TEXT,
                    category TEXT,
                    priority TEXT,
                    summary TEXT,
                    delete_flag INTEGER,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute(
                "INSERT OR REPLACE INTO processed_emails (email_uid, sender, subject, category, priority, summary, delete_flag) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (email.id, email.sender, email.subject, result["category"], result["priority"], result["summary"], 1 if result["delete"] else 0)
            )
            conn.commit()
            conn.close()
            logger.info(f"Saved : {email.subject} ({result['category']})")
        except Exception as e:
            logger.error(f"Database error while saving email info: {e}")

# --------------------------------------------------
# Report
# --------------------------------------------------

class Summary:

    def __init__(self):
        self.total = 0
        self.deleted = 0
        self.drafts = 0

    def print(self):
        logger.info("")
        logger.info("========== SUMMARY ==========")
        logger.info(f"Processed : {self.total}")
        logger.info(f"Drafts    : {self.drafts}")
        logger.info(f"Deleted   : {self.deleted}")
        logger.info("=============================")

# --------------------------------------------------
# Engine
# --------------------------------------------------

class EmailManager:

    def __init__(self):
        self.gmail = GmailService()
        self.ai = AIAnalyzer()
        self.db = Database()
        self.summary = Summary()

    def process(self):
        emails = self.gmail.fetch_unread()
        logger.info(f"{len(emails)} unread emails found")

        self.gmail.connect()
        try:
            for email in emails:
                self.summary.total += 1
                try:
                    result = self.ai.analyze(email)
                    self.db.save_email(email, result)

                    if AUTO_TRASH and result["delete"]:
                        self.gmail.trash(email)
                        self.summary.deleted += 1
                        continue

                    if AUTO_DRAFT:
                        self.gmail.save_draft(email, result["draft_reply"])
                    # Mark handled either way so it isn't re-processed next run.
                    self.gmail.mark_seen(email)
                    if AUTO_DRAFT:
                        self.summary.drafts += 1

                except Exception:
                    logger.error(traceback.format_exc())
        finally:
            self.gmail.close()

        if SAVE_SUMMARY:
            self.summary.print()

# --------------------------------------------------
# HEARTBEAT ENTRY
# --------------------------------------------------

def heartbeat():
    logger.info("--------------------------------")
    logger.info("AI Email Manager Started")
    logger.info(datetime.now())
    EmailManager().process()
    logger.info("Completed")
    logger.info("--------------------------------")

if __name__ == "__main__":
    heartbeat()
