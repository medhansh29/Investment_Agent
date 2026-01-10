import sys
"""
Module: send_notification.py
Purpose: CLI util to trigger email alerts manually or via cron.
"""
import argparse
from src.utils.notification_service import NotificationService
from src.utils.email_templates import EmailTemplates
import json
import os
from src.core.state_manager import StateManager

def main():
    parser = argparse.ArgumentParser(description='Send Investment Agent Notifications')
    parser.add_argument('subject', nargs='?', help='Email Subject (if not using template)')
    parser.add_argument('body', nargs='?', help='Email Body (if not using template)')
    parser.add_argument('--template', choices=['rebalance', 'invest'], help='Use a predefined template')
    
    args = parser.parse_args()
    
    subject = args.subject
    body = args.body
    
    # Template logic
    if args.template == 'rebalance':
        subject, body = EmailTemplates.get_rebalance_content()
    elif args.template == 'invest':
        subject, body = EmailTemplates.get_invest_content()
        
    if not subject or not body:
        print("Error: Must provide either subject/body OR --template")
        parser.print_help()
        sys.exit(1)
    
    service = NotificationService()
    success = service.send_email(subject, body)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
