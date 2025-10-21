from flask import render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import current_user, logout_user, login_required
from flask_socketio import emit, join_room, leave_room
from extensions import db, socketio
from auth import admin_required
from app import app

# Import models explicitly
from models import (
    User, Package, Specialization, Banner, 
    AvailabilitySchedule, Booking, FavoriteExhibitor,
    FavoriteProduct, ChatMessage, ExhibitorAnalytics,
    GalleryAd, Exhibitor, Product, Appointment, Video
)
import json
from datetime import datetime, timedelta
import logging
from sqlalchemy.exc import OperationalError
from functools import wraps
from werkzeug.utils import secure_filename
import os

# Configure upload folder for banners
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'images', 'banners')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def exhibitor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'exhibitor':
            flash('You must be an exhibitor to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Custom Jinja filter for JSON parsing
@app.template_filter('fromjson')
def fromjson(value):
    try:
        return json.loads(value) if value else []
    except:
        return []

# Main routes
@app.route('/')
def landing():
    """Landing page route with multilingual support"""
    # Get active banners
    banners = Banner.query.filter_by(is_active=True).order_by(Banner.order).all()
    
    # Get featured products for homepage
    featured_products = Product.query.filter_by(
        is_homepage_featured=True,
        is_active=True
    ).all()
    
    return render_template('landing.html', 
                         banners=banners,
                         featured_products=featured_products,
                         current_language=session.get('language', 'ar'))

@app.route('/product/<int:product_id>')
def product_details(product_id):
    """Product details page route"""
    product = Product.query.get_or_404(product_id)
    return render_template('product_details.html', 
                         product=product,
                         current_language=session.get('language', 'ar'))

@app.route('/chat/<int:exhibitor_id>')
@login_required
def chat_with_exhibitor(exhibitor_id):
    """Chat with exhibitor route"""
    exhibitor = Exhibitor.query.get_or_404(exhibitor_id)
    # Initialize chat room or get existing chat
    chat_room = f"chat_{min(current_user.id, exhibitor_id)}_{max(current_user.id, exhibitor_id)}"
    
    # Get previous messages
    messages = ChatMessage.query.filter_by(chat_room=chat_room).order_by(ChatMessage.timestamp).all()
    
    return render_template('chat.html',
                         exhibitor=exhibitor,
                         messages=messages,
                         chat_room=chat_room,
                         current_language=session.get('language', 'ar'))

# Availability Management Routes
@app.route('/exhibitor/schedule', methods=['GET', 'POST'])
@login_required
@exhibitor_required
def manage_schedule():
    if request.method == 'POST':
        day_of_week = int(request.form['day_of_week'])
        start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
        session_duration = int(request.form['session_duration'])
        
        schedule = AvailabilitySchedule(
            exhibitor_id=current_user.id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            session_duration=session_duration
        )
        
        db.session.add(schedule)
        try:
            db.session.commit()
            flash('Schedule added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding schedule. Please try again.', 'danger')
            
    schedules = AvailabilitySchedule.query.filter_by(
        exhibitor_id=current_user.id,
        is_active=True
    ).all()
    
    # Get upcoming bookings
    upcoming_bookings = Booking.query.filter(
        Booking.exhibitor_id == current_user.id,
        Booking.booking_date >= datetime.now().date(),
        Booking.status.in_(['pending', 'confirmed'])
    ).order_by(Booking.booking_date, Booking.start_time).all()
    
    return render_template(
        'exhibitor/schedule_management.html',
        schedules=schedules,
        upcoming_bookings=upcoming_bookings
    )

@app.route('/exhibitor/schedule/<int:schedule_id>', methods=['POST'])
@login_required
@exhibitor_required
def update_schedule(schedule_id):
    schedule = AvailabilitySchedule.query.get_or_404(schedule_id)
    if schedule.exhibitor_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('manage_schedule'))
    
    action = request.form.get('action')
    if action == 'delete':
        schedule.is_active = False
    elif action == 'update':
        schedule.start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        schedule.end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
        schedule.session_duration = int(request.form['session_duration'])
    
    try:
        db.session.commit()
        flash('Schedule updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating schedule. Please try again.', 'danger')
    
    return redirect(url_for('manage_schedule'))

