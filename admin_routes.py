from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from extensions import db
from models import Package, User, Order, Visit, Product, Settings, Specialization, Video, ExhibitorBanner, ExhibitorAnalytics, Partner
from werkzeug.utils import secure_filename
from auth import admin_required
import json
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import os

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
    
    # Search User table directly with role='exhibitor'
    exhibitors = User.query.filter(
        User.role == 'exhibitor',
        or_(
            User.email.ilike(f'%{query}%'),
            User.company_name.ilike(f'%{query}%')
        )
    ).all()
    
    return jsonify([{
        'id': exhibitor.id,
        'company_name': exhibitor.company_name or f"{exhibitor.first_name} {exhibitor.last_name}",
        'email': exhibitor.email
    } for exhibitor in exhibitors])

@admin.route('/add-product', methods=['POST'])
@login_required
@admin_required
def add_product():
    """Add a new product with category synchronization"""
    try:
        # Get user ID from form (representing the exhibitor user)
        user_id = request.form.get('user_id')

        if not user_id:
            flash('يجب اختيار العارض أولاً', 'error')
            return redirect(url_for('admin.manage_products'))

        # Verify exhibitor user exists with role='exhibitor'
        user = User.query.filter_by(id=user_id, role='exhibitor').first()
        if not user:
            flash('العارض المحدد غير موجود أو ليس عارضًا', 'error')
            return redirect(url_for('admin.manage_products'))

        # Get product data from form
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        currency = request.form.get('currency')
        is_featured = bool(request.form.get('is_featured'))
        is_homepage_featured = bool(request.form.get('is_homepage_featured'))

        # Get or create category - use user's specialization if available
        explicit_category = request.form.get('category', '').strip()
        if explicit_category:
            category = explicit_category
        elif user.specialization_id:
            specialization = Specialization.query.get(user.specialization_id)
            category = specialization.name if specialization else "غير محدد"
        else:
            category = "غير محدد"

        # Handle image upload
        image = request.files.get('image')
        image_url = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join('static', 'images', 'products', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)
            # Convert backslashes to forward slashes for web URLs
            image_url = '/' + image_path.replace('\\', '/')

        # Create product - use user.id directly from User table
        product = Product(
            exhibitor_id=user_id,              # Use user ID directly from users table
            name=name,
            description=description,
            price=price,
            currency=currency,
            category=category,
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

@admin.route('/update-product/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def update_product(product_id):
    """Update product details including category synchronization"""
    product = Product.query.get_or_404(product_id)
    
    try:
        # Update basic product info
        product.name = request.form.get('name', product.name)
        product.description = request.form.get('description', product.description)
        product.price = float(request.form.get('price', product.price))
        product.currency = request.form.get('currency', product.currency)
        product.is_featured = bool(request.form.get('is_featured'))
        product.is_homepage_featured = bool(request.form.get('is_homepage_featured'))
        
        # Handle category - use explicit category or keep existing
        explicit_category = request.form.get('category', '').strip()
        if explicit_category:
            product.category = explicit_category
        
        # Handle image update if provided
        image = request.files.get('image')
        if image and image.filename:
            # Validate image file
            if allowed_image_file(image.filename):
                # Delete old image if exists
                if product.image_url:
                    old_image_path = os.path.join('static', product.image_url.lstrip('/'))
                    if os.path.exists(old_image_path):
                        try:
                            os.remove(old_image_path)
                        except OSError:
                            pass  # Ignore if old file doesn't exist
                
                # Save new image
                filename = secure_filename(image.filename)
                image_path = os.path.join('static', 'images', 'products', filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
                # Convert backslashes to forward slashes for web URLs
                product.image_url = '/' + image_path.replace('\\', '/')
            else:
                flash('نوع الصورة غير مدعوم. استخدم: PNG, JPG, JPEG, GIF, WEBP', 'warning')
        
        product.updated_at = datetime.now()
        db.session.commit()
        
        flash('تم تحديث المنتج بنجاح', 'success')
        return redirect(url_for('admin.manage_products'))
        
    except ValueError as ve:
        flash('السعر يجب أن يكون رقمًا صحيحًا', 'error')
        return redirect(url_for('admin.manage_products'))
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء تحديث المنتج: {str(e)}', 'error')
        return redirect(url_for('admin.manage_products'))

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
    # Get exhibitors - all from User table with role='exhibitor'
    exhibitors_list = db.session.query(User)\
        .outerjoin(Package)\
        .filter(User.role == 'exhibitor')\
        .order_by(User.created_at.desc())\
        .all()
    
    # Get analytics data for each exhibitor
    for exhibitor in exhibitors_list:
        # Count products
        exhibitor.product_count = Product.query.filter_by(exhibitor_id=exhibitor.id).count()
        
        # Get package name
        exhibitor.package_name = exhibitor.package.name if exhibitor.package else "لا يوجد باقة"
        
        # Get total visits (analytics)
        exhibitor.total_visits = ExhibitorAnalytics.query\
            .filter_by(exhibitor_id=exhibitor.id)\
            .filter_by(action_type='visit')\
            .count()

        # Get unique visitors count
        exhibitor.unique_visitors = db.session.query(ExhibitorAnalytics.user_id)\
            .filter_by(exhibitor_id=exhibitor.id)\
            .filter_by(action_type='visit')\
            .distinct().count()

    return render_template('admin/exhibitors.html', exhibitors=exhibitors_list)

@admin.route('/exhibitors/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_exhibitor():
    """Add new exhibitor route"""
    # Get all specializations and packages for the dropdowns
    specializations = Specialization.query.order_by(Specialization.name).all()
    packages = Package.query.filter_by(is_active=True).order_by(Package.name).all()
    
    if request.method == 'POST':
        try:
            # Create the User record with all exhibitor data directly in User table
            user = User(
                email=request.form['email'],
                password=generate_password_hash(request.form['password'], method='scrypt'),
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                company_name=request.form['company_name'],
                company_description=request.form['company_description'],
                description=request.form.get('description'),
                specialization_id=request.form.get('specialization_id'),
                package_id=request.form.get('package_id'),
                role='exhibitor',
                is_active='is_active' in request.form,
                phone=request.form.get('phone'),
                country=request.form.get('country'),
                contact_email=request.form.get('contact_email', request.form['email']),
                contact_phone=request.form.get('contact_phone', request.form.get('phone')),
                website=request.form.get('website')
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('تم إضافة العارض بنجاح', 'success')
            return redirect(url_for('admin.exhibitors'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة العارض: {str(e)}', 'danger')
            
    return render_template('admin/exhibitor_form.html', exhibitor=None, specializations=specializations, packages=packages)

@admin.route('/exhibitors/<int:exhibitor_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exhibitor(exhibitor_id):
    """Edit exhibitor route"""
    exhibitor = User.query.filter_by(id=exhibitor_id, role='exhibitor').first_or_404()
    specializations = Specialization.query.order_by(Specialization.name).all()
    
    if request.method == 'POST':
        # Update User information directly
        exhibitor.email = request.form['email']
        if request.form.get('password'):  # Only update password if provided
            exhibitor.password = generate_password_hash(request.form['password'], method='scrypt')
        exhibitor.first_name = request.form['first_name']
        exhibitor.last_name = request.form['last_name']
        exhibitor.company_name = request.form['company_name']
        exhibitor.company_description = request.form['company_description']
        exhibitor.description = request.form.get('description')
        exhibitor.specialization_id = request.form.get('specialization_id')
        exhibitor.is_active = 'is_active' in request.form
        exhibitor.phone = request.form.get('phone')
        exhibitor.contact_email = request.form.get('contact_email', request.form['email'])
        exhibitor.contact_phone = request.form.get('contact_phone', request.form.get('phone'))
        exhibitor.website = request.form.get('website')
        exhibitor.country = request.form.get('country')
        
        try:
            db.session.commit()
            flash('تم تحديث العارض بنجاح', 'success')
            return redirect(url_for('admin.exhibitors'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء تحديث العارض. يرجى المحاولة مرة أخرى.', 'danger')
            
    return render_template('admin/exhibitor_form.html', exhibitor=exhibitor, specializations=specializations)

@admin.route('/exhibitors/<int:exhibitor_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exhibitor(exhibitor_id):
    """Delete exhibitor route"""
    exhibitor = User.query.filter_by(id=exhibitor_id, role='exhibitor').first_or_404()
    
    try:
        # Delete the User directly (all data is now in User table)
        db.session.delete(exhibitor)
        db.session.commit()
        flash('تم حذف العارض بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء حذف العارض. يرجى المحاولة مرة أخرى.', 'danger')
    
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
    try:
        total_visits = Visit.query.count()
        unique_visitors = db.session.query(Visit.visitor_id).distinct().count()
        
        # Get visit trend data
        visits_by_date = db.session.query(
            db.func.date(Visit.timestamp).label('date'),
            db.func.count(Visit.id).label('count')
        ).group_by(db.func.date(Visit.timestamp)).all()
        
        return jsonify({
            'total_visits': total_visits,
            'unique_visitors': unique_visitors,
            'visits_by_date': [{'date': str(v.date), 'count': v.count} for v in visits_by_date]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    try:
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
        flash('تم تحديث إعدادات المعرض بنجاح', 'success')
        return redirect(url_for('admin.settings'))
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'error')
        return redirect(url_for('admin.settings'))

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
        # Get user ID from form (representing the exhibitor user)
        user_id = request.form.get('user_id')
        if not user_id:
            flash('يجب اختيار العارض أولاً', 'error')
            return redirect(url_for('admin.manage_videos'))

        # Verify exhibitor user exists with role='exhibitor'
        user = User.query.filter_by(id=user_id, role='exhibitor').first()
        if not user:
            flash('العارض المحدد غير موجود أو ليس عارضاً', 'error')
            return redirect(url_for('admin.manage_videos'))

        # Get video details
        title = request.form.get('title')
        description = request.form.get('description')
        is_active = 'is_active' in request.form

        # Handle video file upload
        video_file = request.files.get('video')
        video_url = None
        if video_file and allowed_video_file(video_file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video_file.filename}")
            video_path = os.path.join(VIDEOS_UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            video_file.save(video_path)
            # Convert backslashes to forward slashes for web URLs
            video_url = '/' + video_path.replace('\\', '/')

        # Create new video record with user_id directly from users table
        video = Video(
            exhibitor_id=user_id,  # Use user_id directly from User table
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
            # Convert backslashes to forward slashes for web URLs
            video.video_url = '/' + video_path.replace('\\', '/')

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

# Exhibitor Banner Management Routes
@admin.route('/exhibitor-banners')
@login_required
@admin_required
def manage_exhibitor_banners():
    """Exhibitor banner management page"""
    # Query User objects directly with role='exhibitor' 
    exhibitors = User.query.filter_by(role='exhibitor').order_by(User.company_name).all()
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
        # Get user ID from form (representing the exhibitor user)
        user_id = request.form.get('exhibitor_id')
        title = request.form.get('title')
        
        if not user_id:
            flash('يجب اختيار العارض أولاً', 'error')
            return redirect(url_for('admin.manage_exhibitor_banners'))

        # Verify exhibitor user exists with role='exhibitor'
        user = User.query.filter_by(id=user_id, role='exhibitor').first()
        if not user:
            flash('العارض المحدد غير موجود أو ليس عارضاً', 'error')
            return redirect(url_for('admin.manage_exhibitor_banners'))

        # Handle banner file upload
        banner = request.files.get('banner')
        if banner and allowed_image_file(banner.filename):
            # Save new banner
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{banner.filename}")
            banner_path = os.path.join(BANNERS_UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(banner_path), exist_ok=True)
            banner.save(banner_path)
            
            # Convert backslashes to forward slashes for web URLs
            image_url = '/' + banner_path.replace('\\', '/')
            
            # Create new banner record with user_id directly from users table
            new_banner = ExhibitorBanner(
                exhibitor_id=user_id,  # Use user_id directly from User table
                title=title,
                image_path=image_url,
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

@admin.route('/exhibitor-banner/<int:banner_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_exhibitor_banner_status(banner_id):
    """Toggle the status of an exhibitor's banner"""
    try:
        banner = ExhibitorBanner.query.get_or_404(banner_id)
        data = request.get_json()
        banner.is_active = data.get('is_active', False)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/visitor-data-filter')
@login_required
@admin_required
def get_visitor_data_filter():
    """API endpoint for filtered visitor data"""
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


@admin.route('/partners')
@login_required
@admin_required
def manage_partners():
    """Admin partner management page"""
    partners = Partner.query.order_by(Partner.display_order, Partner.created_at.desc()).all()
    return render_template('admin/partners.html', partners=partners)

@admin.route('/partners/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_partner():
    """Add new partner route"""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            website_url = request.form.get('website_url')
            display_order = int(request.form.get('display_order', 0))
            is_active = 'is_active' in request.form

            # Handle image file upload
            image = request.files.get('image')
            image_url = None
            if image and allowed_image_file(image.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                image_path = os.path.join('static', 'images', 'partner', filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
                # Convert backslashes to forward slashes for web URLs
                image_url = '/' + image_path.replace('\\', '/')
            else:
                flash('يرجى اختيار ملف صورة صالح', 'error')
                return render_template('admin/partner_form.html', partner=None)

            # Create new partner
            partner = Partner(
                name=name,
                description=description,
                image_path=image_url,
                website_url=website_url,
                display_order=display_order,
                is_active=is_active
            )

            db.session.add(partner)
            db.session.commit()

            flash('تم إضافة الراعي بنجاح', 'success')
            return redirect(url_for('admin.manage_partners'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة الراعي: {str(e)}', 'error')
            return render_template('admin/partner_form.html', partner=None)
            
    return render_template('admin/partner_form.html', partner=None)

@admin.route('/partners/<int:partner_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_partner(partner_id):
    """Edit partner route"""
    partner = Partner.query.get_or_404(partner_id)
    
    if request.method == 'POST':
        try:
            partner.name = request.form.get('name')
            partner.description = request.form.get('description')
            partner.website_url = request.form.get('website_url')
            partner.display_order = int(request.form.get('display_order', 0))
            partner.is_active = 'is_active' in request.form

            # Handle new image file if provided
            image = request.files.get('image')
            if image and allowed_image_file(image.filename):
                # Delete old image if exists
                if partner.image_path:
                    old_image_path = os.path.join('static', partner.image_path.lstrip('/'))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                # Save new image
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                image_path = os.path.join('static', 'images', 'partner', filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
                # Convert backslashes to forward slashes for web URLs
                partner.image_path = '/' + image_path.replace('\\', '/')

            db.session.commit()
            flash('تم تحديث الراعي بنجاح', 'success')
            return redirect(url_for('admin.manage_partners'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث الراعي: {str(e)}', 'error')

    return render_template('admin/partner_form.html', partner=partner)

@admin.route('/partners/<int:partner_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_partner(partner_id):
    """Delete partner route"""
    partner = Partner.query.get_or_404(partner_id)
    
    try:
        # Delete partner image
        if partner.image_path:
            image_path = os.path.join('static', partner.image_path.lstrip('/'))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(partner)
        db.session.commit()
        flash('تم حذف الراعي بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف الراعي: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_partners'))

