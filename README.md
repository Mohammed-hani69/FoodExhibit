# Food Exhibit Platform | منصة معرض الأغذية

## 🌐 About | نبذة عن المشروع

Food Exhibit is a virtual exhibition platform that enables food industry exhibitors to showcase their products and connect with visitors digitally. The platform facilitates virtual meetings, product displays, and business networking in the food industry sector.

منصة معرض الأغذية هي منصة معارض افتراضية تمكن العارضين في صناعة الأغذية من عرض منتجاتهم والتواصل مع الزوار رقمياً. تسهل المنصة الاجتماعات الافتراضية وعرض المنتجات والتواصل التجاري في قطاع صناعة الأغذية.

## 🚀 Features | المميزات

- Virtual Exhibition Halls | قاعات المعرض الافتراضية
- Exhibitor Profiles | ملفات العارضين
- Product Showcases | عرض المنتجات
- Appointment Booking | حجز المواعيد
- Live Chat | المحادثات المباشرة
- Admin Dashboard | لوحة تحكم المشرف
- Visit Statistics | إحصائيات الزيارات

## 💻 Technology Stack | التقنيات المستخدمة

- Python (Flask)
- SQLite
- HTML/CSS/JavaScript
- Socket.IO
- Flask-SQLAlchemy
- Flask-Migrate

## 🛠 Installation | التثبيت

1. Clone the repository | نسخ المستودع
   ```bash
   git clone git@github.com:Mohammed-hani69/FoodExhibit.git
   cd FoodExhibit
   ```

2. Create virtual environment | إنشاء البيئة الافتراضية
   ```bash
   python -m venv venv
   ```

3. Activate virtual environment | تفعيل البيئة الافتراضية
   - Windows:
     ```powershell
     .\venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies | تثبيت المتطلبات
   ```bash
   pip install -r requirements.txt
   ```

5. Initialize the database | تهيئة قاعدة البيانات
   ```bash
   flask db upgrade
   python seed_all_data.py
   ```

6. Run the application | تشغيل التطبيق
   ```bash
   python main.py
   ```

## 📝 Git Commands | أوامر جيت

### First Time Setup | الإعداد لأول مرة
```bash
git init
git remote add origin git@github.com:Mohammed-hani69/FoodExhibit.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

### Regular Updates | التحديثات العادية
```bash
# Get latest changes | جلب آخر التحديثات
git pull origin main

# Add changes | إضافة التغييرات
git add .

# Commit changes | تأكيد التغييرات
git commit -m "v 1.0.4"

# Push changes | رفع التغييرات
git push origin main
```

## 📁 Project Structure | هيكل المشروع

```
FoodExhibit/
├── app.py                 # Main application configuration
├── main.py               # Application entry point
├── models.py             # Database models
├── routes.py             # Main routes
├── admin_routes.py       # Admin panel routes
├── exhibitor_routes.py   # Exhibitor routes
├── auth.py               # Authentication
├── extensions.py         # Flask extensions
├── socket_handlers.py    # WebSocket handlers
├── static/              # Static files (CSS, JS, images)
├── templates/           # HTML templates
└── migrations/          # Database migrations
```

## 👥 Contributing | المساهمة

1. Fork the repository | انسخ المستودع
2. Create your feature branch | أنشئ فرع الميزة الخاصة بك
   ```bash
   git checkout -b feature/YourFeature
   ```
3. Commit your changes | أكد تغييراتك
   ```bash
   git commit -m 'Add some feature'
   ```
4. Push to the branch | ادفع إلى الفرع
   ```bash
   git push origin feature/YourFeature
   ```
5. Create a Pull Request | أنشئ طلب سحب

## 📄 License | الترخيص

This is proprietary software. All rights reserved. | هذا برنامج مملوك. جميع الحقوق محفوظة.
See [LICENSE](LICENSE) file for details. | انظر ملف الترخيص للتفاصيل.

## 📞 Contact | التواصل

For support or inquiries, please contact [hanizezo72@gmail.com OR +201145425207]

للدعم أو الاستفسارات، يرجى التواصل مع [hanizezo72@gmail.com OR +201145425207]