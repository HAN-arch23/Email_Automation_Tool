import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("DEFAULT_SENDER_EMAIL", "").strip()
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# NEW — read Gmail App Password
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").strip()

def send_email_smtp(to_address: str, subject: str, body_text: str, sender: str = None):
    sender = sender or SENDER_EMAIL
    if not sender:
        raise ValueError("No sender set in DEFAULT_SENDER_EMAIL")

    if not EMAIL_PASSWORD:
        raise ValueError("Missing EMAIL_APP_PASSWORD in environment variables")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body_text)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender, EMAIL_PASSWORD)
        smtp.send_message(msg)