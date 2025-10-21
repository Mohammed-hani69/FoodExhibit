from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from extensions import db
from models import Package, User, Order, Visit, Product, Settings, Exhibitor, Specialization, Video, ExhibitorBanner
import os
from werkzeug.utils import secure_filename
from auth import admin_required
import json
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import os
from werkzeug.utils import secure_filename

admin = Blueprint('admin', __name__, url_prefix='/admin')

# Configure upload folders
VIDEOS_UPLOAD_FOLDER = os.path.join('static', 'videos', 'exhibitors')
BANNERS_UPLOAD_FOLDER = os.path.join('static', 'images', 'banners', 'exhibitors')
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@admin.route('/products')
@login_required
@admin_required
def manage_products():
    """Product management page"""
    # Get all products with eager loading of exhibitors
    products = Product.query.all()
    
    # Get all users who are exhibitors
    exhibitors = User.query.filter_by(role='exhibitor').order_by(User.company_name).all()
    exhibitor_list = [{
        'id': exhibitor.id,
        'company_name': exhibitor.company_name or f"{exhibitor.first_name} {exhibitor.last_name}",
        'email': exhibitor.email
    } for exhibitor in exhibitors]
    
    return render_template('admin/products.html', products=products, exhibitors=exhibitor_list)

@admin.route('/search-exhibitors')
@login_required
@admin_required
def search_exhibitors():
    """Search exhibitors by name or email"""
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify([])
    
    exhibitors = db.session.query(Exhibitor, User).join(User).filter(
        or_(
            User.email.ilike(f'%{query}%'),
            Exhibitor.company_name.ilike(f'%{query}%')
        )
    ).all()
    
    return jsonify([{
        'id': exhibitor.id,
        'company_name': exhibitor.company_name,
        'email': user.email
    } for exhibitor, user in exhibitors])

@admin.route('/add-product', methods=['POST'])
@login_required
@admin_required
def add_product():
    """Add a new product"""
    try:
        # 1️⃣ جلب معرف العارض (من جدول users)
        exhibitor_id = request.form.get('user_id')

        if not exhibitor_id:
            flash('يجب اختيار العارض أولاً', 'error')
            return redirect(url_for('admin.manage_products'))

        # 2️⃣ التأكد أن المستخدم المختار هو عارض
        exhibitor = User.query.filter_by(id=exhibitor_id, role='exhibitor').first()
        if not exhibitor:
            flash('العارض المحدد غير موجود أو ليس عارضًا', 'error')
            return redirect(url_for('admin.manage_products'))

        # 3️⃣ جلب اسم القسم من جدول التخصصات
        specialization_name = None
        if exhibitor.specialization_id:
            specialization = Specialization.query.get(exhibitor.specialization_id)
            specialization_name = specialization.name if specialization else None

        # 4️⃣ جلب باقي بيانات المنتج من الفورم
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        currency = request.form.get('currency')
        is_featured = bool(request.form.get('is_featured'))
        is_homepage_featured = bool(request.form.get('is_homepage_featured'))

        # 5️⃣ حفظ اسم القسم (category)
        category = specialization_name or "غير محدد"

        # 6️⃣ معالجة الصورة
        image = request.files.get('image')
        image_url = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join('static', 'images', 'products', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)
            image_url = '/' + image_path

        # 7️⃣ إنشاء المنتج
        product = Product(
            exhibitor_id=exhibitor.id,       # حفظ معرف العارض من جدول users
            name=name,
            description=description,
            price=price,
            currency=currency,
            category=category,               # اسم القسم من جدول specialization
            image_url=image_url,
            is_featured=is_featured,
            is_homepage_featured=is_homepage_featured
        )

        db.session.add(product)
        db.session.commit()

        flash('تم إضافة المنتج بنجاح', 'success')
        return redirect(url_for('admin.manage_products'))

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء إضافة المنتج: {str(e)}', 'error')
        return redirect(url_for('admin.manage_products'))


@admin.route('/update-product-feature', methods=['POST'])
@login_required
@admin_required
def update_product_feature():
    """Update product feature status"""
    data = request.json
    product_id = data.get('product_id')
    feature_type = data.get('feature_type')
    is_enabled = data.get('is_enabled')
    
    product = Product.query.get_or_404(product_id)
    
    try:
        if feature_type == 'homepage':
            product.is_homepage_featured = is_enabled
        elif feature_type == 'exhibitor':
            product.is_featured = is_enabled
            
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/delete-product/<int:product_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_product(product_id):
    """Delete a product"""
    product = Product.query.get_or_404(product_id)
    
    try:
        # Delete product image if exists
        if product.image_url:
            image_path = os.path.join('static', product.image_url.lstrip('/'))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/get-product/<int:product_id>')
