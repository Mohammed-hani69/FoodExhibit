from datetime import datetime
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# User model with roles for food exhibition platform
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    role = db.Column(db.String, default='user')  # user, exhibitor, admin
    phone = db.Column(db.String, nullable=True)
    company_name = db.Column(db.String, nullable=True)  # For exhibitors
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    favorites_exhibitors = db.relationship('FavoriteExhibitor', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites_products = db.relationship('FavoriteProduct', backref='user', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='user', lazy=True)
    chat_messages = db.relationship('ChatMessage', foreign_keys='ChatMessage.user_id', backref='user', lazy=True)

# OAuth model for Replit Auth
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key', 
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

# Exhibitor model
class Exhibitor(db.Model):
    __tablename__ = 'exhibitors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String)
    banner_url = db.Column(db.String)
    gallery_hall = db.Column(db.String, default='hall1')  # hall1, hall2, etc.
    position_x = db.Column(db.Float, default=0.0)  # 3D position
    position_y = db.Column(db.Float, default=0.0)
    position_z = db.Column(db.Float, default=0.0)
    ranking = db.Column(db.Integer, default=1)  # For positioning in gallery
    website = db.Column(db.String)
    contact_email = db.Column(db.String)
    contact_phone = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='exhibitor_profile')
    products = db.relationship('Product', backref='exhibitor', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='exhibitor', lazy=True)
    analytics = db.relationship('ExhibitorAnalytics', backref='exhibitor', lazy=True, cascade='all, delete-orphan')
    available_slots = db.relationship('AvailableSlot', backref='exhibitor', lazy=True, cascade='all, delete-orphan')

# Product model
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('exhibitors.id'), nullable=False)
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

# Favorite Exhibitors
class FavoriteExhibitor(db.Model):
    __tablename__ = 'favorite_exhibitors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('exhibitors.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (UniqueConstraint('user_id', 'exhibitor_id', name='uq_user_exhibitor'),)

# Favorite Products
class FavoriteProduct(db.Model):
    __tablename__ = 'favorite_products'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    product = db.relationship('Product', backref='favorites')
    
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='uq_user_product'),)

# Chat Messages
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('exhibitors.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_from_exhibitor = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    exhibitor = db.relationship('Exhibitor', backref='chat_messages')

# Available Slots for appointments
class AvailableSlot(db.Model):
    __tablename__ = 'available_slots'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('exhibitors.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

# Appointments
class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('exhibitors.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('available_slots.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    slot = db.relationship('AvailableSlot', backref='appointments')

# Analytics for exhibitors
class ExhibitorAnalytics(db.Model):
    __tablename__ = 'exhibitor_analytics'
    id = db.Column(db.Integer, primary_key=True)
    exhibitor_id = db.Column(db.Integer, db.ForeignKey('exhibitors.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)  # Visitor
    action_type = db.Column(db.String(50))  # visit, favorite, appointment, chat
    page_visited = db.Column(db.String(100))  # profile, product, gallery
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    session_duration = db.Column(db.Integer, default=0)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    visitor = db.relationship('User', backref='analytics_actions')
    product = db.relationship('Product', backref='analytics')

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