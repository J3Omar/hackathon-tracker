#!/usr/bin/env python3
"""
Telegram Notifier Module
Sends formatted notifications about hackathons via Telegram
"""

import os
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        # Handle single ID or comma-separated list of IDs
        if isinstance(chat_id, str):
            self.chat_ids = [cid.strip() for cid in chat_id.split(',')]
        elif isinstance(chat_id, list):
            self.chat_ids = [str(cid) for cid in chat_id]
        else:
            self.chat_ids = [str(chat_id)]
    
    def send_message(self, text, parse_mode='Markdown'):
        """Send a message to Telegram"""
        overall_success = True
        for cid in self.chat_ids:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                payload = {
                    "chat_id": cid,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": False
                }
                response = requests.post(url, json=payload)
                response.raise_for_status()
                logger.info(f"Message sent successfully to {cid}")
            except Exception as e:
                logger.error(f"Failed to send message to {cid}: {e}")
                overall_success = False
        return overall_success
    
    def format_hackathon_message(self, post):
        """Format a hackathon post into a nice Telegram message"""
        analysis = post.get('analysis', {})
        
        # Build the message
        message_parts = []
        
        # Header with emoji
        message_parts.append("🚀 *هاكاثون جديد!*\n")
        
        # Event name
        event_name = analysis.get('event_name', 'غير محدد')
        message_parts.append(f"*{event_name}*\n")
        
        # Event details
        event_date = analysis.get('event_date', 'غير محدد')
        if event_date and event_date != 'null':
            try:
                date_obj = datetime.strptime(event_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d %B %Y')
                message_parts.append(f"📅 *التاريخ:* {formatted_date}")
            except:
                message_parts.append(f"📅 *التاريخ:* {event_date}")
        
        location = analysis.get('location', 'غير محدد')
        if location and location != 'null':
            message_parts.append(f"📍 *المكان:* {location}")
        
        deadline = analysis.get('deadline', 'غير محدد')
        if deadline and deadline != 'null':
            try:
                deadline_obj = datetime.strptime(deadline, '%Y-%m-%d')
                formatted_deadline = deadline_obj.strftime('%d %B %Y')
                message_parts.append(f"⏰ *آخر موعد:* {formatted_deadline}")
            except:
                message_parts.append(f"⏰ *آخر موعد:* {deadline}")
        
        prizes = analysis.get('prizes')
        if prizes and prizes != 'null':
            message_parts.append(f"💰 *الجوائز:* {prizes}")
        
        requirements = analysis.get('requirements')
        if requirements and requirements != 'null':
            message_parts.append(f"📋 *المتطلبات:* {requirements}")
        
        # Confidence score
        confidence = analysis.get('confidence', 0)
        message_parts.append(f"\n📊 *درجة الثقة:* {confidence*100:.0f}%")
        
        # Post link
        post_url = post.get('url', '')
        if post_url:
            message_parts.append(f"\n🔗 [رابط المنشور]({post_url})")
        
        # Footer
        message_parts.append("\n━━━━━━━━━━━━━━━━")
        
        return "\n".join(message_parts)
    
    def send_daily_summary(self, hackathons):
        """Send a daily summary of all found hackathons"""
        if not hackathons:
            summary = "📭 *تقرير يومي*\n\nلم يتم العثور على هاكاثونات جديدة اليوم."
            return self.send_message(summary)
        
        # Header
        today = datetime.now().strftime('%d %B %Y')
        summary = f"📊 *تقرير يومي - {today}*\n\n"
        summary += f"تم العثور على *{len(hackathons)}* هاكاثون:\n\n"
        
        # Send summary header
        self.send_message(summary)
        
        # Send each hackathon as a separate message
        for i, post in enumerate(hackathons, 1):
            message = self.format_hackathon_message(post)
            self.send_message(message)
            
            # Small delay between messages
            import time
            time.sleep(1)
        
        # Footer
        footer = f"\n✅ تم إرسال {len(hackathons)} إشعار بنجاح!"
        self.send_message(footer)
        
        return True
    
    def send_error_notification(self, error_message):
        """Send error notification"""
        message = f"❌ *خطأ في النظام*\n\n{error_message}"
        return self.send_message(message)
    
    def test_connection(self):
        """Test if bot can send messages"""
        try:
            test_message = "✅ الاتصال بالبوت ناجح!\n\nالنظام جاهز للعمل 🚀"
            return self.send_message(test_message)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


def test_notifier():
    """Test the notifier"""
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return
    
    notifier = TelegramNotifier(bot_token, chat_id)
    
    # Test connection
    if notifier.test_connection():
        print("✅ Connection successful!")
        
        # Test hackathon message
        test_post = {
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
        
        notifier.send_message(notifier.format_hackathon_message(test_post))
    else:
        print("❌ Connection failed!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_notifier()
