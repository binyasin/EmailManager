import imaplib
import email
import os
import json

EMAIL = "support@stellarstech.com"
HOST = "mail.stellarstech.com"
PORT = 993

import sqlite3
db_path = r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\skills\smart-email\data\email.db"
db = sqlite3.connect(db_path)
row = db.execute("SELECT * FROM accounts WHERE email = ?", (EMAIL,)).fetchone()
PASSWORD = row[1]
db.close()

OUTPUT_DIR = r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\temp_attachments"
os.makedirs(OUTPUT_DIR, exist_ok=True)

mail = imaplib.IMAP4_SSL(HOST, PORT)
mail.login(EMAIL, PASSWORD)
mail.select("INBOX")

result, data = mail.uid("FETCH", "6", "(RFC822)")
if result != "OK" or not data[0]:
    print(json.dumps({"error": "Email not found"}))
    mail.logout()
    exit()

raw_email = data[0][1]
msg = email.message_from_bytes(raw_email)

result = {
    "subject": msg.get("Subject", ""),
    "from": msg.get("From", ""),
    "date": msg.get("Date", ""),
    "body": "",
    "attachments": []
}

if msg.is_multipart():
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        content_type = part.get_content_type()
        filename = part.get_filename()

        if filename:
            file_path = os.path.join(OUTPUT_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(part.get_payload(decode=True))
            result["attachments"].append({
                "filename": filename,
                "contentType": content_type,
                "savedPath": file_path
            })
        elif content_type == "text/plain" and "attachment" not in content_disposition:
            try:
                result["body"] = part.get_payload(decode=True).decode("utf-8")
            except:
                result["body"] = str(part.get_payload(decode=True))
else:
    result["body"] = msg.get_payload(decode=True).decode("utf-8")

mail.logout()
print(json.dumps(result, indent=2))