@app.route('/exhibitor/bookings')
@login_required
@exhibitor_required
def exhibitor_bookings():
    status_filter = request.args.get('status', 'all')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Booking.query.filter_by(exhibitor_id=current_user.id)
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if date_from:
        query = query.filter(Booking.booking_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(Booking.booking_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    bookings = query.order_by(Booking.booking_date.desc(), Booking.start_time).all()
    return render_template('exhibitor/bookings.html', bookings=bookings)

@app.route('/exhibitor/booking/<int:booking_id>', methods=['POST'])
@login_required
@exhibitor_required
def update_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.exhibitor_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('exhibitor.bookings'))
    
    action = request.form.get('action')
    if action in ['confirm', 'cancel', 'complete']:
        booking.status = action + 'ed' if action != 'cancel' else 'cancelled'
        try:
            db.session.commit()
            flash(f'Booking {booking.status} successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating booking. Please try again.', 'danger')
    
    return redirect(url_for('exhibitor.bookings'))

# Book Appointment Route for Users
@app.route('/exhibitor/<int:exhibitor_id>/book', methods=['GET', 'POST'])
@login_required
def exhibitor_booking(exhibitor_id):
    exhibitor = User.query.get_or_404(exhibitor_id)
    if exhibitor.role != 'exhibitor':
        flash('Invalid exhibitor.', 'danger')
        return redirect(url_for('landing'))
    
    if request.method == 'POST':
        schedule_id = request.form.get('schedule_id')
        booking_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        start_time = datetime.strptime(request.form.get('time'), '%H:%M').time()
        
        schedule = AvailabilitySchedule.query.get_or_404(schedule_id)
        end_time = datetime.combine(booking_date, start_time)
        end_time = (end_time + timedelta(minutes=schedule.session_duration)).time()
        
        # Check if slot is available
        existing_booking = Booking.query.filter_by(
            exhibitor_id=exhibitor_id,
            booking_date=booking_date,
            start_time=start_time,
            status='confirmed'
        ).first()
        
        if existing_booking:
            flash('This time slot is already booked.', 'danger')
            return redirect(url_for('exhibitor.booking', exhibitor_id=exhibitor_id))
        
        booking = Booking(
            user_id=current_user.id,
            exhibitor_id=exhibitor_id,
            schedule_id=schedule_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            notes=request.form.get('notes')
        )
        
        db.session.add(booking)
        try:
            db.session.commit()
            flash('Appointment booked successfully! Waiting for exhibitor confirmation.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error booking appointment. Please try again.', 'danger')
        
    schedules = AvailabilitySchedule.query.filter_by(
        exhibitor_id=exhibitor_id,
        is_active=True
    ).all()
    
    # Get already booked slots
    booked_slots = Booking.query.filter(
        Booking.exhibitor_id == exhibitor_id,
        Booking.booking_date >= datetime.now().date(),
        Booking.status.in_(['confirmed', 'pending'])
    ).all()
    
    return render_template(
        'booking/book_appointment.html',
        exhibitor=exhibitor,
        schedules=schedules,
        booked_slots=booked_slots
    )

@app.route('/exhibitor/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_exhibitor_profile():
    """Exhibitor profile edit route"""
    if current_user.role != 'exhibitor':
        flash('هذه الصفحة مخصصة للعارضين فقط', 'error')
        return redirect(url_for('index'))
    
    # جلب بيانات العارض
    exhibitor = current_user
    
    # جلب جميع التخصصات من قاعدة البيانات
    specializations = Specialization.query.order_by(Specialization.name).all()
    
    if request.method == 'POST':
        try:
            # تحديث بيانات العارض
            exhibitor.company_name = request.form.get('company_name')
            exhibitor.specialization_id = request.form.get('specialization_id')
            exhibitor.company_description = request.form.get('description')

            # معالجة رفع الشعار
            if 'logo' in request.files:
                logo = request.files['logo']
                if logo.filename != '':
                    if allowed_file(logo.filename):
                        # إنشاء اسم فريد للملف باستخدام الطابع الزمني
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + secure_filename(logo.filename)
                        
                        # التأكد من وجود المجلد وإنشاؤه إذا لم يكن موجوداً
                        upload_path = os.path.join(current_app.root_path, 'static', 'images', 'exhibitors')
                        if not os.path.exists(upload_path):
                            os.makedirs(upload_path)
                        
                        # حفظ الملف
                        file_path = os.path.join(upload_path, filename)
                        logo.save(file_path)
                        
                        # تحديث مسار الصورة في قاعدة البيانات
                        if exhibitor.profile_image_url:
                            # حذف الصورة القديمة
                            old_file = os.path.join(current_app.root_path, 'static', 
                                                  exhibitor.profile_image_url.lstrip('/'))
                            if os.path.exists(old_file):
                                os.remove(old_file)
                        
                        exhibitor.profile_image_url = f'/static/images/exhibitors/{filename}'
                    else:
                        flash('نوع الملف غير مسموح به. يرجى استخدام JPG، PNG، أو GIF فقط.', 'error')
                        return redirect(url_for('edit_exhibitor_profile'))

            db.session.commit()
            flash('تم تحديث الملف الشخصي بنجاح', 'success')
            return redirect(url_for('exhibitor_profile', exhibitor_id=current_user.id))
            
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء تحديث الملف الشخصي', 'error')
            print(str(e))
    
    # جلب التخصص الحالي للعارض
    current_specialization = None
    if exhibitor.specialization_id:
        current_specialization = Specialization.query.get(exhibitor.specialization_id)
    
    return render_template('exhibitor_profile_edit.html',
                         exhibitor=exhibitor,
                         specializations=specializations,
                         current_specialization=current_specialization)

# Language route
@app.route('/set-language/<language>')
def set_language(language):
    """Set the user's preferred language"""
    if language in ['en', 'ar', 'fr']:
        session['language'] = language
        return redirect(request.referrer or url_for('landing'))
    return redirect(request.referrer or url_for('landing'))

# Banner management routes
@app.route('/admin/banners')
@login_required
@admin_required
def manage_banners():
    """Admin interface for managing banners"""
    banners = Banner.query.order_by(Banner.order).all()
    return render_template('admin/banners.html', banners=banners)

@app.route('/admin/banners/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_banner():
    """Add a new banner with multilingual support"""
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title')  # Arabic title
            title_en = request.form.get('title_en')
            title_fr = request.form.get('title_fr')
            description = request.form.get('description')  # Arabic description
            description_en = request.form.get('description_en')
            description_fr = request.form.get('description_fr')
            order = request.form.get('order', 0)
            is_active = bool(request.form.get('is_active'))
            
            # Handle file upload
            if 'image' not in request.files:
                flash('No file provided', 'error')
                return redirect(request.url)
                
            file = request.files['image']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
                
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_path = f'/static/images/banners/{filename}'
                
                # Create new banner with multilingual content
                banner = Banner(
                    title=title,
                    title_en=title_en,
                    title_fr=title_fr,
                    description=description,
                    description_en=description_en,
                    description_fr=description_fr,
                    image_path=image_path,
                    order=order,
                    is_active=is_active
                )
                
                db.session.add(banner)
                db.session.commit()
                flash('Banner added successfully!', 'success')
                return redirect(url_for('manage_banners'))
            else:
                flash('Invalid file type', 'error')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding banner: {str(e)}', 'error')
            
    return render_template('admin/banner_form.html')
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        link = request.form.get('link')
        order = request.form.get('order', 0, type=int)
        is_active = bool(request.form.get('is_active'))
        
        if 'image' not in request.files:
            flash('No image file provided', 'error')
            return redirect(request.url)
            
        file = request.files['image']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            
            banner = Banner(
                title=title,
                description=description,
                image_path=f'/static/images/banners/{filename}',
                link=link,
                order=order,
                is_active=is_active
            )
            
            db.session.add(banner)
            db.session.commit()
            
            flash('Banner added successfully', 'success')
            return redirect(url_for('manage_banners'))
            
    return render_template('admin/banner_form.html', banner=None)

@app.route('/admin/banners/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_banner(id):
    """Edit an existing banner"""
    banner = Banner.query.get_or_404(id)
    
    if request.method == 'POST':
        banner.title = request.form.get('title')
        banner.description = request.form.get('description')
        banner.link = request.form.get('link')
        banner.order = request.form.get('order', 0, type=int)
        banner.is_active = bool(request.form.get('is_active'))
        
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                if allowed_file(file.filename):
                    # Remove old image if it exists
                    if banner.image_path:
                        old_image = os.path.join(app.root_path, banner.image_path.lstrip('/'))
                        if os.path.exists(old_image):
                            os.remove(old_image)
                    
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    banner.image_path = f'/static/images/banners/{filename}'
        
        db.session.commit()
        flash('Banner updated successfully', 'success')
        return redirect(url_for('manage_banners'))
        
    return render_template('admin/banner_form.html', banner=banner)

@app.route('/admin/banners/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_banner(id):
    """Delete a banner"""
    banner = Banner.query.get_or_404(id)
    
    # Remove image file
    if banner.image_path:
        image_path = os.path.join(app.root_path, banner.image_path.lstrip('/'))
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(banner)
    db.session.commit()
    
    flash('Banner deleted successfully', 'success')
    return redirect(url_for('manage_banners'))

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

def init_banners():
    """Initialize banners in the database"""
    try:
        # Check if banners already exist
        if Banner.query.first() is None:
            banners = [
                {
                    'title': 'معرض الأغذية العالمي 2025',
                    'description': 'اكتشف أحدث المنتجات والابتكارات في صناعة الأغذية',
                    'image_path': '/static/images/banners/94b8645acef5852980278eb1f65dace9.png',
                    'order': 1,
                    'is_active': True
                },
                {
                    'title': 'معرض الصناعات الغذائية',
                    'description': 'انضم إلى أكبر تجمع للشركات العالمية في مجال الأغذية',
                    'image_path': '/static/images/banners/c49d2b879f33281ddab7b2622ac26fd6.png',
                    'order': 2,
                    'is_active': True
                },
                {
                    'title': 'استكشف الفرص الاستثمارية',
                    'description': 'فرص استثمارية واعدة في قطاع الصناعات الغذائية',
                    'image_path': '/static/images/banners/f0ab21cde3bc84ac57a308db1514b772.png',
                    'order': 3,
                    'is_active': True
                },
                {
                    'title': 'معرض الأغذية 2025',
                    'description': 'تواصل مع أكثر من 500 عارض من مختلف أنحاء العالم',
                    'image_path': '/static/images/banners/VISIT-FOODEXPO-2022.jpg',
                    'order': 4,
                    'is_active': True
                },
                {
                    'title': 'معرض المكونات الغذائية العالمي',
                    'description': 'اكتشف أحدث التقنيات والمكونات في صناعة الأغذية',
                    'image_path': '/static/images/banners/World-Food-Ingredients-Expo-2023.jpg',
                    'order': 5,
                    'is_active': True
                }
            ]
            
            for banner_data in banners:
                banner = Banner(**banner_data)
                db.session.add(banner)
            
            db.session.commit()
            print("Default banners initialized successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing banners: {str(e)}")

# Initialize banners when the application starts
with app.app_context():
    init_banners()

# Track user analytics
def track_user_action(action_type, page_visited=None, exhibitor_id=None, product_id=None):
    if current_user.is_authenticated and exhibitor_id is not None:
        analytics = ExhibitorAnalytics()
        analytics.exhibitor_id = exhibitor_id
        analytics.user_id = current_user.id
        analytics.action_type = action_type
        analytics.page_visited = page_visited
        analytics.product_id = product_id
        db.session.add(analytics)
        db.session.commit()

@app.route('/')
def index():
    """Landing page with featured products and exhibition overview"""
    # Get active banners ordered by their display order
    banners = Banner.query.filter_by(is_active=True).order_by(Banner.order).all()
    
    if current_user.is_authenticated:
        # Track homepage visit
        track_user_action('visit', 'homepage')
        
        # Get featured products for homepage
        featured_products = Product.query.filter_by(is_homepage_featured=True, is_active=True).limit(6).all()
        
        # Get gallery halls with exhibitor counts
        halls = {}
        for hall in ['hall1', 'hall2', 'hall3']:
            count = Exhibitor.query.filter_by(gallery_hall=hall, is_active=True).count()
            halls[hall] = count
        
        return render_template('index.html', 
                             banners=banners,
                             featured_products=featured_products,
                             halls=halls,
                             user=current_user)
    else:
        # Show landing page for non-authenticated users
        return render_template('landing.html', banners=banners)
        featured_products = Product.query.filter_by(is_homepage_featured=True, is_active=True).limit(6).all()
        return render_template('landing.html', featured_products=featured_products)

@app.route('/gallery')
@login_required
def gallery():
    """3D Gallery main page"""
    track_user_action('visit', 'gallery')
    
    # Get all active exhibitors grouped by hall
    exhibitors_by_hall = {}
    for hall in ['hall1', 'hall2', 'hall3']:
        exhibitors = Exhibitor.query.filter_by(gallery_hall=hall, is_active=True).order_by(Exhibitor.ranking).all()
        exhibitors_by_hall[hall] = exhibitors
    
    # Get gallery advertisements
    ads = GalleryAd.query.filter_by(is_active=True).order_by(GalleryAd.display_order).all()
    
    return render_template('gallery.html', 
                         exhibitors_by_hall=exhibitors_by_hall,
                         ads=ads)

@app.route('/gallery/<hall>')
@login_required
def gallery_hall(hall):
    """Specific gallery hall view"""
    track_user_action('visit', f'gallery_{hall}')
    
    # Get exhibitors for this hall
    exhibitors = Exhibitor.query.filter_by(gallery_hall=hall, is_active=True).order_by(Exhibitor.ranking).all()
    
    # Get hall-specific advertisements
    ads = GalleryAd.query.filter_by(hall=hall, is_active=True).order_by(GalleryAd.display_order).all()
    
    return render_template('gallery_hall.html', 
                         exhibitors=exhibitors,
                         hall=hall,
                         ads=ads)

@app.route('/exhibitor/<int:exhibitor_id>')
@login_required
def exhibitor_profile(exhibitor_id):
    """Exhibitor profile page with products and chat"""
    exhibitor = Exhibitor.query.get_or_404(exhibitor_id)
    
    # Track profile visit
    track_user_action('visit', 'exhibitor_profile', exhibitor_id=exhibitor_id)

    user_id = exhibitor.user_id
    
    # Get exhibitor's products
    products = Product.query.filter_by(exhibitor_id=user_id, is_active=True, is_featured=True).all()
    
    # Get exhibitor's videos
    videos = Video.query.filter_by(exhibitor_id=user_id, is_active=True).all()
    
    # Check if user has favorited this exhibitor
    is_favorited = False
    if current_user.is_authenticated:
        favorite = FavoriteExhibitor.query.filter_by(
            user_id=current_user.id,
            exhibitor_id=exhibitor_id
        ).first()
        is_favorited = favorite is not None
    
    # Get available schedules - use exhibitor.user_id since that's what we store in AvailabilitySchedule
    schedules = AvailabilitySchedule.query.filter_by(
        exhibitor_id=exhibitor.user_id,
        is_active=True
    ).all()
    
    # Get existing bookings for next 30 days
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=30)
    booked_slots = Booking.query.filter(
        Booking.exhibitor_id == exhibitor.user_id,  # Use user_id here too
        Booking.booking_date >= start_date,
        Booking.booking_date <= end_date,
        Booking.status.in_(['pending', 'confirmed'])
    ).all()
    
    # Get other products (products from same specialization but different exhibitor)
    if exhibitor.user.specialization_id:
        other_products = Product.query.filter_by(exhibitor_id=user_id, is_active=True).all()
    else:
        other_products = []

    # Calculate available slots
    available_slots = []
    for schedule in schedules:
        today = datetime.now().date()
        for i in range(30):  # Next 30 days
            date = today + timedelta(days=i)
            if date.weekday() == schedule.day_of_week:
                slots = schedule.get_available_slots(date)
                # Filter out booked slots
                booked_times = {(b.start_time, b.end_time) for b in booked_slots if b.booking_date == date}
                available_slots.extend([
                    {'date': date, 'start': slot['start'], 'end': slot['end']}
                    for slot in slots
                    if (slot['start'], slot['end']) not in booked_times
                ])

    return render_template('exhibitor_profile.html',
                         exhibitor=exhibitor,
                         products=products,
                         other_products=other_products,
                         videos=videos,
                         is_favorited=is_favorited,
                         available_slots=available_slots)



@app.route('/my-box')
@login_required
def my_box():
    """User's saved exhibitors and products"""
    # Get user's favorite exhibitors
    favorite_exhibitors = db.session.query(Exhibitor).join(FavoriteExhibitor).filter(
        FavoriteExhibitor.user_id == current_user.id
    ).all()
    
    # Get user's favorite products
    favorite_products = db.session.query(Product).join(FavoriteProduct).filter(
        FavoriteProduct.user_id == current_user.id
    ).all()
    
    # Count total favorites
    favorites_count = len(favorite_exhibitors) + len(favorite_products)
    
    # Get visited exhibitors count from analytics
    visited_count = db.session.query(ExhibitorAnalytics).filter(
        ExhibitorAnalytics.user_id == current_user.id,
        ExhibitorAnalytics.action_type == 'visit'
    ).distinct(ExhibitorAnalytics.exhibitor_id).count()
    
    # Get scheduled meetings count
    meetings_count = db.session.query(Appointment).filter(
        Appointment.user_id == current_user.id,
        Appointment.status != 'cancelled'
    ).count()
    
    return render_template('my_box.html',
                         favorites=favorite_exhibitors + favorite_products,  # Combined list for the template
                         favorite_exhibitors=favorite_exhibitors,
                         favorite_products=favorite_products,
                         favorites_count=favorites_count,
                         visited_count=visited_count,
                         meetings_count=meetings_count)

@app.route('/toggle-favorite-exhibitor/<int:exhibitor_id>', methods=['POST'])
@login_required
def toggle_favorite_exhibitor(exhibitor_id):
    """Add/remove exhibitor from favorites"""
    favorite = FavoriteExhibitor.query.filter_by(
        user_id=current_user.id,
        exhibitor_id=exhibitor_id
    ).first()
    
    if favorite:
        # Remove from favorites
        db.session.delete(favorite)
        action = 'removed'
    else:
        # Add to favorites
        favorite = FavoriteExhibitor()
        favorite.user_id = current_user.id
        favorite.exhibitor_id = exhibitor_id
        db.session.add(favorite)
        action = 'added'
        
        # Track favorite action
        track_user_action('favorite', 'exhibitor_profile', exhibitor_id=exhibitor_id)
    
    db.session.commit()
    return jsonify({'status': 'success', 'action': action})

@app.route('/toggle-favorite-product/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite_product(product_id):
    """Add/remove product from favorites"""
    favorite = FavoriteProduct.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if favorite:
        # Remove from favorites
        db.session.delete(favorite)
        action = 'removed'
    else:
        # Add to favorites
        favorite = FavoriteProduct()
        favorite.user_id = current_user.id
        favorite.product_id = product_id
        db.session.add(favorite)
        action = 'added'
        
        # Track favorite action
        product = Product.query.get(product_id)
        if product:
            track_user_action('favorite', 'product', exhibitor_id=product.exhibitor_id, product_id=product_id)
    
    db.session.commit()
    return jsonify({'status': 'success', 'action': action})

@app.route('/book-appointment', methods=['POST'])
@login_required
def book_appointment():
    """Book an appointment with an exhibitor"""
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    booking_date_str = data.get('date')
    start_time_str = data.get('time')
    notes = data.get('notes', '')
    
    if not all([schedule_id, booking_date_str, start_time_str]):
        return jsonify({'status': 'error', 'message': 'جميع البيانات المطلوبة غير مكتملة'})
    
    try:
        # Parse date and time
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        
        # Get schedule with locking
        with db.session.begin():
            schedule = AvailabilitySchedule.query.with_for_update().get(schedule_id)
            
            if not schedule:
                return jsonify({'status': 'error', 'message': 'جدول المواعيد غير موجود'})
            
            # Calculate end time
            end_time_dt = datetime.combine(booking_date, start_time) + timedelta(minutes=schedule.session_duration)
            end_time = end_time_dt.time()
            
            # Check if slot is already booked
            existing_booking = Booking.query.filter_by(
                exhibitor_id=schedule.exhibitor_id,
                booking_date=booking_date,
                start_time=start_time,
                status='confirmed'
            ).first()
            
            if existing_booking:
                return jsonify({'status': 'error', 'message': 'هذا الموعد محجوز مسبقاً'})
            
            # Create new booking
            booking = Booking(
                user_id=current_user.id,
                exhibitor_id=schedule.exhibitor_id,
                schedule_id=schedule_id,
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time,
                notes=notes
            )
            
            db.session.add(booking)
        
        # Track appointment booking (outside transaction)
        track_user_action('booking', 'create', exhibitor_id=schedule.exhibitor_id)
        
        return jsonify({'status': 'success', 'message': 'تم حجز الموعد بنجاح'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error booking appointment: {str(e)}")
        return jsonify({'status': 'error', 'message': 'حدث خطأ في حجز الموعد'})

# API Routes for JavaScript functionality

@app.route('/api/chat-history/<int:exhibitor_id>')
@login_required
def get_chat_history(exhibitor_id):
    """Get chat history for an exhibitor"""
    try:
        messages = ChatMessage.query.filter_by(
            exhibitor_id=exhibitor_id,
            user_id=current_user.id
        ).order_by(ChatMessage.created_at).limit(50).all()
        
        chat_data = []
        for message in messages:
            chat_data.append({
                'message': message.message,
                'sender_type': 'exhibitor' if message.is_from_exhibitor else 'user',
                'timestamp': message.created_at.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'messages': chat_data
        })
    except Exception as e:
        logging.error(f"Error loading chat history: {str(e)}")
        return jsonify({'status': 'error', 'message': 'حدث خطأ في تحميل المحادثة'})

@app.route('/api/product/<int:product_id>')
@login_required
def get_product_details(product_id):
    """Get product details for modal display"""
    try:
        product = Product.query.get_or_404(product_id)
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'currency': product.currency,
            'image_url': product.image_url,
            'exhibitor_id': product.exhibitor_id,
            'is_featured': product.is_featured
        }
        
        return jsonify({
            'status': 'success',
            'product': product_data
        })
    except Exception as e:
        logging.error(f"Error loading product details: {str(e)}")
        return jsonify({'status': 'error', 'message': 'حدث خطأ في تحميل المنتج'})

@app.route('/api/available-slots/<int:schedule_id>')
@login_required
def get_available_slots(schedule_id):
    """Get available appointment slots for a specific schedule"""
    try:
        # Get the specific schedule
        schedule = AvailabilitySchedule.query.get_or_404(schedule_id)
        if not schedule.is_active:
            return jsonify({'status': 'error', 'message': 'هذا الجدول غير متاح حالياً'})
        
        # Get next 30 days of available slots
        today = datetime.now().date()
        available_slots = []
        
        # Look at next 30 days
        for i in range(30):
            date = today + timedelta(days=i)
            # Only check days matching the schedule's day_of_week
            if date.weekday() == schedule.day_of_week:
                # Get slots for this date
                day_slots = schedule.get_available_slots(date)
                
                # Filter out booked slots
                booked_times = {(b.start_time, b.end_time) for b in Booking.query.filter_by(
                    exhibitor_id=schedule.exhibitor_id,
                    booking_date=date,
                    status='confirmed'
                ).all()}
        
                # Add available slots that aren't booked
                for slot in day_slots:
                    if (slot['start'], slot['end']) not in booked_times:
                        available_slots.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'start': slot['start'].strftime('%H:%M'),
                            'end': slot['end'].strftime('%H:%M')
                        })
        
        return jsonify({
            'status': 'success',
            'slots': available_slots,
            'schedule': {
                'day_of_week': schedule.day_of_week,
                'start_time': schedule.start_time.strftime('%H:%M'),
                'end_time': schedule.end_time.strftime('%H:%M'),
                'session_duration': schedule.session_duration
            }
        })
    
    except Exception as e:
        logging.error(f"Error loading available slots: {str(e)}")
        return jsonify({'status': 'error', 'message': 'حدث خطأ في تحميل المواعيد المتاحة'})

# Socket.IO events for chat system
@socketio.on('join_chat')
def on_join_chat(data):
    """Join a chat room with an exhibitor"""
    if not current_user.is_authenticated:
        return
        
    exhibitor_id = data['exhibitor_id']
    room = f"chat_{exhibitor_id}"
    join_room(room)
    
    # Track chat initiation
    track_user_action('chat', 'join', exhibitor_id=exhibitor_id)
    
    emit('chat_joined', {'room': room})

@socketio.on('send_message')
def on_send_message(data):
    """Send a chat message"""
    if not current_user.is_authenticated:
        return
        
    exhibitor_id = data['exhibitor_id']
    message_text = data['message']
    
    # Save message to database
    message = ChatMessage()
    message.user_id = current_user.id
    message.exhibitor_id = exhibitor_id
    message.message = message_text
    message.is_from_exhibitor = False
    db.session.add(message)
    db.session.commit()
    
    room = f"chat_{exhibitor_id}"
    emit('new_message', {
        'message': message_text,
        'user_name': f"{current_user.first_name} {current_user.last_name}",
        'timestamp': message.created_at.strftime('%H:%M'),
        'is_from_exhibitor': False
    }, to=room)

# Admin and Exhibitor Routes (basic implementations)
@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard - redirects based on role"""
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'exhibitor':
        return redirect(url_for('exhibitor.dashboard'))
    else:
        return redirect(url_for('my_box'))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

# Specialization Management Routes
@app.route('/admin/specializations')
@admin_required
def manage_specializations():
    specializations = Specialization.query.all()
    return render_template('admin/specializations.html', specializations=specializations)

@app.route('/admin/specializations/add', methods=['POST'])
@admin_required
def add_specialization():
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Name is required', 'error')
        return redirect(url_for('manage_specializations'))
    
    existing = Specialization.query.filter_by(name=name).first()
    if existing:
        flash('A specialization with this name already exists', 'error')
        return redirect(url_for('manage_specializations'))
    
    specialization = Specialization(name=name, description=description)
    db.session.add(specialization)
    db.session.commit()
    
    flash('Specialization added successfully', 'success')
    return redirect(url_for('manage_specializations'))

@app.route('/admin/specializations/edit/<int:id>', methods=['POST'])
@admin_required
def edit_specialization(id):
    specialization = Specialization.query.get_or_404(id)
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Specialization name is required', 'error')
        return redirect(url_for('manage_specializations'))
    
    existing = Specialization.query.filter(
        Specialization.name == name,
        Specialization.id != id
    ).first()
    
    if existing:
        flash('A specialization with this name already exists', 'error')
        return redirect(url_for('manage_specializations'))
    
    specialization.name = name
    specialization.description = description
    db.session.commit()
    
    flash('Specialization updated successfully', 'success')
    return redirect(url_for('manage_specializations'))

@app.route('/admin/specializations/delete/<int:id>', methods=['POST'])
@admin_required
def delete_specialization(id):
    specialization = Specialization.query.get_or_404(id)
    
    # Check if any exhibitors are using this specialization
    if User.query.filter_by(specialization_id=id).first():
        flash('Cannot delete specialization as it is being used by exhibitors', 'error')
        return redirect(url_for('manage_specializations'))
    
    db.session.delete(specialization)
    db.session.commit()
    
    flash('Specialization deleted successfully', 'success')
    return redirect(url_for('manage_specializations'))

# Utility function to get specialization
def get_specialization(specialization_id):
    from models import Specialization
    return Specialization.query.get(specialization_id)

# Exhibitor Approval Routes
@app.route('/admin/exhibitors/pending')
@admin_required
def pending_exhibitors():
    exhibitors = User.query.filter_by(role='exhibitor', is_active=False).all()
    return render_template('admin/pending_exhibitors.html', 
                         exhibitors=exhibitors,
                         get_specialization=get_specialization)

@app.route('/admin/exhibitors/approve/<int:id>', methods=['POST'])
@admin_required
def approve_exhibitor(id):
    exhibitor = User.query.get_or_404(id)
    if exhibitor.role != 'exhibitor':
        flash('Invalid user role', 'error')
        return redirect(url_for('pending_exhibitors'))
    
    exhibitor.is_active = True
    db.session.commit()
    flash('Exhibitor approved successfully', 'success')
    return redirect(url_for('pending_exhibitors'))

@app.route('/admin/exhibitors/reject/<int:id>', methods=['POST'])
@admin_required
def reject_exhibitor(id):
    exhibitor = User.query.get_or_404(id)
    if exhibitor.role != 'exhibitor':
        flash('Invalid user role', 'error')
        return redirect(url_for('pending_exhibitors'))
    
    db.session.delete(exhibitor)
    db.session.commit()
    flash('Exhibitor rejected and removed', 'success')
    return redirect(url_for('pending_exhibitors'))