@login_required
@admin_required
def get_product(product_id):
    """Get product details for editing"""
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'currency': product.currency,
        'category': product.category,
        'is_featured': product.is_featured,
        'is_homepage_featured': product.is_homepage_featured,
        'image_url': product.image_url
    })

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    # Get statistics
    total_users = User.query.count()
    total_exhibitors = User.query.filter_by(role='exhibitor').count()
    total_products = Product.query.count()
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         total_exhibitors=total_exhibitors,
                         total_products=total_products)

# Admin Exhibitor Management Routes
@admin.route('/exhibitors')
@login_required
@admin_required
def exhibitors():
    """Admin exhibitor management page"""
    exhibitors = User.query.filter_by(role='exhibitor').order_by(User.created_at.desc()).all()
    return render_template('admin/exhibitors.html', exhibitors=exhibitors)

@admin.route('/exhibitors/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_exhibitor():
    """Add new exhibitor route"""
    # Get all specializations for the dropdown
    specializations = Specialization.query.order_by(Specialization.name).all()
    
    if request.method == 'POST':
        # Create the User record
        user = User(
            email=request.form['email'],
            password=generate_password_hash(request.form['password'], method='scrypt'),
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            company_name=request.form['company_name'],
            company_description=request.form['company_description'],
            specialization_id=request.form.get('specialization_id'),
            role='exhibitor',
            is_active='is_active' in request.form,
            phone=request.form.get('phone')
        )
        
        # Create the Exhibitor record
        exhibitor = Exhibitor(
            company_name=request.form['company_name'],
            contact_email=request.form['email'],
            contact_phone=request.form.get('phone'),
            country=request.form.get('country')
        )
        
        db.session.add(user)
        
        try:
            db.session.flush()  # This will assign an ID to the user
            exhibitor.user_id = user.id
            db.session.add(exhibitor)
            db.session.commit()
            flash('Exhibitor added successfully.', 'success')
            return redirect(url_for('admin.exhibitors'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding exhibitor. Please try again.', 'danger')
            
    return render_template('admin/exhibitor_form.html', exhibitor=None, specializations=specializations)

@admin.route('/exhibitors/<int:exhibitor_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exhibitor(exhibitor_id):
    """Edit exhibitor route"""
    exhibitor = User.query.filter_by(id=exhibitor_id, role='exhibitor').first_or_404()
    specializations = Specialization.query.order_by(Specialization.name).all()
    
    if request.method == 'POST':
        # Update User information
        exhibitor.email = request.form['email']
        if request.form.get('password'):  # Only update password if provided
            exhibitor.password = generate_password_hash(request.form['password'], method='scrypt')
        exhibitor.first_name = request.form['first_name']
        exhibitor.last_name = request.form['last_name']
        exhibitor.company_name = request.form['company_name']
        exhibitor.company_description = request.form['company_description']
        exhibitor.specialization_id = request.form.get('specialization_id')
        exhibitor.is_active = 'is_active' in request.form
        exhibitor.phone = request.form.get('phone')

        # Update Exhibitor information
        exhibitor_profile = Exhibitor.query.filter_by(user_id=exhibitor.id).first()
        if exhibitor_profile:
            exhibitor_profile.company_name = request.form['company_name']
            exhibitor_profile.contact_email = request.form['email']
            exhibitor_profile.contact_phone = request.form.get('phone')
            exhibitor_profile.country = request.form.get('country')
        
        try:
            db.session.commit()
            flash('Exhibitor updated successfully.', 'success')
            return redirect(url_for('admin.exhibitors'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating exhibitor. Please try again.', 'danger')
            
    return render_template('admin/exhibitor_form.html', exhibitor=exhibitor, specializations=specializations)

@admin.route('/exhibitors/<int:exhibitor_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exhibitor(exhibitor_id):
    """Delete exhibitor route"""
    exhibitor = User.query.filter_by(id=exhibitor_id, role='exhibitor').first_or_404()
    
    try:
        db.session.delete(exhibitor)
        db.session.commit()
        flash('Exhibitor deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting exhibitor. Please try again.', 'danger')
    
    return redirect(url_for('admin.exhibitors'))

# Admin Package Management Routes
@admin.route('/packages')
@login_required
@admin_required
def packages():
    """Admin package management page"""
    packages = Package.query.order_by(Package.created_at.desc()).all()
    return render_template('admin/packages.html', packages=packages)

@admin.route('/packages/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_package():
    """Add new package route"""
    if request.method == 'POST':
        features = request.form.get('features').split('\n')
        features = [f.strip() for f in features if f.strip()]  # Clean up empty lines
        
        package = Package(
            name=request.form['name'],
            name_en=request.form['name_en'],
            price=float(request.form['price']),
            description=request.form['description'],
            description_en=request.form['description_en'],
            features=json.dumps(features),
            is_active='is_active' in request.form
        )
        
        db.session.add(package)
        try:
            db.session.commit()
            flash('Package added successfully.', 'success')
            return redirect(url_for('admin.packages'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding package. Please try again.', 'danger')
            
    return render_template('admin/package_form.html', package=None)

@admin.route('/packages/<int:package_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_package(package_id):
    """Edit package route"""
    package = Package.query.get_or_404(package_id)
    
    if request.method == 'POST':
        features = request.form.get('features').split('\n')
        features = [f.strip() for f in features if f.strip()]
        
        package.name = request.form['name']
        package.name_en = request.form['name_en']
        package.price = float(request.form['price'])
        package.description = request.form['description']
        package.description_en = request.form['description_en']
        package.features = json.dumps(features)
        package.is_active = 'is_active' in request.form
        
        try:
            db.session.commit()
            flash('Package updated successfully.', 'success')
            return redirect(url_for('admin.packages'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating package. Please try again.', 'danger')
            
    return render_template('admin/package_form.html', package=package)

@admin.route('/packages/<int:package_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_package(package_id):
    """Delete package route"""
    package = Package.query.get_or_404(package_id)
    
    try:
        db.session.delete(package)
        db.session.commit()
        flash('Package deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting package. Please try again.', 'danger')
    
    return redirect(url_for('admin.packages'))

# User Management Routes
@admin.route('/users')
@login_required
@admin_required
def users():
    """Admin user management page"""
    # Get users, excluding exhibitors
    users = User.query.filter(User.role != 'exhibitor').order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Add new user route"""
    if request.method == 'POST':
        user = User(
            email=request.form['email'],
            password=generate_password_hash(request.form['password'], method='scrypt'),
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            role=request.form['role'],
            is_active='is_active' in request.form
        )
        
        db.session.add(user)
        try:
            db.session.commit()
            flash('User added successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding user. Please try again.', 'danger')
            
    return render_template('admin/user_form.html', user=None)

@admin.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user route"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.email = request.form['email']
        if request.form.get('password'):  # Only update password if provided
            user.password = generate_password_hash(request.form['password'], method='scrypt')
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.role = request.form['role']
        user.is_active = 'is_active' in request.form
        
        try:
            db.session.commit()
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating user. Please try again.', 'danger')
            
    return render_template('admin/user_form.html', user=user)

@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user route"""
    if user_id == 1:  # Protect the main admin account
        flash('Cannot delete the main administrator account.', 'danger')
        return redirect(url_for('admin.users'))
        
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user. Please try again.', 'danger')
    
    return redirect(url_for('admin.users'))# Sales Report Routes
@admin.route('/sales-report')
@login_required
@admin_required
def sales_report():
    """Admin sales report page"""
    # Get basic stats
    total_sales = Order.query.count()
    revenue = db.session.query(func.sum(Order.amount)).scalar() or 0
    avg_sale = revenue / total_sales if total_sales > 0 else 0
    
    # Calculate conversion rate
    total_visitors = User.query.count()
    conversion_rate = (total_sales / total_visitors * 100) if total_visitors > 0 else 0
    
    # Get recent sales
    sales = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Prepare chart data
    dates = []
    sales_data = []
    package_distribution = []
    
    # Last 30 days data
    for i in range(30, -1, -1):
        date = datetime.now() - timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
        daily_sales = Order.query.filter(
            func.date(Order.created_at) == date.date()
        ).count()
        sales_data.append(daily_sales)
    
    # Package distribution
    packages = Package.query.all()
    for package in packages:
        count = Order.query.filter_by(package_id=package.id).count()
        package_distribution.append(count)
    
    return render_template('admin/sales_report.html',
                         total_sales=total_sales,
                         revenue=revenue,
                         avg_sale=round(avg_sale, 2),
                         conversion_rate=round(conversion_rate, 2),
                         sales=sales,
                         dates=dates,
                         sales_data=sales_data,
                         package_distribution=package_distribution)

@admin.route('/sales-data')
@login_required
@admin_required
def get_sales_data():
    """API endpoint for sales data"""
    time_range = int(request.args.get('timeRange', 30))
    package_type = request.args.get('packageType', 'all')
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=time_range)
    
    # Build query
    query = Order.query.filter(Order.created_at.between(start_date, end_date))
    
    if package_type != 'all':
        query = query.join(Package).filter(Package.name == package_type)
    
    # Get sales trend
    sales_trend = {}
    for order in query.all():
        date = order.created_at.strftime('%Y-%m-%d')
        sales_trend[date] = sales_trend.get(date, 0) + 1
    
    # Get package distribution
    package_dist = {}
    if package_type == 'all':
        for package in Package.query.all():
            count = Order.query.filter_by(package_id=package.id).count()
            package_dist[package.name] = count
    
    return jsonify({
        'salesTrend': sales_trend,
        'packageDist': package_dist
    })

# Visit Statistics Routes
@admin.route('/visit-statistics')
@login_required
@admin_required
def visit_statistics():
    """Admin visit statistics page"""
    # Calculate basic stats
    total_visits = Visit.query.count()
    unique_visitors = db.session.query(func.count(func.distinct(Visit.visitor_id))).scalar()
    
    # Calculate average duration
    avg_duration = db.session.query(func.avg(Visit.duration)).scalar() or 0
    
    # Calculate bounce rate
    bounced_visits = Visit.query.filter(Visit.duration < 30).count()  # Less than 30 seconds
    bounce_rate = (bounced_visits / total_visits * 100) if total_visits > 0 else 0
    
    # Prepare visitor trend data
    dates = []
    visitor_data = []
    visitor_type_distribution = []
    
    # Last 30 days data
    for i in range(30, -1, -1):
        date = datetime.now() - timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
        daily_visits = Visit.query.filter(
            func.date(Visit.timestamp) == date.date()
        ).count()
        visitor_data.append(daily_visits)
    
    # New vs Returning visitors - based on unique visitor_ids
    unique_visitors = db.session.query(Visit.visitor_id).distinct().all()
    repeat_visitors = db.session.query(Visit.visitor_id)\
        .group_by(Visit.visitor_id)\
        .having(func.count(Visit.visitor_id) > 1)\
        .count()
    new_visitors = len(unique_visitors) - repeat_visitors
    visitor_type_distribution = [new_visitors, repeat_visitors]
    
    # Get popular times
    popular_times = []
    for hour in range(24):
        visits = Visit.query.filter(func.extract('hour', Visit.timestamp) == hour).count()
        avg_duration = db.session.query(
            func.avg(Visit.duration)
        ).filter(func.extract('hour', Visit.timestamp) == hour).scalar() or 0
        
        popular_times.append({
            'hour': f"{hour:02d}:00",
            'visitors': visits,
            'avg_duration': f"{int(avg_duration)} seconds",
            'popular_sections': "Main Hall, Exhibition Area"  # This should be dynamic based on actual data
        })
    
    # Sample heatmap data (this should be replaced with actual data)
    heatmap_data = [
        {"x": 100, "y": 100, "value": 50},
        {"x": 200, "y": 200, "value": 80},
        # Add more points based on actual visitor movement data
    ]
    
    return render_template('admin/visit_statistics.html',
                         total_visits=total_visits,
                         unique_visitors=unique_visitors,
                         avg_duration=f"{int(avg_duration)} seconds",
                         bounce_rate=round(bounce_rate, 2),
                         dates=dates,
                         visitor_data=visitor_data,
                         visitor_type_distribution=visitor_type_distribution,
                         popular_times=popular_times,
                         heatmap_data=heatmap_data)

@admin.route('/visitor-data')
@login_required
@admin_required
def get_visitor_data():
    """API endpoint for visitor data"""

@admin.route('/settings')
@login_required
@admin_required
def settings():
    """Admin settings page"""
    settings_dict = {}
    settings = Settings.query.all()
    for setting in settings:
        settings_dict[setting.key] = setting.value
    return render_template('admin/settings.html', settings=settings_dict)

@admin.route('/settings/interface', methods=['POST'])
@login_required
@admin_required
def update_interface_settings():
    """Update interface settings"""
    primary_color = request.form.get('primary_color')
    
    setting = Settings.query.filter_by(key='primary_color').first()
    if setting:
        setting.value = primary_color
    else:
        setting = Settings(key='primary_color', value=primary_color)
        db.session.add(setting)
    
    db.session.commit()
    flash('Interface settings updated successfully', 'success')
    return redirect(url_for('admin.settings'))

@admin.route('/settings/exhibition', methods=['POST'])
@login_required
@admin_required
def update_exhibition_settings():
    """Update exhibition settings"""

# Video Management Routes
@admin.route('/videos')
@login_required
@admin_required
def manage_videos():
    """Video management page"""
    videos = Video.query.all()
    exhibitors = User.query.filter_by(role='exhibitor').order_by(User.company_name).all()
    exhibitor_list = [{
        'id': exhibitor.id,
        'company_name': exhibitor.company_name or f"{exhibitor.first_name} {exhibitor.last_name}",
        'email': exhibitor.email
    } for exhibitor in exhibitors]
    
    return render_template('admin/videos.html', videos=videos, exhibitors=exhibitor_list)

@admin.route('/add-video', methods=['POST'])
@login_required
@admin_required
def add_video():
    """Add a new video"""
    try:
        # Get exhibitor ID
        exhibitor_id = request.form.get('user_id')
        if not exhibitor_id:
            flash('يجب اختيار العارض أولاً', 'error')
            return redirect(url_for('admin.manage_videos'))

        # Verify exhibitor exists
        exhibitor = User.query.filter_by(id=exhibitor_id, role='exhibitor').first()
        if not exhibitor:
            flash('العارض المحدد غير موجود أو ليس عارضاً', 'error')
            return redirect(url_for('admin.manage_videos'))

        # Get video details
        title = request.form.get('title')
        description = request.form.get('description')
        is_active = 'is_active' in request.form

        # Handle video file upload
        video = request.files.get('video')
        video_url = None
        if video and allowed_video_file(video.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video.filename}")
            video_path = os.path.join(VIDEOS_UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            video.save(video_path)
            video_url = '/' + video_path

        # Create new video record
        video = Video(
            exhibitor_id=exhibitor.id,
            title=title,
            description=description,
            video_url=video_url,
            is_active=is_active
        )

        db.session.add(video)
        db.session.commit()

        flash('تم إضافة الفيديو بنجاح', 'success')
        return redirect(url_for('admin.manage_videos'))

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء إضافة الفيديو: {str(e)}', 'error')
        return redirect(url_for('admin.manage_videos'))

@admin.route('/get-video/<int:video_id>')
@login_required
@admin_required
def get_video(video_id):
    """Get video details for editing"""
    video = Video.query.get_or_404(video_id)
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'video_url': video.video_url,
        'is_active': video.is_active
    })

@admin.route('/update-video/<int:video_id>', methods=['POST'])
@login_required
@admin_required
def update_video(video_id):
    """Update an existing video"""
    video = Video.query.get_or_404(video_id)
    
    try:
        # Update video details
        video.title = request.form.get('title')
        video.description = request.form.get('description')
        video.is_active = 'is_active' in request.form

        # Handle new video file if provided
        new_video = request.files.get('video')
        if new_video and allowed_video_file(new_video.filename):
            # Delete old video file if exists
            if video.video_url:
                old_video_path = os.path.join('static', video.video_url.lstrip('/'))
                if os.path.exists(old_video_path):
                    os.remove(old_video_path)

            # Save new video file
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{new_video.filename}")
            video_path = os.path.join(VIDEOS_UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            new_video.save(video_path)
            video.video_url = '/' + video_path

        db.session.commit()
        flash('تم تحديث الفيديو بنجاح', 'success')
        return redirect(url_for('admin.manage_videos'))

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء تحديث الفيديو: {str(e)}', 'error')
        return redirect(url_for('admin.manage_videos'))

@admin.route('/delete-video/<int:video_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_video(video_id):
    """Delete a video"""
    video = Video.query.get_or_404(video_id)
    
    try:
        # Delete video file if exists
        if video.video_url:
            video_path = os.path.join('static', video.video_url.lstrip('/'))
            if os.path.exists(video_path):
                os.remove(video_path)
        
        db.session.delete(video)
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    exhibition_name = request.form.get('exhibition_name')
    exhibition_date = request.form.get('exhibition_date')
    
    # Update exhibition name
    name_setting = Settings.query.filter_by(key='exhibition_name').first()
    if name_setting:
        name_setting.value = exhibition_name
    else:
        name_setting = Settings(key='exhibition_name', value=exhibition_name)
        db.session.add(name_setting)
    
    # Update exhibition date
    date_setting = Settings.query.filter_by(key='exhibition_date').first()
    if date_setting:
        date_setting.value = exhibition_date
    else:
        date_setting = Settings(key='exhibition_date', value=exhibition_date)
        db.session.add(date_setting)
    
    db.session.commit()
    flash('Exhibition settings updated successfully', 'success')
    return redirect(url_for('admin.settings'))
    
# Exhibitor Banner Management Routes
@admin.route('/exhibitor-banners')
@login_required
@admin_required
def manage_exhibitor_banners():
    """Exhibitor banner management page"""
    exhibitors = db.session.query(Exhibitor, User).join(User).order_by(User.company_name).all()
    banners = ExhibitorBanner.query.all()
    
    return render_template('admin/exhibitor_banners.html', 
                         exhibitors=exhibitors,
                         banners=banners)

@admin.route('/exhibitor-banner/add', methods=['POST'])
@login_required
@admin_required
def add_exhibitor_banner():
    """Add a new banner for an exhibitor"""
    try:
        # Get exhibitor ID and title
        exhibitor_id = request.form.get('exhibitor_id')
        title = request.form.get('title')
        
        if not exhibitor_id:
            flash('يجب اختيار العارض أولاً', 'error')
            return redirect(url_for('admin.manage_exhibitor_banners'))

        # Verify exhibitor exists
        exhibitor = Exhibitor.query.get(exhibitor_id)
        if not exhibitor:
            flash('العارض المحدد غير موجود', 'error')
            return redirect(url_for('admin.manage_exhibitor_banners'))

        # Handle banner file upload
        banner = request.files.get('banner')
        if banner and allowed_image_file(banner.filename):
            # Save new banner
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{banner.filename}")
            banner_path = os.path.join(BANNERS_UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(banner_path), exist_ok=True)
            banner.save(banner_path)
            
            # Create new banner record
            new_banner = ExhibitorBanner(
                exhibitor_id=exhibitor_id,
                title=title,
                image_path='/' + banner_path,
                is_active=True
            )
            
            db.session.add(new_banner)
            db.session.commit()

            flash('تم إضافة البنر بنجاح', 'success')
        else:
            flash('يرجى اختيار ملف صورة صالح', 'error')

        return redirect(url_for('admin.manage_exhibitor_banners'))

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء إضافة البنر: {str(e)}', 'error')
        return redirect(url_for('admin.manage_exhibitor_banners'))

@admin.route('/exhibitor-banner/<int:banner_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exhibitor_banner(banner_id):
    """Delete an exhibitor's banner"""
    banner = ExhibitorBanner.query.get_or_404(banner_id)
    
    try:
        # Delete banner file
        if banner.image_path:
            banner_path = os.path.join('static', banner.image_path.lstrip('/'))
            if os.path.exists(banner_path):
                os.remove(banner_path)
        
        db.session.delete(banner)
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

    time_range = int(request.args.get('timeRange', 30))
    visitor_type = request.args.get('visitorType', 'all')
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=time_range)
    
    # Build query
    query = Visit.query.filter(Visit.timestamp.between(start_date, end_date))
    
    if visitor_type != 'all':
        is_new = visitor_type == 'new'
        query = query.filter(Visit.is_new_visitor == is_new)
    
    # Get visitor trend
    visitor_trend = {}
    for visit in query.all():
        date = visit.timestamp.strftime('%Y-%m-%d')
        visitor_trend[date] = visitor_trend.get(date, 0) + 1
    
    # Get visitor type distribution
    new_visitors = query.filter(Visit.is_new_visitor == True).count()
    returning_visitors = query.filter(Visit.is_new_visitor == False).count()
    
    return jsonify({
        'visitorTrend': visitor_trend,
        'visitorType': {
            'new': new_visitors,
            'returning': returning_visitors
        }
    })
