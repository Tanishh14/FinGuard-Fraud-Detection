import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

class MailService:
    @staticmethod
    def send_otp_email(email: str, otp: str, purpose: str):
        subject = f"FinGuard - {purpose} OTP"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: #2563eb; text-align: center;">FinGuard Security</h2>
                    <p>Hello,</p>
                    <p>Your One-Time Password (OTP) for <strong>{purpose}</strong> is:</p>
                    <div style="font-size: 32px; font-weight: bold; text-align: center; padding: 20px; background-color: #f3f4f6; border-radius: 8px; margin: 20px 0; color: #1e40af; letter-spacing: 5px;">
                        {otp}
                    </div>
                    <p>This code will expire in 10 minutes. If you did not request this, please ignore this email.</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        This is an automated message from FinGuard Fraud Detection System.
                    </p>
                </div>
            </body>
        </html>
        """

        if settings.USE_CONSOLE_MAILER:
            print("\n" + "="*50)
            print(f"DEBUG EMAIL TO: {email}")
            print(f"SUBJECT: {subject}")
            print(f"OTP: {otp}")
            print(f"PURPOSE: {purpose}")
            print("="*50 + "\n")
            return True

        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send email via SMTP: {e}")
            print("[INFO] Falling back to Console Mailer for development...")
            # Fallback to console print
            print("\n" + "="*50)
            print(f"FALLBACK CONSOLE EMAIL TO: {email}")
            print(f"SUBJECT: {subject}")
            print(f"OTP: {otp}")
            print(f"PURPOSE: {purpose}")
            print("="*50 + "\n")
            return True

    @staticmethod
    def send_transaction_alert(email: str, transaction_details: dict, is_blocked: bool = False):
        purpose = "Transaction Blocked" if is_blocked else "Transaction Approved"
        color = "#dc2626" if is_blocked else "#16a34a"
        action_text = "Appeal this block" if is_blocked else "Report as fraudulent"
        
        # In a real app, this would be a full URL to your frontend
        action_url = f"http://localhost:5173/transactions/{transaction_details['id']}/report-appeal"
        
        subject = f"FinGuard - {purpose}"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                    <h2 style="color: {color}; text-align: center;">FinGuard Transaction Alert</h2>
                    <p>Hello,</p>
                    <p>A transaction was recently <strong>{"blocked" if is_blocked else "approved"}</strong> on your account.</p>
                    
                    <div style="background-color: #f9fafb; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p><strong>Amount:</strong> {transaction_details['currency']} {transaction_details['amount']:.2f}</p>
                        <p><strong>Merchant:</strong> {transaction_details['merchant']}</p>
                        <p><strong>Time:</strong> {transaction_details['timestamp']}</p>
                        <p><strong>Status:</strong> <span style="color: {color}; font-weight: bold;">{transaction_details['status']}</span></p>
                    </div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <a href="{action_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            {action_text}
                        </a>
                    </p>
                    
                    <p style="font-size: 14px; margin-top: 30px;">If this transaction was not made by you or if you believe it was falsely blocked, please use the button above to report it to finguardadmin.</p>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        This is an automated security message from FinGuard Fraud Detection System.
                    </p>
                </div>
            </body>
        </html>
        """

        if settings.USE_CONSOLE_MAILER:
            print("\n" + "="*50)
            print(f"DEBUG EMAIL TO: {email}")
            print(f"SUBJECT: {subject}")
            print(f"DETAILS: {transaction_details}")
            print(f"ACTION URL: {action_url}")
            print("="*50 + "\n")
            return True

        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send alert email via SMTP: {e}")
            print("[INFO] Falling back to Console Mailer for development...")
            # Fallback to console print
            print("\n" + "="*50)
            print(f"FALLBACK CONSOLE EMAIL TO: {email}")
            print(f"SUBJECT: {subject}")
            print("="*50 + "\n")
            return True

mail_service = MailService()
