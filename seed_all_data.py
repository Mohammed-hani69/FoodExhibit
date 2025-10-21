from app import create_app
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
        for exhibitor in exhibitors:
            for j in range(3):  # 3 products per exhibitor
                product = Product(
                    name=f"منتج {j+1} - {exhibitor.company_name}",
                    name_en=f"Product {j+1} - {exhibitor.company_name}",
                    description=f"وصف المنتج {j+1} من {exhibitor.company_name}",
                    description_en=f"Description of product {j+1} from {exhibitor.company_name}",
                    price=random.randint(100, 1000),
                    user_id=exhibitor.id,
                    is_active=True,
                    image_path="static/images/products/product1.png"  # Default image
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