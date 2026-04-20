# 🚀 Hackathon Tracker

نظام تلقائي لتتبع الهاكاثونات والمسابقات البرمجية في مصر من صفحات الفيسبوك باستخدام Gemma 3 والذكاء الاصطناعي.

## 📋 المميزات

- ✅ **مراقبة تلقائية** لصفحات الفيسبوك بتخفٍ عالٍ (Stealth Mode)
- 🤖 **تحليل ذكي** باستخدام Gemma 3 عبر LM Studio
- 📱 **إشعارات فورية** عبر Telegram و البريد الإلكتروني (Email)
- 🗓️ **جدولة يومية و تعويضية** تلقائية (تعمل حتى لو كان الجهاز مغلقاً وقت الإرسال)
- 🎯 **تصفية ذكية** حسب الموقع والتاريخ
- 🛡️ **تخطي الحظر** بمحاكاة السلوك البشري ودعم الـ Proxies
- 💾 **تجنب التكرار** بحفظ المنشورات المعروضة (Persistent Sessions)

## 🛠️ المتطلبات

### البرامج الأساسية
- Python 3.8+
- LM Studio مع نموذج Gemma 3
- Google Chrome / Chromium

### الحسابات المطلوبة
1. **حساب فيسبوك احتياطي** (للتصفح الآلي)
2. **Telegram Bot** للإشعارات
3. **حساب Gmail (App Password)** لإرسال البريد الإلكتروني

## 📦 التثبيت

### 1. Clone المشروع
```bash
cd ~/projects
git clone <repository-url>
cd hackathon-tracker
```

### 2. تشغيل السكريبت التلقائي
```bash
chmod +x setup.sh
./setup.sh
```

### 3. إعداد ملف .env
افتح ملف `.env` وأضف بياناتك:

```env
# Facebook Credentials
FB_EMAIL=your_backup_account@example.com
FB_PASSWORD=your_password
FB_PROXY=http://user:pass@ip:port  # اختياري لتخطي الحظر

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789,987654321

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
TARGET_EMAILS=email1@example.com,email2@example.com

# LM Studio (افتراضياً)
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions

# الكلمات المفتاحية للبحث
SEARCH_KEYWORDS=hackathon,هاكاثون,مسابقة برمجية,competition

# صفحات فيسبوك محددة (اختياري)
TARGET_PAGES=https://www.facebook.com/GDGDelta,https://www.facebook.com/IEEEZagazig

# كلمات الموقع للتصفية
LOCATION_KEYWORDS=الزقازيق,الدقهلية,delta,mansoura,المنصورة,دمياط
```

## 🔧 الإعداد التفصيلي

### إنشاء Telegram Bot

