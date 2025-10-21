from app import app, db
from models import User, Package, Specialization, Exhibitor, Product, Banner, ChatMessage, Visit
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(email='admin@foodexhibit.com').first()
        if not admin:
            # Create default admin user
            admin = User(
                email='admin@foodexhibit.com',
                password=generate_password_hash('admin123'),
                first_name='Admin',
                last_name='User',
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            
            # Create default specialization
            spec = Specialization(
                name='General Food',
                description='General food products'
            )
            db.session.add(spec)
            
            # Create default package
            package = Package(
                name='Basic Package',
                name_en='Basic Package',
                price=0.0,
                description='Basic exhibition package',
                description_en='Basic exhibition package',
                features='[]',
                is_active=True
            )
            db.session.add(package)
            
            try:
                db.session.commit()
                print("Database initialized successfully!")
            except Exception as e:
                db.session.rollback()
                print(f"Error initializing database: {str(e)}")

if __name__ == '__main__':
    init_db()