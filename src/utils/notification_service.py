"""
Module: notification_service.py
Purpose: Handles sending email notifications and system alerts (macOS) 
         to the user regarding agent activities.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.config import Config
from src.core.state_manager import StateManager
import os
import json
from dotenv import load_dotenv

load_dotenv()

class NotificationService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.sender_email = os.getenv("SMTP_EMAIL")
        self.sender_password = os.getenv("SMTP_PASSWORD")
        self.state_file = StateManager.DEFAULT_STATE_PATH

    def get_recipient_email(self):
         # Read from user_state.json
         try:
             with open(self.state_file, 'r') as f:
                 data = json.load(f)
                 return data.get('user_info', {}).get('email')
         except Exception as e:
             print(f"Error reading user_state.json: {e}")
             return None

    def send_email(self, subject, body):
        recipient = self.get_recipient_email()
        if not recipient:
            print("No recipient email found in user_state.json")
            return False
            
        if not self.sender_email or not self.sender_password:
             print("Missing SMTP credentials (SMTP_EMAIL, SMTP_PASSWORD) in .env. Notification NOT sent.")
             return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient, text)
            server.quit()
            print(f"Email sent to {recipient}")
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
