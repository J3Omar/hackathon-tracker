import os
from dotenv import load_dotenv
from email_notifier import EmailNotifier
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT', '587')
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')
target_emails = os.getenv('TARGET_EMAILS')

notifier = EmailNotifier(smtp_server, smtp_port, smtp_username, smtp_password, target_emails)

test_hackathons = [
    {
        'url': 'https://facebook.com/test',
        'analysis': {
            'event_name': 'GDG Delta Hackathon 2025',
            'event_date': '2025-05-15',
            'location': 'جامعة الزقازيق',
            'deadline': '2025-05-01',
            'prizes': '10,000 جنيه',
            'requirements': 'فرق من 3-5 أفراد',
            'confidence': 0.95
        }
    }
]

print("Testing Email Notifier...")
success = notifier.send_daily_summary(test_hackathons)
if success:
    print("✅ Test Email sent successfully to:", target_emails)
else:
    print("❌ Failed to send Test Email.")
