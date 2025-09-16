from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import current_user, logout_user
from flask_socketio import emit, join_room, leave_room
from app import app, db, socketio
from models import *
from replit_auth import require_login, make_replit_blueprint
from datetime import datetime, timedelta
import logging

# Register Replit Auth blueprint
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

# Track user analytics
def track_user_action(action_type, page_visited=None, exhibitor_id=None, product_id=None):
    if current_user.is_authenticated:
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
                             featured_products=featured_products,
                             halls=halls,
                             user=current_user)
    else:
        # Show landing page for non-authenticated users
        featured_products = Product.query.filter_by(is_homepage_featured=True, is_active=True).limit(6).all()
        return render_template('landing.html', featured_products=featured_products)

@app.route('/gallery')
@require_login
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
@require_login
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
@require_login
def exhibitor_profile(exhibitor_id):
    """Exhibitor profile page with products and chat"""
    exhibitor = Exhibitor.query.get_or_404(exhibitor_id)
    
    # Track profile visit
    track_user_action('visit', 'exhibitor_profile', exhibitor_id=exhibitor_id)
    
    # Get exhibitor's products
    products = Product.query.filter_by(exhibitor_id=exhibitor_id, is_active=True).all()
    
    # Check if user has favorited this exhibitor
    is_favorited = False
    if current_user.is_authenticated:
        favorite = FavoriteExhibitor.query.filter_by(
            user_id=current_user.id,
            exhibitor_id=exhibitor_id
        ).first()
        is_favorited = favorite is not None
    
    # Get available appointment slots (next 30 days)
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    available_slots = AvailableSlot.query.filter(
        AvailableSlot.exhibitor_id == exhibitor_id,
        AvailableSlot.start_time >= start_date,
        AvailableSlot.start_time <= end_date,
        AvailableSlot.is_available == True
    ).order_by(AvailableSlot.start_time).all()
    
    return render_template('exhibitor_profile.html',
                         exhibitor=exhibitor,
                         products=products,
                         is_favorited=is_favorited,
                         available_slots=available_slots)

@app.route('/my-box')
@require_login
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
    
    return render_template('my_box.html',
                         favorite_exhibitors=favorite_exhibitors,
                         favorite_products=favorite_products)

@app.route('/toggle-favorite-exhibitor/<int:exhibitor_id>', methods=['POST'])
@require_login
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
@require_login
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
@require_login
def book_appointment():
    """Book an appointment with an exhibitor"""
    data = request.get_json()
    slot_id = data.get('slot_id')
    notes = data.get('notes', '')
    
    slot = AvailableSlot.query.get_or_404(slot_id)
    
    if not slot.is_available:
        return jsonify({'status': 'error', 'message': 'هذا الموعد غير متاح'})
    
    # Create appointment
    appointment = Appointment()
    appointment.user_id = current_user.id
    appointment.exhibitor_id = slot.exhibitor_id
    appointment.slot_id = slot_id
    appointment.appointment_date = slot.start_time
    appointment.duration_minutes = slot.duration_minutes
    appointment.notes = notes
    
    # Mark slot as unavailable
    slot.is_available = False
    
    db.session.add(appointment)
    db.session.commit()
    
    # Track appointment booking
    track_user_action('appointment', 'booking', exhibitor_id=slot.exhibitor_id)
    
    return jsonify({'status': 'success', 'message': 'تم حجز الموعد بنجاح'})

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
@require_login
def dashboard():
    """User dashboard - redirects based on role"""
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'exhibitor':
        return redirect(url_for('exhibitor_dashboard'))
    else:
        return redirect(url_for('my_box'))

@app.route('/admin')
@require_login
def admin_dashboard():
    """Admin dashboard"""
    if current_user.role != 'admin':
        flash('غير مصرح لك بالوصول لهذه الصفحة')
        return redirect(url_for('index'))
    
    # Get statistics
    total_users = User.query.count()
    total_exhibitors = Exhibitor.query.count()
    total_products = Product.query.count()
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         total_exhibitors=total_exhibitors,
                         total_products=total_products)

@app.route('/exhibitor-dashboard')
@require_login
def exhibitor_dashboard():
    """Exhibitor dashboard"""
    if current_user.role != 'exhibitor':
        flash('غير مصرح لك بالوصول لهذه الصفحة')
        return redirect(url_for('index'))
    
    exhibitor = Exhibitor.query.filter_by(user_id=current_user.id).first()
    if not exhibitor:
        flash('لم يتم العثور على ملف العارض')
        return redirect(url_for('index'))
    
    # Get exhibitor's analytics
    total_visits = ExhibitorAnalytics.query.filter_by(
        exhibitor_id=exhibitor.id,
        action_type='visit'
    ).count()
    
    total_favorites = FavoriteExhibitor.query.filter_by(exhibitor_id=exhibitor.id).count()
    total_appointments = Appointment.query.filter_by(exhibitor_id=exhibitor.id).count()
    
    return render_template('exhibitor_dashboard.html',
                         exhibitor=exhibitor,
                         total_visits=total_visits,
                         total_favorites=total_favorites,
                         total_appointments=total_appointments)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403