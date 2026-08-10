import os
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import json
import os.path
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER", "binyasin39@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))

def delete_email_by_subject_or_sender(target_subject=None, target_sender=None):
    if not EMAIL_PASS:
        print("[-] App password not configured.")
        return False
        
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
        
        # Search for matching emails
        search_criteria = 'ALL'
        status, messages = mail.search(None, search_criteria)
        email_ids = messages[0].split()
        
        deleted_count = 0
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Clean headers
                    def clean_header(val):
                        if not val: return ""
                        decoded = decode_header(val)
                        res_str = ""
                        for b, enc in decoded:
                            if isinstance(b, bytes):
                                res_str += b.decode(enc or "utf-8", errors="ignore")
                            else:
                                res_str += str(b)
                        return res_str
                    
                    subject = clean_header(msg.get("Subject"))
                    sender = clean_header(msg.get("From"))
                    
                    match = False
                    if target_subject and target_subject.lower() in subject.lower():
                        match = True
                    if target_sender and target_sender.lower() in sender.lower():
                        match = True
                        
                    if match:
                        # Mark the email as deleted
                        mail.store(e_id, '+FLAGS', '\\Deleted')
                        print(f"[+] Marked for deletion: ID {e_id.decode()} | From: {sender} | Subject: {subject}")
                        deleted_count += 1
                        
        # Expunge to permanently delete marked emails
        if deleted_count > 0:
            mail.expunge()
            print(f"[+] Permanently deleted {deleted_count} email(s).")
        else:
            print("[-] No matching emails found to delete.")
            
        mail.logout()
        return True
    except Exception as e:
        print(f"[-] Deletion failed: {e}")
        return False

if __name__ == "__main__":
    # Example execution - Can be configured as needed
    print("[*] Running email cleanup routine...")
    # By default, we check if any specific deletion is requested
