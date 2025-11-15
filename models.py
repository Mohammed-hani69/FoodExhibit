from datetime import datetime, timedelta
from extensions import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# Partner model for sponsors/partners display on landing page
class Partner(db.Model):
    __tablename__ = 'partners'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=False)
    website_url = db.Column(db.String(255), nullable=True)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Add relationship to exhibitor (User with role='exhibitor')
    exhibitor = db.relationship('User', backref=db.backref('videos', lazy=True))

# Package model for subscription packages
class Package(db.Model):
    __tablename__ = 'packages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=True)  # English name
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    description_en = db.Column(db.Text, nullable=True)  # English description
    features = db.Column(db.Text, nullable=True)  # Store as JSON string
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

# Specialization model for exhibitors
class Specialization(db.Model):
    __tablename__ = 'specializations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

# User model with roles for food exhibition platform
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    profile_image_url = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), default='user')  # user, exhibitor, admin
    phone = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=False)  # Added country field
    company_name = db.Column(db.String(100), nullable=True)  # For exhibitors
    hall = db.Column(db.String(20), nullable=True)  # For exhibitors: hall1, hall2, hall3
    company_description = db.Column(db.Text, nullable=True)  # For exhibitors
    specialization_id = db.Column(db.Integer, db.ForeignKey('specializations.id'), nullable=True)
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id'), nullable=True)  # Made nullable, will be validated in registration
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Exhibitor additional fields
    description = db.Column(db.Text, nullable=True)  # وصف الشركة - Company description
    logo_url = db.Column(db.String(255), nullable=True)  # رابط اللوجو - Logo URL
    banner_url = db.Column(db.String(255), nullable=True)  # رابط البنر - Banner URL
    video_url = db.Column(db.String(255), nullable=True)  # رابط الفيديو - Video URL
    gallery_hall = db.Column(db.String(50), nullable=True)  # القاعة (hall1, hall2, hall3) - Gallery hall assignment
    position_x = db.Column(db.Float, default=0.0, nullable=True)  # الموضع X ثلاثي الأبعاد - 3D position X
    position_y = db.Column(db.Float, default=0.0, nullable=True)  # الموضع Y ثلاثي الأبعاد - 3D position Y
    position_z = db.Column(db.Float, default=0.0, nullable=True)  # الموضع Z ثلاثي الأبعاد - 3D position Z
    ranking = db.Column(db.Integer, default=0, nullable=True)  # الترتيب في المعرض - Ranking in exhibition
    website = db.Column(db.String(255), nullable=True)  # موقع الويب - Website URL
    contact_email = db.Column(db.String(120), nullable=True)  # البريد الإلكتروني للاتصال - Contact email
    contact_phone = db.Column(db.String(20), nullable=True)  # رقم الهاتف للاتصال - Contact phone
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    specialization = db.relationship('Specialization', backref='users')
    package = db.relationship('Package', backref='users')
    orders = db.relationship('Order', backref='user')
    visits = db.relationship('Visit', backref='user')

# Available Slots for appointments
class AvailableSlot(db.Model):
    __tablename__ = 'available_slot'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    exhibitor = db.relationship('User', backref='available_slots')

# Appointment model for meetings between users and exhibitors
class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('available_slot.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    exhibitor = db.relationship('User', foreign_keys=[exhibitor_id], backref='exhibitor_appointments')
    user = db.relationship('User', foreign_keys=[user_id], backref='user_appointments')
    slot = db.relationship('AvailableSlot', backref='appointments')

# Chat Message model
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)  # Standardized field name for message content
    timestamp = db.Column(db.DateTime, default=datetime.now)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    
    @property
    def chat_room(self):
        """Generate consistent chat room identifier from sender and receiver IDs"""
        return f"chat_{min(self.sender_id, self.receiver_id)}_{max(self.sender_id, self.receiver_id)}"

# Order model for tracking sales
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship
    package = db.relationship('Package', backref='orders')

# Visit model for tracking visitor statistics
class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Visit(db.Model):
    __tablename__ = 'visits'
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(50), nullable=False)  # Anonymous ID for tracking unique visitors
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=0)  # Duration in seconds
    page_views = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Optional link to user

