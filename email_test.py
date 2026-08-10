import os
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER", "binyasin39@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))

def test_imap_connection():
    if not EMAIL_PASS or EMAIL_PASS == "your_16_digit_app_password_here":
        print("[-] App password not set in .env")
        return False
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        print("[+] IMAP Connection Successful!")
        mail.logout()
        return True
    except Exception as e:
        print(f"[-] IMAP Connection Failed: {e}")
        return False

def test_smtp_connection():
    if not EMAIL_PASS or EMAIL_PASS == "your_16_digit_app_password_here":
        print("[-] App password not set in .env")
        return False
    try:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        server.login(EMAIL_USER, EMAIL_PASS)
        print("[+] SMTP Connection Successful!")
        server.quit()
        return True
    except Exception as e:
        print(f"[-] SMTP Connection Failed: {e}")
        return False

if __name__ == "__main__":
    print(f"Testing connections for {EMAIL_USER}...")
    imap_ok = test_imap_connection()
    smtp_ok = test_smtp_connection()
    if imap_ok and smtp_ok:
        print("[+] Ready to manage emails!")
    else:
        print("[-] Please generate and update your Google App Password in .env")