1. افتح [@BotFather](https://t.me/botfather) على Telegram
2. أرسل `/newbot`
3. اتبع التعليمات واحصل على **Bot Token**
4. ابحث عن [@userinfobot](https://t.me/userinfobot) للحصول على **Chat ID**

### تشغيل LM Studio

1. افتح LM Studio
2. حمّل نموذج Gemma 3
3. ابدأ السيرفر المحلي (Local Server)
4. تأكد أنه شغال على `localhost:1234`

### إضافة صفحات فيسبوك مستهدفة

في ملف `.env`، أضف روابط الصفحات المطلوبة:

```env
TARGET_PAGES=https://www.facebook.com/GDGDelta,https://www.facebook.com/IEEEZagazig,https://www.facebook.com/ACMZagazig
```

## 🧪 الاختبار

### اختبار كل وحدة على حدة

```bash
# تفعيل البيئة الافتراضية
source venv/bin/activate

# اختبار Facebook Scraper
python3 fb_scraper.py

# اختبار Gemma Analyzer
python3 gemma_analyzer.py

# اختبار Telegram Notifier
python3 telegram_notifier.py
```

### تشغيل فحص كامل (Manual)
```bash
python3 main.py
```

## ⏰ الجدولة التلقائية

### الطريقة 1: استخدام Scheduler المدمج (موصى به)

```bash
# تشغيل الـ scheduler في الخلفية
nohup python3 scheduler.py > logs/scheduler.log 2>&1 &
```

للإيقاف:
```bash
pkill -f scheduler.py
```

### الطريقة 2: استخدام Cron Job (موصى بها)

تتميز هذه الطريقة بميزة **التعويض (Catch-up)**. سيحاول النظام العمل كل نصف ساعة، وإذا اكتشف أنه لم يرسل تقرير اليوم، سيرسله فوراً.

1. افتح crontab:
```bash
crontab -e
```

2. أضف السطر التالي:
```bash
*/30 * * * * cd /home/your_username/hackathon-tracker && source venv/bin/activate && python3 main.py --wait-until 22:00 >> logs/cron.log 2>&1
```

تأكد من تغيير `your_username` باسم المستخدم الخاص بك.

### الطريقة 3: استخدام Systemd Service (الأكثر احترافية)

1. إنشاء ملف service:
```bash
sudo nano /etc/systemd/system/hackathon-tracker.service
```

2. أضف المحتوى التالي:
```ini
[Unit]
Description=Hackathon Tracker Scheduler
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/hackathon-tracker
ExecStart=/home/your_username/hackathon-tracker/venv/bin/python3 scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. تفعيل وتشغيل الـ service:
```bash
sudo systemctl enable hackathon-tracker
sudo systemctl start hackathon-tracker
```

4. فحص الحالة:
```bash
sudo systemctl status hackathon-tracker
```

## 📊 كيف يعمل النظام؟

```
┌─────────────────────┐
│  LM Studio          │
│  (Gemma 3 Model)    │
│  localhost:1234     │
└──────────┬──────────┘
           │
           │ Analysis API
           │
┌──────────▼──────────┐
│  Main Script        │
│  (Orchestrator)     │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
┌────▼─────┐ ┌──▼──────────┐
│ Facebook │ │  Telegram   │
│ Scraper  │ │  Notifier   │
└──────────┘ └─────────────┘
```

### سير العمل اليومي:

1. **الساعة 10 مساءً**: النظام يبدأ تلقائياً
2. **الخطوة 1**: تسجيل الدخول إلى فيسبوك
3. **الخطوة 2**: البحث عن الكلمات المفتاحية + تصفح الصفحات المحددة
4. **الخطوة 3**: جمع المنشورات الجديدة فقط
5. **الخطوة 4**: تحليل كل منشور بواسطة Gemma 3
6. **الخطوة 5**: فلترة الهاكاثونات ذات الصلة (حسب الموقع والتاريخ)
7. **الخطوة 6**: إرسال إشعارات على Telegram
8. **الخطوة 7**: حفظ المنشورات المعروضة لتجنب التكرار

## 📁 هيكل المشروع

```
hackathon-tracker/
├── config/
│   └── config.json          # الإعدادات العامة
├── data/
│   ├── posts.json           # المنشورات المحفوظة
│   └── seen_posts.json      # المنشورات المعروضة سابقاً
├── logs/
│   ├── tracker.log          # سجل التشغيل
│   └── cron.log             # سجل الـ cron
├── venv/                    # البيئة الافتراضية
├── .env                     # البيانات الحساسة
├── .env.example             # قالب البيانات
├── requirements.txt         # المكتبات المطلوبة
├── setup.sh                 # سكريبت التثبيت
├── fb_scraper.py            # وحدة تصفح فيسبوك
├── gemma_analyzer.py        # وحدة التحليل بـ Gemma
├── telegram_notifier.py     # وحدة الإشعارات (تليجرام)
├── email_notifier.py        # وحدة الإشعارات (إيميل)
├── main.py                  # السكريبت الرئيسي
├── scheduler.py             # الجدولة التلقائية
└── README.md                # هذا الملف
```

## ⚙️ التخصيص

### تعديل معايير الفلترة

في `config/config.json`:

```json
{
  "filters": {
    "days_ahead": 60,        // فحص الهاكاثونات خلال 60 يوم القادمة
    "min_confidence": 0.6    // الحد الأدنى لثقة التحليل (60%)
  }
}
```

### تعديل إعدادات التصفح

```json
{
  "scraping": {
    "max_posts_per_page": 20,   // عدد المنشورات لكل صفحة
    "scroll_delay": 2,           // التأخير بين التمريرات (ثانية)
    "headless": true             // تشغيل بدون واجهة رسومية
  }
}
```

## 🔒 الأمان والخصوصية

- ⚠️ **لا تشارك ملف `.env` أبداً**
- ✅ استخدم حساب فيسبوك احتياطي (ليس حسابك الشخصي)
- ✅ فعّل Two-Factor Authentication على حساب Telegram
- ✅ راقب استهلاك الحساب لتجنب الـ Block من فيسبوك

## ❓ استكشاف الأخطاء

### مشكلة: فشل تسجيل الدخول إلى فيسبوك

**الحل:**
- تأكد من صحة البيانات في `.env`
- جرب تسجيل الدخول يدوياً من المتصفح أولاً
- قد يظهر CAPTCHA - غير `headless: false` للتعامل اليدوي

### مشكلة: Gemma لا يستجيب

**الحل:**
- تأكد من تشغيل LM Studio
- تحقق من عنوان الـ API: `http://localhost:1234`
- جرب إرسال طلب يدوي باستخدام `curl`

### مشكلة: لا تصل الإشعارات على Telegram

**الحل:**
- تحقق من صحة `TELEGRAM_BOT_TOKEN` و `TELEGRAM_CHAT_ID`
- أرسل رسالة للبوت أولاً قبل تشغيل النظام
- جرب: `python3 telegram_notifier.py`

## 📈 التحسينات المستقبلية

- [ ] إضافة دعم لمنصات أخرى (LinkedIn, Twitter)
- [ ] Dashboard ويب لعرض النتائج
- [ ] تصنيف تلقائي حسب المجالات
- [ ] إشعارات قبل انتهاء موعد التسجيل
- [ ] تكامل مع Google Calendar

## 📝 الترخيص

هذا المشروع مفتوح المصدر للاستخدام الشخصي والتعليمي.

## 🤝 المساهمة

نرحب بأي اقتراحات أو تحسينات!

---

**صُنع بـ ❤️ لمجتمع المطورين في مصر**