# Model for Exhibitor's availability schedule
class AvailabilitySchedule(db.Model):
    __tablename__ = 'availability_schedules'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    session_duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def get_available_slots(self, date):
        """Returns available time slots for the given date"""
        if date.weekday() != self.day_of_week:
            return []
        
        slots = []
        current_time = self.start_time
        while current_time <= self.end_time:
            current_datetime = datetime.combine(date, current_time)
            slot_end_datetime = current_datetime + timedelta(minutes=self.session_duration)
            slot_end = slot_end_datetime.time()
            if slot_end <= self.end_time:
                slots.append({
                    'start': current_time,
                    'end': slot_end
                })
            current_time = slot_end
        return slots

# Banner model for homepage sliders with multilingual support
class Banner(db.Model):
    __tablename__ = 'banners'
    id = db.Column(db.Integer, primary_key=True)
    # Default (Arabic) content
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # English content
    title_en = db.Column(db.String(100), nullable=True)
    description_en = db.Column(db.Text, nullable=True)
    # French content
    title_fr = db.Column(db.String(100), nullable=True)
    description_fr = db.Column(db.Text, nullable=True)
    # Common fields
    image_path = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    order = db.Column(db.Integer, default=0)  # For controlling banner order
    is_active = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(2), default='ar')  # ar, en, fr
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def get_title(self, lang='ar'):
        if lang == 'en' and self.title_en:
            return self.title_en
        elif lang == 'fr' and self.title_fr:
            return self.title_fr
        return self.title

    def get_description(self, lang='ar'):
        if lang == 'en' and self.description_en:
            return self.description_en
        elif lang == 'fr' and self.description_fr:
            return self.description_fr
        return self.description



# Exhibitor model

# Product model
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    currency = db.Column(db.String(10), default='USD')
    image_url = db.Column(db.String)
    category = db.Column(db.String(100))
    is_featured = db.Column(db.Boolean, default=False)  # Featured in gallery/homepage
    is_homepage_featured = db.Column(db.Boolean, default=False)  # Featured on homepage
    view_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship to exhibitor (User with role='exhibitor')
    exhibitor = db.relationship('User', backref=db.backref('products', lazy=True))

# Favorite Exhibitors
class FavoriteExhibitor(db.Model):
    __tablename__ = 'favorite_exhibitors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (UniqueConstraint('user_id', 'exhibitor_id', name='uq_user_exhibitor'),)

# Favorite Products
class FavoriteProduct(db.Model):
    __tablename__ = 'favorite_products'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    product = db.relationship('Product', backref='favorites')
    
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='uq_user_product'),)

# Analytics for exhibitors
class ExhibitorAnalytics(db.Model):
    __tablename__ = 'exhibitor_analytics'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Visitor
    action_type = db.Column(db.String(50))  # visit, favorite, appointment, chat
    page_visited = db.Column(db.String(100))  # profile, product, gallery
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    session_duration = db.Column(db.Integer, default=0)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    exhibitor = db.relationship('User', foreign_keys=[exhibitor_id], backref='exhibitor_analytics')
    visitor = db.relationship('User', foreign_keys=[user_id], backref='analytics_actions')
    product = db.relationship('Product', backref='analytics')

# Booking model for appointments
class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('availability_schedules.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='bookings_made')
    exhibitor = db.relationship('User', foreign_keys=[exhibitor_id], backref='bookings_received')
    schedule = db.relationship('AvailabilitySchedule', backref='bookings')

# Exhibitor Banners
class ExhibitorBanner(db.Model):
    __tablename__ = 'exhibitor_banners'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship
    exhibitor = db.relationship('User', backref=db.backref('banners', lazy=True))

# Gallery Advertisements
class GalleryAd(db.Model):
    __tablename__ = 'gallery_ads'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String, nullable=False)
    link_url = db.Column(db.String)
    position = db.Column(db.String(20))  # left, right, back
    hall = db.Column(db.String(20), default='hall1')
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)