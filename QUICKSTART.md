# 🚀 دليل البدء السريع

## خطوات التشغيل في 5 دقائق

### 1️⃣ تثبيت المتطلبات
```bash
chmod +x setup.sh
./setup.sh
```

### 2️⃣ إعداد Telegram Bot
1. افتح [@BotFather](https://t.me/botfather)
2. أرسل: `/newbot`
3. اختر اسم للبوت
4. احفظ الـ **Token**
5. ابحث عن [@userinfobot](https://t.me/userinfobot)
6. احفظ الـ **Chat ID**

### 3️⃣ تعديل ملف .env
```bash
nano .env
```

أضف:
- `FB_EMAIL` - إيميل حساب فيسبوك احتياطي
- `FB_PASSWORD` - كلمة المرور
- `TELEGRAM_BOT_TOKEN` - من BotFather
- `TELEGRAM_CHAT_ID` - من userinfobot
- `SMTP_USERNAME` و `SMTP_PASSWORD` - لإرسال الإيميلات (App Password)
- `TARGET_EMAILS` - الإيميلات التي ستستقبل الإشعارات

### 4️⃣ تشغيل LM Studio
1. افتح LM Studio
2. حمّل Gemma 3
3. ابدأ Local Server
4. تأكد أنه على `localhost:1234`

### 5️⃣ اختبار النظام
```bash
source venv/bin/activate
python3 main.py
```

### 6️⃣ تفعيل الجدولة التلقائية

**الطريقة السهلة (Cron Job):**
```bash
crontab -e
# أضف هذا السطر ليعمل النظام كل نصف ساعة (للتعويض لو كان الجهاز مغلقاً)
*/30 * * * * cd /home/your_username/hackathon-tracker && source venv/bin/activate && python3 main.py --wait-until 22:00 >> logs/cron.log 2>&1
```

**الطريقة الاحترافية (Systemd):**
```bash
# إنشاء service file
sudo nano /etc/systemd/system/hackathon-tracker.service
```

أضف:
```ini
[Unit]
Description=Hackathon Tracker
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/hackathon-tracker
ExecStart=/home/YOUR_USERNAME/hackathon-tracker/venv/bin/python3 scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

ثم:
```bash
sudo systemctl enable hackathon-tracker
sudo systemctl start hackathon-tracker
sudo systemctl status hackathon-tracker
```

## ✅ تم!

النظام الآن يعمل تلقائياً كل يوم الساعة 10 مساءً.

## 🔍 فحص السجلات
```bash
tail -f logs/tracker.log
```

## 🛑 إيقاف النظام
```bash
# إذا استخدمت nohup
pkill -f scheduler.py

# إذا استخدمت systemd
sudo systemctl stop hackathon-tracker
```

---

**مشاكل؟** اقرأ [README.md](README.md) للتفاصيل الكاملة
