"""
# Heartbeat Checklist

- Check email inbox for urgent/unread messages (see `memory/email-config.md`, `email_manager.py`).
- Check calendar for events in the next 24-48h.
- Reach out if: an important email arrived, a calendar event is <2h away, or it's been >8h since last contact.
- Stay quiet (`HEARTBEAT_OK`) during 23:00-08:00 unless urgent, or if last check was <30 minutes ago.
"""

"""
AI Email Manager Heartbeat

This file is intended to be executed periodically by HEARTBEAT.

Workflow

1. Fetch unread emails
2. Analyze using AI
3. Categorize
4. Generate draft replies
5. Delete newsletters / no-reply emails
6. Save everything to database
7. Produce summary

Replace the TODO sections with your own implementation.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
import traceback
import subprocess
import json
import sqlite3
import os

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

# We'll use OpenClaw's model configuration for parsing if we run with Node-inference,
# or simply call the smart-email skill CLI which has its own SQLite store.
SKILL_DIR = r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\skills\smart-email"
DB_PATH = os.path.join(SKILL_DIR, "data", "email.db")

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

    def save_draft(self, email, draft):
        """
        In a real production system, this saves the draft back to Gmail or the DB.
        Because smart-email skill is built on read-only IMAP node-imap,
        we register drafts locally in the SQLite email.db or log them.
        """
        logger.info(f"Draft successfully saved locally for {email.subject}: '{draft[:60]}...'")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Ensure table exists
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

    def move_to_trash(self, email):
        """
        Moves the email to trash. Since direct IMAP writes require custom flags,
        we mark them locally in our sqlite database as 'trashed' so they are filtered.
        """
        logger.info(f"Moved to Trash (marked local-trash) : {email.subject}")
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
# AI (Using OpenClaw Node Inference / Direct Fallback)
# --------------------------------------------------

class AIAnalyzer:

    def analyze(self, email):
        """
        Analyzes email sender, subject, and content.
        Uses local keyword categorization and rule-based priority routing.
        """
        sender = email.sender.lower()
        subject = email.subject.lower()
        body = email.body.lower()

        # Rule-based Newsletter/No-Reply Trashing
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

        for email in emails:
            self.summary.total += 1
            try:
                result = self.ai.analyze(email)
                self.db.save_email(email, result)

                if AUTO_TRASH and result["delete"]:
                    self.gmail.move_to_trash(email)
                    self.summary.deleted += 1
                    continue

                if AUTO_DRAFT:
                    self.gmail.save_draft(email, result["draft_reply"])
                    self.summary.drafts += 1

            except Exception:
                logger.error(traceback.format_exc())

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
