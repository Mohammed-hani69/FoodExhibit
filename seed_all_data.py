from main import create_app
from extensions import db
from models import User, Product, Package, Specialization
from werkzeug.security import generate_password_hash
from datetime import datetime
import random

def seed_all_data():
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        db.session.query(Product).delete()
        db.session.query(User).delete()
        db.session.query(Package).delete()
        db.session.query(Specialization).delete()
        db.session.commit()

        # Create packages
        packages = [
            Package(
                name="باقة أساسية",
                name_en="Basic Package",
                price=1000,
                description="باقة أساسية للعارضين",
                description_en="Basic package for exhibitors",
                features="[\"عرض المنتجات\", \"الدردشة مع الزوار\"]"
            ),
            Package(
                name="باقة متقدمة",
                name_en="Premium Package",
                price=2000,
                description="باقة متقدمة مع مميزات إضافية",
                description_en="Premium package with additional features",
                features="[\"عرض المنتجات\", \"الدردشة مع الزوار\", \"إحصائيات متقدمة\"]"
            )
        ]
        db.session.add_all(packages)
        db.session.commit()

        # Create specializations
        specializations = [
            Specialization(name="مواد غذائية", description="منتجات غذائية متنوعة"),
            Specialization(name="مشروبات", description="مشروبات وعصائر"),
            Specialization(name="معدات مطابخ", description="معدات وأدوات المطابخ")
        ]
        db.session.add_all(specializations)
        db.session.commit()

        # Create admin user
        admin = User(
            email="admin@foodexhibit.com",
            password=generate_password_hash("admin123"),
            first_name="مدير",
            last_name="النظام",
            role="admin",
            country="مصر",
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()

        # Create exhibitors
        exhibitor_companies = [
            "شركة الغذاء المتميز",
            "مصنع المشروبات الطبيعية",
            "شركة المعدات الحديثة"
        ]
        
        exhibitors = []
        for i, company in enumerate(exhibitor_companies):
            exhibitor = User(
                email=f"exhibitor{i+1}@example.com",
                password=generate_password_hash(f"exhibitor{i+1}"),
                first_name=f"عارض",
                last_name=f"{i+1}",
                role="exhibitor",
                company_name=company,
                company_description=f"وصف شركة {company}",
                country="مصر",
                phone=f"+20100000000{i}",
                specialization_id=specializations[i].id,
                package_id=packages[random.randint(0, 1)].id,
                is_active=True
            )
            exhibitors.append(exhibitor)
        
        db.session.add_all(exhibitors)
        db.session.commit()

        # Create products for exhibitors
        products = []
        product_images = [
            "static/images/products/568b3a94-13d6-4b7f-8668-7a44102af8a5.png",
            "static/images/products/Gemini_Generated_Image_ifog0sifog0sifog_1.png",
            "static/images/products/Gemini_Generated_Image_ls5452ls5452ls54.png"
        ]
        
        product_names = {
            0: ["عصير طبيعي", "مشروب الطاقة", "عصير فواكه"],
            1: ["شوكولاتة داكنة", "حلوى بالفواكه", "بسكويت محشو"],
            2: ["معدات تقطيع", "فرن صناعي", "خلاط صناعي"]
        }
        
        product_descriptions = {
            0: ["عصير طبيعي 100٪ من الفواكه الطازجة", "مشروب طاقة طبيعي من الأعشاب", "مزيج من الفواكه الطازجة"],
            1: ["شوكولاتة داكنة فاخرة 70٪ كاكاو", "حلوى طبيعية محشوة بالفواكه", "بسكويت محشو بالشوكولاتة"],
            2: ["معدات تقطيع احترافية للمطاعم", "فرن صناعي متعدد الاستخدامات", "خلاط صناعي قوي للمطاعم"]
        }

        for i, exhibitor in enumerate(exhibitors):
            for j in range(3):  # 3 products per exhibitor
                product = Product(
                    name=product_names[i][j],
                    description=product_descriptions[i][j],
                    price=random.randint(100, 1000),
                    exhibitor_id=exhibitor.id,
                    is_active=True,
                    is_featured=random.choice([True, False]),
                    category=exhibitor.specialization.name,
                    currency="EGP",
                    image_url=product_images[j]  # Use real product images
                )
                products.append(product)
        
        db.session.add_all(products)
        db.session.commit()

        # Create regular visitors
        visitors = []
        for i in range(5):
            visitor = User(
                email=f"visitor{i+1}@example.com",
                password=generate_password_hash(f"visitor{i+1}"),
                first_name=f"زائر",
                last_name=f"{i+1}",
                role="user",
                country="مصر",
                phone=f"+20111000000{i}",
                is_active=True
            )
            visitors.append(visitor)
        
        db.session.add_all(visitors)
        db.session.commit()

        print("تم إضافة جميع البيانات بنجاح!")
        print("بيانات تسجيل دخول المدير:")
        print("البريد الإلكتروني: admin@foodexhibit.com")
        print("كلمة المرور: admin123")
        print("\nبيانات العارضين:")
        for i, exhibitor in enumerate(exhibitors):
            print(f"العارض {i+1}:")
            print(f"البريد الإلكتروني: exhibitor{i+1}@example.com")
            print(f"كلمة المرور: exhibitor{i+1}")
        print("\nبيانات الزوار:")
        for i in range(5):
            print(f"الزائر {i+1}:")
            print(f"البريد الإلكتروني: visitor{i+1}@example.com")
            print(f"كلمة المرور: visitor{i+1}")

if __name__ == "__main__":
    seed_all_data()