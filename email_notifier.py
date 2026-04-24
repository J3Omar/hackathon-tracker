import ssl
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
            self.target_emails = [e.strip() for e in target_emails.split(",") if e.strip()]
        elif isinstance(target_emails, list):
            self.target_emails = [str(e) for e in target_emails if e]
        else:
            self.target_emails = []

    def _create_smtp_connection(self):
        """
        Create a secure SMTP connection using a verified TLS context.
        Protects against MITM attacks by validating the server certificate.
        """
        context = ssl.create_default_context()
        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(self.smtp_username, self.smtp_password)
        return server

    def format_hackathon_email(self, hackathons):
        """Format a list of hackathons into an HTML email."""
        if not hackathons:
            return "<p>لم يتم العثور على هاكاثونات جديدة اليوم.</p>"

        html = "<div dir='rtl' style='font-family: Arial, sans-serif; text-align: right;'>"
        html += (
            f"<h2 style='color: #2c3e50;'>🚀 تقرير الهاكاثونات اليومي - "
            f"{datetime.now().strftime('%d %B %Y')}</h2>"
        )
        html += f"<p style='font-size: 16px;'>تم العثور على <b>{len(hackathons)}</b> هاكاثون:</p><hr>"

        for post in hackathons:
            analysis = post.get("analysis", {})
            event_name = analysis.get("title") or "غير محدد"
            event_date = analysis.get("date") or "غير محدد"
            event_time = analysis.get("time") or "غير محدد"
            location = analysis.get("location") or "غير محدد"
            deadline = analysis.get("registration_deadline") or "غير محدد"
            prizes = analysis.get("prizes") or "غير محدد"
            organizer = analysis.get("organizer") or "غير محدد"
            description = analysis.get("description") or ""
            team_size = analysis.get("team_size") or "غير محدد"
            eligibility = analysis.get("eligibility") or "غير محدد"
            online_or_onsite = analysis.get("online_or_onsite") or "غير محدد"
            confidence = analysis.get("confidence", 0)
            dist = analysis.get("distance_from_zagazig_km")

            # Sanitise URLs before embedding in HTML
            reg_link = analysis.get("registration_link") or ""
            if reg_link and not reg_link.startswith("https://") and not reg_link.startswith("http://"):
                reg_link = ""
            url = post.get("url") or "#"
            if url and not url.startswith("https://") and not url.startswith("http://"):
                url = "#"

            html += f"<h3 style='color: #e74c3c;'>{event_name}</h3>"
            if description:
                html += f"<p style='color:#555;'>{description}</p>"
            html += "<ul style='list-style-type: none; padding-right: 0;'>"
            html += f"<li><b>🏢 الجهة المنظمة:</b> {organizer}</li>"
            html += f"<li><b>📅 التاريخ:</b> {event_date}</li>"
            html += f"<li><b>⏱️ الوقت:</b> {event_time}</li>"
            html += f"<li><b>📍 المكان:</b> {location} ({online_or_onsite})</li>"
            if dist is not None:
                html += f"<li><b>📏 المسافة من الزقازيق:</b> {dist} كم</li>"
            html += f"<li><b>👥 حجم الفريق:</b> {team_size}</li>"
            html += f"<li><b>🎯 الشروط:</b> {eligibility}</li>"
            html += f"<li><b>⏰ آخر موعد للتسجيل:</b> {deadline}</li>"
            html += f"<li><b>💰 الجوائز:</b> {prizes}</li>"
            html += f"<li><b>📊 درجة الثقة:</b> {confidence * 100:.0f}%</li>"

            if reg_link:
                html += (
                    f"<li style='margin-top: 10px;'><b>🔗 "
                    f"<a href='{reg_link}' style='color: #27ae60; text-decoration: none;'>"
                    f"رابط التسجيل</a></b></li>"
                )

            if url != "#":
                html += (
                    f"<li style='margin-top: 5px;'><b>🔗 "
                    f"<a href='{url}' style='color: #3498db; text-decoration: none;'>"
                    f"رابط المنشور الأصلي</a></b></li>"
                )
            html += "</ul><hr>"

        html += "</div>"
        return html

    def send_daily_summary(self, hackathons):
        """Send a daily summary of all found hackathons via Email."""
        if not self.smtp_server or not self.smtp_username or not self.smtp_password or not self.target_emails:
            logger.warning("Email configuration missing. Skipping email notification.")
            return False

        msg = MIMEMultipart()
        msg["From"] = self.smtp_username
        msg["To"] = ", ".join(self.target_emails)
        msg["Subject"] = f"🚀 تقرير الهاكاثونات اليومي - {datetime.now().strftime('%Y-%m-%d')}"

        html_body = self.format_hackathon_email(hackathons)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            server = self._create_smtp_connection()
            server.send_message(msg)
            server.quit()
            logger.info(f"Email sent successfully to {len(self.target_emails)} recipients.")
            return True
        except ssl.SSLError as e:
            logger.error(f"SSL error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_error_notification(self, error_message):
        """Send error notification via Email."""
        if not self.smtp_server or not self.smtp_username or not self.target_emails:
            return False

        msg = MIMEMultipart()
        msg["From"] = self.smtp_username
        msg["To"] = ", ".join(self.target_emails)
        msg["Subject"] = "❌ خطأ في نظام Hackathon Tracker"

        # Escape error message to prevent XSS in HTML email
        import html as html_lib
        safe_error = html_lib.escape(str(error_message))
        html_body = (
            "<div dir='rtl' style='font-family: Arial, sans-serif; text-align: right;'>"
            "<h2 style='color: red;'>حدث خطأ أثناء فحص الهاكاثونات:</h2>"
            f"<pre dir='ltr' style='text-align: left; background: #f8f9fa; padding: 10px;'>{safe_error}</pre>"
            "</div>"
        )
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            server = self._create_smtp_connection()
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send error email: {e}")
            return False
