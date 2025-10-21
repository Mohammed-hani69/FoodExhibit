from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db, Specialization, Package
from functools import wraps

auth = Blueprint('auth', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if user.is_active:
                login_user(user)
                if user.role == 'exhibitor':
                    return redirect(url_for('exhibitor.dashboard'))
                elif user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Your account is not active. Please contact admin.', 'error')
        else:
            flash('Please check your login details and try again.', 'error')
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    specializations = Specialization.query.all()
    packages = Package.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        phone = request.form.get('phone')
        package_id = request.form.get('package_id')
        country = request.form.get('country')  # ✅ أضفنا هذا السطر

        # التحقق أن البلد تم إدخاله
        if not country:
            flash('Please select your country.', 'error')
            return render_template('auth/register.html', specializations=specializations, packages=packages)

        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', 'error')
            return redirect(url_for('auth.register'))
        
        # Only require package selection for exhibitors
        if role == 'exhibitor':
            if not package_id:
                flash('Please select a package to continue.', 'error')
                return render_template('auth/register.html', specializations=specializations, packages=packages)
            
            # Verify package exists and is active
            package = Package.query.get(package_id)
            if not package or not package.is_active:
                flash('Selected package is not available. Please choose another package.', 'error')
                return render_template('auth/register.html', specializations=specializations, packages=packages)

        # ✅ أضف country في إنشاء المستخدم
        new_user = User(
            email=email,
            password=generate_password_hash(password, method='scrypt'),
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone=phone,
            country=country,
            package_id=package_id if role == 'exhibitor' else None
        )
        
        if role == 'exhibitor':
            company_name = request.form.get('company_name')
            specialization_id = request.form.get('specialization_id')
            if not company_name or not specialization_id:
                flash('Company name and specialization are required for exhibitors', 'error')
                return redirect(url_for('auth.register'))
            
            new_user.company_name = company_name
            new_user.specialization_id = specialization_id
            new_user.is_active = False  # Exhibitors need admin approval
            
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'exhibitor':
            flash('Registration successful! Please wait for admin approval.', 'success')
        else:
            flash('Registration successful! Please login.', 'success')
            
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', specializations=specializations, packages=packages)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
