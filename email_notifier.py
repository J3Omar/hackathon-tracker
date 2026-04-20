import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self, smtp_server, smtp_port, smtp_username, smtp_password, target_emails):
        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port) if smtp_port else 587
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        
        if isinstance(target_emails, str):
            self.target_emails = [e.strip() for e in target_emails.split(',') if e.strip()]
        elif isinstance(target_emails, list):
            self.target_emails = [str(e) for e in target_emails if e]
        else:
            self.target_emails = []

    def format_hackathon_email(self, hackathons):
        """Format a list of hackathons into an HTML email"""
        if not hackathons:
            return "<p>لم يتم العثور على هاكاثونات جديدة اليوم.</p>"
            
        html = f"<div dir='rtl' style='font-family: Arial, sans-serif; text-align: right;'>"
        html += f"<h2 style='color: #2c3e50;'>🚀 تقرير الهاكاثونات اليومي - {datetime.now().strftime('%d %B %Y')}</h2>"
        html += f"<p style='font-size: 16px;'>تم العثور على <b>{len(hackathons)}</b> هاكاثون:</p><hr>"
        
        for post in hackathons:
            analysis = post.get('analysis', {})
            event_name = analysis.get('event_name', 'غير محدد')
            event_date = analysis.get('event_date', 'غير محدد')
            location = analysis.get('location', 'غير محدد')
            deadline = analysis.get('deadline', 'غير محدد')
            prizes = analysis.get('prizes', 'غير محدد')
            requirements = analysis.get('requirements', 'غير محدد')
            confidence = analysis.get('confidence', 0)
            url = post.get('url', '#')
            
            html += f"<h3 style='color: #e74c3c;'>{event_name}</h3>"
            html += "<ul style='list-style-type: none; padding-right: 0;'>"
            html += f"<li><b>📅 التاريخ:</b> {event_date}</li>"
            html += f"<li><b>📍 المكان:</b> {location}</li>"
            html += f"<li><b>⏰ آخر موعد:</b> {deadline}</li>"
            html += f"<li><b>💰 الجوائز:</b> {prizes}</li>"
            html += f"<li><b>📋 المتطلبات:</b> {requirements}</li>"
            html += f"<li><b>📊 درجة الثقة:</b> {confidence*100:.0f}%</li>"
            html += f"<li style='margin-top: 10px;'><b>🔗 <a href='{url}' style='color: #3498db; text-decoration: none;'>رابط المنشور الأصلي</a></b></li>"
            html += "</ul><hr>"
            
        html += "</div>"
        return html

    def send_daily_summary(self, hackathons):
        """Send a daily summary of all found hackathons via Email"""
        if not self.smtp_server or not self.smtp_username or not self.smtp_password or not self.target_emails:
            logger.warning("Email configuration missing. Skipping email notification.")
            return False
            
        msg = MIMEMultipart()
        msg['From'] = self.smtp_username
        msg['To'] = ", ".join(self.target_emails)
        msg['Subject'] = f"🚀 تقرير الهاكاثونات اليومي - {datetime.now().strftime('%Y-%m-%d')}"
        
        html_body = self.format_hackathon_email(hackathons)
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            logger.info(f"Email sent successfully to {len(self.target_emails)} recipients.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
            
    def send_error_notification(self, error_message):
        """Send error notification via Email"""
        if not self.smtp_server or not self.smtp_username or not self.target_emails:
            return False
            
        msg = MIMEMultipart()
        msg['From'] = self.smtp_username
        msg['To'] = ", ".join(self.target_emails)
        msg['Subject'] = "❌ خطأ في نظام Hackathon Tracker"
        
        html_body = f"<div dir='rtl' style='font-family: Arial, sans-serif; text-align: right;'><h2 style='color: red;'>حدث خطأ أثناء فحص الهاكاثونات:</h2><pre dir='ltr' style='text-align: left; background: #f8f9fa; padding: 10px;'>{error_message}</pre></div>"
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send error email: {e}")
            return False
