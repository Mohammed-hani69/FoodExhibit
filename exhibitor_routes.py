from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import AvailableSlot, db, User, Product, ExhibitorAnalytics, FavoriteExhibitor, Appointment, Specialization, ExhibitorBanner, Video
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from functools import wraps

exhibitor = Blueprint("exhibitor", __name__, url_prefix="/exhibitor")

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@exhibitor.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != 'exhibitor':
        flash('Access denied. This area is for exhibitors only.', 'error')
        return redirect(url_for('index'))
    
    # Use current_user directly - all exhibitor data is now in the User model
    exhibitor = current_user
    
    # Get analytics data for this exhibitor
    analytics = ExhibitorAnalytics.query.filter_by(exhibitor_id=exhibitor.id).first()
    
    # Get favorite count for this exhibitor
    favorite_count = FavoriteExhibitor.query.filter_by(exhibitor_id=exhibitor.id).count()
    
    # Get upcoming appointments for this exhibitor
    upcoming_appointments = Appointment.query.filter_by(exhibitor_id=exhibitor.id)\
        .filter(Appointment.status != 'cancelled')\
        .order_by(Appointment.appointment_date.asc())\
        .limit(5)\
        .all()
    
    return render_template('exhibitor_dashboard.html',
                         exhibitor=exhibitor,
                         analytics=analytics,
                         favorite_count=favorite_count,
                         upcoming_appointments=upcoming_appointments)

@exhibitor.route("/profile/<int:exhibitor_id>")
def profile(exhibitor_id):
    # Get the user (exhibitor) directly - all data is now in User model
    exhibitor_profile = User.query.filter_by(id=exhibitor_id, role='exhibitor').first_or_404()
    
    # Get exhibitor's products
    products = Product.query.filter_by(exhibitor_id=exhibitor_profile.id).all()
    
    # Get exhibitor's banners
    banners = ExhibitorBanner.query.filter_by(
        exhibitor_id=exhibitor_profile.id, 
        is_active=True
    ).order_by(ExhibitorBanner.display_order).all()
    
    # Get exhibitor's videos
    videos = Video.query.filter_by(
        exhibitor_id=exhibitor_profile.id,
        is_active=True
    ).all()
    
    # Check if favorited
    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = FavoriteExhibitor.query.filter_by(
            user_id=current_user.id,
            exhibitor_id=exhibitor_profile.id
        ).first() is not None

    # Get available slots for this exhibitor
    available_slots = AvailableSlot.query.filter_by(
        exhibitor_id=exhibitor_profile.id,
        is_available=True
    ).order_by(AvailableSlot.start_time).all()

    # Get booked slots for the current user with this exhibitor
    booked_slots = []
    if current_user.is_authenticated:
        booked_slots = Appointment.query.filter_by(
            user_id=current_user.id,
            exhibitor_id=exhibitor_profile.id,
            status='scheduled'
        ).all()

    return render_template('exhibitor_profile.html',
                         exhibitor=exhibitor_profile,
                         user=exhibitor_profile,
                         products=products,
                         banners=banners,
                         videos=videos,
                         is_favorited=is_favorited,
                         description=exhibitor_profile.company_description,
                         available_slots=available_slots,
                         booked_slots=booked_slots)


@exhibitor.route("/profile/edit", methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.role != 'exhibitor':
        flash('Access denied. This area is for exhibitors only.', 'error')
        return redirect(url_for('index'))

    # Get all specializations for the dropdown
    specializations = Specialization.query.all()

    if request.method == 'POST':
        try:
            # Get form data
            company_name = request.form.get('company_name')
            specialization_id = request.form.get('specialization_id')
            description = request.form.get('description')

            # Update exhibitor data - all data is now stored in User model
            exhibitor = User.query.get(current_user.id)
            exhibitor.company_name = company_name
            exhibitor.specialization_id = specialization_id
            exhibitor.company_description = description

            # Handle logo upload
            if 'logo' in request.files and request.files['logo'].filename:
                logo = request.files['logo']
                if logo and allowed_file(logo.filename):
                    # Generate a unique filename using timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + secure_filename(logo.filename)
                    
                    # Create directory if it doesn't exist
                    upload_path = os.path.join(current_app.root_path, 'static', 'images', 'exhibitors')
                    if not os.path.exists(upload_path):
                        os.makedirs(upload_path)
                    
                    # Save the file
                    filepath = os.path.join(upload_path, filename)
                    logo.save(filepath)
                    
                    # Update the database
                    exhibitor.profile_image_url = f'/static/images/exhibitors/{filename}'
                    
                    # Delete old logo if exists
                    if exhibitor.profile_image_url and os.path.exists(os.path.join(current_app.root_path, 'static', exhibitor.profile_image_url.lstrip('/'))):
                        os.remove(os.path.join(current_app.root_path, 'static', exhibitor.profile_image_url.lstrip('/')))

            db.session.commit()
            flash('تم تحديث الملف الشخصي بنجاح', 'success')
            return redirect(url_for('exhibitor.profile', exhibitor_id=current_user.id))

        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء تحديث الملف الشخصي', 'error')

    # Get current exhibitor and specialization
    exhibitor = User.query.get(current_user.id)
    
    # Order specializations by name for better display
    specializations = Specialization.query.order_by(Specialization.name).all()
    
    # Get current specialization name for displaying in form
    current_specialization = None
    if exhibitor.specialization_id:
        current_specialization = Specialization.query.get(exhibitor.specialization_id)
    
    return render_template('exhibitor_profile_edit.html',
                         exhibitor=exhibitor,
                         specializations=specializations,
                         current_specialization=current_specialization)
