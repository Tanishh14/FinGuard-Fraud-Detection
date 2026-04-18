import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add backend to path to import app
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.config import settings

def test_smtp():
    print(f"SMTP_HOST: {settings.SMTP_HOST}")
    print(f"SMTP_PORT: {settings.SMTP_PORT}")
    print(f"SMTP_USER: {settings.SMTP_USER}")
    
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_FROM_EMAIL
    msg['To'] = settings.SMTP_USER
    msg['Subject'] = "Test SSL/TLS"
    msg.attach(MIMEText("Testing different connection methods", 'plain'))

    print("\n--- Testing TLS (Port 587) ---")
    try:
        with smtplib.SMTP(settings.SMTP_HOST, 587) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            print("TLS Login Successful")
            server.send_message(msg)
            print("TLS Send Successful")
    except Exception as e:
        print(f"TLS Failed: {e}")

    print("\n--- Testing SSL (Port 465) ---")
    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, 465) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            print("SSL Login Successful")
            server.send_message(msg)
            print("SSL Send Successful")
    except Exception as e:
        print(f"SSL Failed: {e}")

if __name__ == "__main__":
    test_smtp()
