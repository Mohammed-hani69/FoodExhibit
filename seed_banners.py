from main import app, db
from models import Banner

# Banner data to seed
banners = [
    # Arabic Banners
    {
        'title': 'معرض الأغذية العالمي 2025',
        'title_en': 'World Food Exhibition 2025',
        'title_fr': 'Exposition Mondiale de l\'Alimentation 2025',
        'description': 'اكتشف أحدث المنتجات والابتكارات في صناعة الأغذية',
        'description_en': 'Discover the latest products and innovations in the food industry',
        'description_fr': 'Découvrez les derniers produits et innovations de l\'industrie alimentaire',
        'image_path': '/static/images/banners/94b8645acef5852980278eb1f65dace9.png',
        'order': 1,
        'is_active': True,
        'language': 'ar'
    },
    {
        'title': 'معرض الصناعات الغذائية',
        'title_en': 'Food Industries Exhibition',
        'title_fr': 'Salon des Industries Alimentaires',
        'description': 'انضم إلى أكبر تجمع للشركات العالمية في مجال الأغذية',
        'description_en': 'Join the largest gathering of global food companies',
        'description_fr': 'Rejoignez le plus grand rassemblement d\'entreprises alimentaires mondiales',
        'image_path': '/static/images/banners/c49d2b879f33281ddab7b2622ac26fd6.png',
        'order': 2,
        'is_active': True,
        'language': 'ar'
    },
    {
        'title': 'استكشف الفرص الاستثمارية',
        'title_en': 'Explore Investment Opportunities',
        'title_fr': 'Explorez les Opportunités d\'Investissement',
        'description': 'فرص استثمارية واعدة في قطاع الصناعات الغذائية',
        'description_en': 'Promising investment opportunities in the food industry sector',
        'description_fr': 'Opportunités d\'investissement prometteuses dans le secteur alimentaire',
        'image_path': '/static/images/banners/f0ab21cde3bc84ac57a308db1514b772.png',
        'order': 3,
        'is_active': True,
        'language': 'ar'
    },
    {
        'title': 'معرض الأغذية 2025',
        'title_en': 'Food Expo 2025',
        'title_fr': 'Expo Alimentaire 2025',
        'description': 'تواصل مع أكثر من 500 عارض من مختلف أنحاء العالم',
        'description_en': 'Connect with over 500 exhibitors from around the world',
        'description_fr': 'Connectez-vous avec plus de 500 exposants du monde entier',
        'image_path': '/static/images/banners/VISIT-FOODEXPO-2022.jpg',
        'order': 4,
        'is_active': True,
        'language': 'ar'
    },
    {
        'title': 'معرض المكونات الغذائية العالمي',
        'title_en': 'World Food Ingredients Expo',
        'title_fr': 'Expo Mondiale des Ingrédients Alimentaires',
        'description': 'اكتشف أحدث التقنيات والمكونات في صناعة الأغذية',
        'description_en': 'Discover the latest technologies and ingredients in food manufacturing',
        'description_fr': 'Découvrez les dernières technologies et ingrédients dans la fabrication alimentaire',
        'image_path': '/static/images/banners/World-Food-Ingredients-Expo-2023.jpg',
        'order': 5,
        'is_active': True,
        'language': 'ar'
    }
]

def seed_banners():
    with app.app_context():
        try:
            # Clear existing banners
            Banner.query.delete()
            
            # Add banners to database
            for banner_data in banners:
                banner = Banner(**banner_data)
                db.session.add(banner)
            
            # Commit changes
            db.session.commit()
            print("Banners seeded successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding banners: {str(e)}")
            raise

if __name__ == '__main__':
    seed_banners()
