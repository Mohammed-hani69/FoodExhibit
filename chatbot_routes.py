"""
Chatbot Routes for AI-powered chat integration
مسارات الشات بوت الذكي
"""

from flask import Blueprint, request, jsonify, session, current_app, render_template
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models import ChatMessage, User, Specialization, Package
from werkzeug.security import generate_password_hash
import logging
from ai_chatbot import get_chatbot, handle_user_registration, validate_registration_data, detect_language

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')

# Store conversation contexts per user
conversation_contexts = {}
# Store registration state per user session
registration_state = {}
# Store message drafts per user
message_drafts = {}


@chatbot_bp.route('/', methods=['GET'])
def chatbot_page():
    """Main chatbot page - shows language selection first"""
    try:
        return render_template('ai_chatbot.html', current_language=session.get('language', 'ar'))
    except Exception as e:
        logger.error(f"Error loading chatbot page: {str(e)}")
        return render_template('ai_chatbot.html', current_language=session.get('language', 'ar'))


@chatbot_bp.route('/chat', methods=['POST'])
def chat_with_bot():
    """
    Main endpoint for chatting with AI chatbot
    Auto-detects language from user message
    Handles registration requests, account status, and email creation
    
    Request JSON:
    {
        "message": "user message in any language",
        "conversation_id": "optional - for persistent conversations"
    }
    
    Response will be in the same language as the user's message
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No message provided'
            }), 400
        
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', None)
        
        if not user_message:
            return jsonify({
                'status': 'error',
                'message': 'Empty message'
            }), 400
        
        # Get user ID (anonymous if not logged in)
        user_id = current_user.id if current_user.is_authenticated else None
        
        # Get session ID for registration tracking
        session_id = session.get('id', request.remote_addr)
        
        # Initialize registration state for this session if needed
        if session_id not in registration_state:
            registration_state[session_id] = {}
        
        user_state = registration_state[session_id]
        
        try:
            # 1️⃣ Check if user wants to register
            from ai_chatbot import detect_account_status_request, detect_email_request
            
            reg_check = handle_user_registration(user_message, user_id)
            
            if reg_check['action'] == 'start_registration':
                # Start registration flow
                user_state['registering'] = True
                user_state['step'] = 'email'
                user_state['data'] = {}
                user_state['language'] = reg_check['language']
                
                return jsonify({
                    'status': 'success',
                    'response': reg_check['message'],
                    'registration_mode': True,
                    'current_step': 'email',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            # 2️⃣ Check if user wants to check account status
            elif detect_account_status_request(user_message):
                language = detect_language(user_message)
                
                if language == 'ar':
                    ask_msg = 'لأتحقق من حالة حسابك، أحتاج إلى بريدك الإلكتروني. ما هو بريدك؟'
                else:
                    ask_msg = 'To check your account status, I need your email address. What is your email?'
                
                user_state['checking_status'] = True
                user_state['status_language'] = language
                
                return jsonify({
                    'status': 'success',
                    'response': ask_msg,
                    'checking_status': True,
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            # 3️⃣ Check if we're in status check mode
            elif user_state.get('checking_status') == True:
                language = user_state.get('status_language', 'ar')
                email = user_message.strip().lower()
                
                # Call the account status endpoint
                status_response = check_account_status_internal(email, language)
                
                # Clean up status check mode
                user_state['checking_status'] = False
                
                return status_response
            
            # 4️⃣ Check if user wants to create a company email
            elif detect_email_request(user_message):
                language = detect_language(user_message)
                
                if language == 'ar':
                    ask_msg = 'حسناً! لإنشاء رسالة بريدية للشركة، أحتاج إلى:\n\n1️⃣ بريدك الإلكتروني (عنوان البريد المسجل)\n\nما هو بريدك؟'
                else:
                    ask_msg = 'Great! To create a company email, I need:\n\n1️⃣ Your email address (registered email)\n\nWhat is your email?'
                
                user_state['creating_email'] = True
                user_state['email_language'] = language
                user_state['email_data'] = {}
                user_state['email_step'] = 'email'
                
                return jsonify({
                    'status': 'success',
                    'response': ask_msg,
                    'creating_email': True,
                    'email_step': 'email',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            # 5️⃣ Check if we're in email creation mode
            elif user_state.get('creating_email') == True:
                return handle_email_creation(user_message, session_id, user_state)
            
            # 6️⃣ Check if we're in registration mode
            elif user_state.get('registering') == True:
                return handle_registration_input(user_message, session_id, user_state)
            
            # 7️⃣ Normal chat mode
            else:
                # Get chatbot instance
                chatbot = get_chatbot()
                
                # Get or initialize user conversation context
                context_key = f"user_{user_id}_{conversation_id or 'default'}"
                
                # Get response from AI (language will be auto-detected)
                response = chatbot.get_response(user_message, user_id=user_id)
                
                # Save conversation to database if user is logged in
                if user_id and response['success']:
                    try:
                        # Save user message
                        user_msg = ChatMessage(
                            sender_id=user_id,
                            receiver_id=None,  # Null for bot messages
                            message=user_message,
                            timestamp=datetime.now(),
                            is_read=False
                        )
                        db.session.add(user_msg)
                        
                        # Save bot response
                        bot_msg = ChatMessage(
                            sender_id=None,  # Null for bot
                            receiver_id=user_id,
                            message=response['response'],
                            timestamp=datetime.now(),
                            is_read=True  # Bot messages are already "read"
                        )
                        db.session.add(bot_msg)
                        db.session.commit()
                        
                    except Exception as db_error:
                        logger.error(f"Error saving chat message: {str(db_error)}")
                        db.session.rollback()
                        # Continue even if save fails
                
                return jsonify({
                    'status': 'success',
                    'response': response.get('response'),
                    'provider': response.get('provider'),
                    'timestamp': response.get('timestamp'),
                    'user_id': user_id
                }), 200
            
        except Exception as ai_error:
            logger.error(f"AI Chatbot error: {str(ai_error)}")
            return jsonify({
                'status': 'error',
                'message': f"خطأ في خدمة الشات بوت: {str(ai_error)}",
                'error': str(ai_error)
            }), 500
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ غير متوقع',
            'error': str(e)
        }), 500


def handle_registration_input(user_message: str, session_id: str, user_state: dict):
    """
    Handle user input during registration process
    Guides user through each step and creates account when complete
    """
    try:
        current_step = user_state.get('step')
        reg_data = user_state.get('data', {})
        language = user_state.get('language', 'ar')
        
        messages_ar = {
            'email': 'ما هو عنوان بريدك الإلكتروني؟',
            'first_name': 'ما هو اسمك الأول؟',
            'last_name': 'ما هو اسمك الأخير؟',
            'password': 'اختر كلمة مرور آمنة (6 أحرف على الأقل):',
            'phone': 'ما هو رقم هاتفك؟ (اختياري - اترك فارغاً لتخطي)',
            'country': 'ما هي دولتك؟',
            'role': 'هل تريد التسجيل كـ: (اكتب: عارض أو مستخدم عادي)',
            'confirm': 'هل تريد إكمال التسجيل بهذه البيانات؟ (نعم/لا)'
        }
        
        messages_en = {
            'email': 'What is your email address?',
            'first_name': 'What is your first name?',
            'last_name': 'What is your last name?',
            'password': 'Choose a secure password (at least 6 characters):',
            'phone': 'What is your phone number? (Optional - leave empty to skip)',
            'country': 'What is your country?',
            'role': 'Do you want to register as: (type: exhibitor or user)',
            'confirm': 'Do you want to complete registration with this data? (yes/no)'
        }
        
        messages = messages_ar if language == 'ar' else messages_en
        
        # Handle email step
        if current_step == 'email':
            # Validate email
            if '@' not in user_message:
                msg = 'البريد الإلكتروني غير صحيح. يرجى إدخال بريد صحيح:' if language == 'ar' else 'Invalid email. Please enter a valid email:'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'email',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=user_message.lower()).first()
            if existing_user:
                msg = 'هذا البريد الإلكتروني مسجل بالفعل!' if language == 'ar' else 'This email is already registered!'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'email',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['email'] = user_message.lower()
            user_state['data'] = reg_data
            user_state['step'] = 'first_name'
            
            return jsonify({
                'status': 'success',
                'response': messages.get('first_name', messages_ar['first_name']),
                'registration_mode': True,
                'current_step': 'first_name',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle first name step
        elif current_step == 'first_name':
            if len(user_message.strip()) < 2:
                msg = 'الاسم قصير جداً. حاول مرة أخرى:' if language == 'ar' else 'Name is too short. Try again:'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'first_name',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['first_name'] = user_message.strip()
            user_state['data'] = reg_data
            user_state['step'] = 'last_name'
            
            return jsonify({
                'status': 'success',
                'response': messages.get('last_name', messages_ar['last_name']),
                'registration_mode': True,
                'current_step': 'last_name',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle last name step
        elif current_step == 'last_name':
            if len(user_message.strip()) < 2:
                msg = 'الاسم قصير جداً. حاول مرة أخرى:' if language == 'ar' else 'Name is too short. Try again:'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'last_name',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['last_name'] = user_message.strip()
            user_state['data'] = reg_data
            user_state['step'] = 'password'
            
            return jsonify({
                'status': 'success',
                'response': messages.get('password', messages_ar['password']),
                'registration_mode': True,
                'current_step': 'password',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle password step
        elif current_step == 'password':
            if len(user_message) < 6:
                msg = 'كلمة المرور قصيرة جداً (6 أحرف على الأقل):' if language == 'ar' else 'Password is too short (at least 6 characters):'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'password',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['password'] = user_message
            user_state['data'] = reg_data
            user_state['step'] = 'phone'
            
            return jsonify({
                'status': 'success',
                'response': messages.get('phone', messages_ar['phone']),
                'registration_mode': True,
                'current_step': 'phone',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle phone step (optional)
        elif current_step == 'phone':
            if user_message.strip().lower() in ['skip', 'تخطي', 'لا', 'no', '']:
                reg_data['phone'] = ''
            else:
                reg_data['phone'] = user_message.strip()
            
            user_state['data'] = reg_data
            user_state['step'] = 'country'
            
            return jsonify({
                'status': 'success',
                'response': messages.get('country', messages_ar['country']),
                'registration_mode': True,
                'current_step': 'country',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle country step
        elif current_step == 'country':
            if len(user_message.strip()) < 2:
                msg = 'الدولة غير صحيحة. حاول مرة أخرى:' if language == 'ar' else 'Invalid country. Try again:'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'country',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['country'] = user_message.strip()
            user_state['data'] = reg_data
            user_state['step'] = 'role'
            
            return jsonify({
                'status': 'success',
                'response': messages.get('role', messages_ar['role']),
                'registration_mode': True,
                'current_step': 'role',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle role step
        elif current_step == 'role':
            user_input = user_message.strip().lower()
            
            if language == 'ar':
                if 'عارض' in user_input or 'exhibitor' in user_input:
                    reg_data['role'] = 'exhibitor'
                elif 'مستخدم' in user_input or 'user' in user_input:
                    reg_data['role'] = 'user'
                else:
                    msg = 'الخيار غير صحيح. اكتب: عارض أو مستخدم عادي'
                    return jsonify({
                        'status': 'success',
                        'response': msg,
                        'registration_mode': True,
                        'current_step': 'role',
                        'timestamp': datetime.now().isoformat()
                    }), 200
            else:
                if 'exhibitor' in user_input:
                    reg_data['role'] = 'exhibitor'
                elif 'user' in user_input:
                    reg_data['role'] = 'user'
                else:
                    msg = 'Invalid option. Type: exhibitor or user'
                    return jsonify({
                        'status': 'success',
                        'response': msg,
                        'registration_mode': True,
                        'current_step': 'role',
                        'timestamp': datetime.now().isoformat()
                    }), 200
            
            user_state['data'] = reg_data
            
            # If exhibitor, ask for company name
            if reg_data['role'] == 'exhibitor':
                user_state['step'] = 'company_name'
                msg = 'رائع! الآن سأطلب منك معلومات الشركة.\n\nما هو اسم شركتك؟' if language == 'ar' else 'Great! Now I need your company information.\n\nWhat is your company name?'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'company_name',
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                # Regular user - skip to confirm
                user_state['step'] = 'confirm'
                summary = format_registration_summary(reg_data, language)
                confirm_msg = 'هل تريد إكمال التسجيل بهذه البيانات؟ (نعم/لا)' if language == 'ar' else 'Do you want to complete registration with this data? (yes/no)'
                full_msg = summary + '\n\n' + confirm_msg
                
                return jsonify({
                    'status': 'success',
                    'response': full_msg,
                    'registration_mode': True,
                    'current_step': 'confirm',
                    'timestamp': datetime.now().isoformat()
                }), 200
        
        # Handle company name step
        elif current_step == 'company_name':
            if len(user_message.strip()) < 2:
                msg = 'اسم الشركة قصير جداً. حاول مرة أخرى:' if language == 'ar' else 'Company name is too short. Try again:'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'company_name',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['company_name'] = user_message.strip()
            user_state['data'] = reg_data
            user_state['step'] = 'specialization'
            
            # Get specializations from database
            specs = Specialization.query.all()
            spec_list = '\n'.join([f"{i+1}. {spec.name}" for i, spec in enumerate(specs)])
            
            if language == 'ar':
                msg = f'ممتاز! الآن ما هو تخصص شركتك؟\n\n{spec_list}\n\nاكتب رقم التخصص:'
            else:
                msg = f'Excellent! What is your company specialization?\n\n{spec_list}\n\nType the specialization number:'
            
            user_state['specializations'] = {str(i): spec.id for i, spec in enumerate(specs)}
            
            return jsonify({
                'status': 'success',
                'response': msg,
                'registration_mode': True,
                'current_step': 'specialization',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle specialization step
        elif current_step == 'specialization':
            user_input = user_message.strip()
            specs = Specialization.query.all()
            
            # Try to find by number or name
            spec_id = None
            
            # Check if it's a number
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(specs):
                    spec_id = specs[idx].id
            
            # Check if it matches a name
            if not spec_id:
                for spec in specs:
                    if user_input.lower() in spec.name.lower() or spec.name.lower() in user_input.lower():
                        spec_id = spec.id
                        break
            
            if not spec_id:
                spec_list = '\n'.join([f"{i+1}. {spec.name}" for i, spec in enumerate(specs)])
                msg = f'التخصص غير صحيح. الرجاء الاختيار من القائمة:\n\n{spec_list}\n\nاكتب رقم التخصص:' if language == 'ar' else f'Invalid specialization. Please select from the list:\n\n{spec_list}\n\nType the number:'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'specialization',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['specialization_id'] = spec_id
            user_state['data'] = reg_data
            user_state['step'] = 'package'
            
            # Get active packages
            packages = Package.query.filter_by(is_active=True).all()
            pkg_list = '\n'.join([f"{i+1}. {pkg.name} - {pkg.price} ({pkg.description[:30]}...)" for i, pkg in enumerate(packages)])
            
            if language == 'ar':
                msg = f'ممتاز! الآن ما هي الباقة المفضلة لديك؟\n\n{pkg_list}\n\nاكتب رقم الباقة:'
            else:
                msg = f'Great! Which package would you like?\n\n{pkg_list}\n\nType the package number:'
            
            user_state['packages'] = {str(i): pkg.id for i, pkg in enumerate(packages)}
            
            return jsonify({
                'status': 'success',
                'response': msg,
                'registration_mode': True,
                'current_step': 'package',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle package selection step
        elif current_step == 'package':
            user_input = user_message.strip()
            packages = Package.query.filter_by(is_active=True).all()
            
            package_id = None
            
            # Check if it's a number
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(packages):
                    package_id = packages[idx].id
            
            # Check if it matches a name
            if not package_id:
                for pkg in packages:
                    if user_input.lower() in pkg.name.lower() or pkg.name.lower() in user_input.lower():
                        package_id = pkg.id
                        break
            
            if not package_id:
                pkg_list = '\n'.join([f"{i+1}. {pkg.name} - {pkg.price}" for i, pkg in enumerate(packages)])
                msg = f'الباقة غير صحيحة. الرجاء الاختيار من القائمة:\n\n{pkg_list}\n\nاكتب رقم الباقة:' if language == 'ar' else f'Invalid package. Please select from the list:\n\n{pkg_list}\n\nType the number:'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': True,
                    'current_step': 'package',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            reg_data['package_id'] = package_id
            user_state['data'] = reg_data
            user_state['step'] = 'confirm'
            
            # Show complete summary
            summary = format_exhibitor_summary(reg_data, language)
            confirm_msg = 'هل تريد إكمال التسجيل بهذه البيانات؟ (نعم/لا)' if language == 'ar' else 'Do you want to complete registration with this data? (yes/no)'
            full_msg = summary + '\n\n' + confirm_msg
            
            return jsonify({
                'status': 'success',
                'response': full_msg,
                'registration_mode': True,
                'current_step': 'confirm',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Handle confirmation step
        elif current_step == 'confirm':
            user_input = user_message.strip().lower()
            
            if language == 'ar':
                is_confirmed = user_input in ['نعم', 'yes', 'ok', 'حسناً', 'نعم اكمل', 'نعم تمام']
            else:
                is_confirmed = user_input in ['yes', 'نعم', 'ok', 'sure', 'yes please']
            
            if is_confirmed:
                # Create the account
                return create_account_from_registration(reg_data, session_id, language)
            else:
                # Cancel registration
                user_state['registering'] = False
                user_state['data'] = {}
                user_state['step'] = None
                
                msg = 'تم إلغاء عملية التسجيل. كيف يمكنني مساعدتك الآن؟' if language == 'ar' else 'Registration cancelled. How can I help you now?'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'registration_mode': False,
                    'timestamp': datetime.now().isoformat()
                }), 200
    
    except Exception as e:
        logger.error(f"Error handling registration input: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


def format_registration_summary(data: dict, language: str) -> str:
    """Format registration data summary"""
    if language == 'ar':
        return f"""
📋 **ملخص البيانات:**
- البريد الإلكتروني: {data.get('email')}
- الاسم الأول: {data.get('first_name')}
- الاسم الأخير: {data.get('last_name')}
- الهاتف: {data.get('phone', 'لم يتم تحديده')}
- الدولة: {data.get('country')}
- نوع الحساب: {'عارض' if data.get('role') == 'exhibitor' else 'مستخدم عادي'}
"""
    else:
        return f"""
📋 **Data Summary:**
- Email: {data.get('email')}
- First Name: {data.get('first_name')}
- Last Name: {data.get('last_name')}
- Phone: {data.get('phone', 'Not set')}
- Country: {data.get('country')}
- Account Type: {'Exhibitor' if data.get('role') == 'exhibitor' else 'Regular User'}
"""


def check_account_status_internal(email: str, language: str):
    """
    Check if exhibitor account is activated
    Internal helper function
    """
    try:
        if not email or '@' not in email:
            msg = 'البريد الإلكتروني غير صحيح!' if language == 'ar' else 'Invalid email address!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user:
            msg = 'البريد الإلكتروني غير مسجل في النظام!' if language == 'ar' else 'Email not found in the system!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'found': False,
                'timestamp': datetime.now().isoformat()
            }), 404
        
        if user.role != 'exhibitor':
            msg = 'هذا الحساب ليس حساب عارض!' if language == 'ar' else 'This account is not an exhibitor account!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'is_exhibitor': False,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if user.is_active:
            pkg_name = user.package.name if user.package else 'N/A'
            if language == 'ar':
                response_msg = f"""✅ **تم تفعيل حسابك بنجاح!**

مرحباً {user.first_name}،

🏢 **معلومات حسابك:**
- الشركة: {user.company_name}
- الباقة: {pkg_name}
- الحالة: ✅ مفعل وجاهز للاستخدام

يمكنك الآن تسجيل الدخول واستخدام جميع ميزات المنصة."""
            else:
                response_msg = f"""✅ **Your Account Has Been Activated!**

Hello {user.first_name},

🏢 **Account Information:**
- Company: {user.company_name}
- Package: {pkg_name}
- Status: ✅ Active and Ready to Use

You can now log in and use all platform features."""
            
            return jsonify({
                'status': 'success',
                'response': response_msg,
                'account_active': True,
                'company_name': user.company_name,
                'package_name': pkg_name,
                'timestamp': datetime.now().isoformat()
            }), 200
        
        else:
            if language == 'ar':
                response_msg = f"""⏳ **حسابك في انتظار الموافقة**

مرحباً {user.first_name}،

🏢 **معلومات حسابك:**
- الشركة: {user.company_name}
- الباقة: {user.package.name if user.package else 'N/A'}
- الحالة: ⏳ قيد المراجعة

فريق الإدارة يقوم حالياً بمراجعة طلبك. 
سيتم إرسال بريد إلكتروني لتأكيد التفعيل عندما يتم الموافقة عليه."""
            else:
                response_msg = f"""⏳ **Your Account is Pending Approval**

Hello {user.first_name},

🏢 **Account Information:**
- Company: {user.company_name}
- Package: {user.package.name if user.package else 'N/A'}
- Status: ⏳ Under Review

The admin team is currently reviewing your request.
You will receive a confirmation email once your account is activated."""
            
            return jsonify({
                'status': 'success',
                'response': response_msg,
                'account_active': False,
                'company_name': user.company_name,
                'timestamp': datetime.now().isoformat()
            }), 200
        
    except Exception as e:
        logger.error(f"Error checking account status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


def handle_email_creation(user_message: str, session_id: str, user_state: dict):
    """
    معالجة عملية إنشاء رسالة بريدية للشركة
    Handle company email creation process - AI generates the content
    """
    try:
        from ai_chatbot import generate_company_email
        
        language = user_state.get('email_language', 'ar')
        email_step = user_state.get('email_step', 'email')
        email_data = user_state.get('email_data', {})
        
        # الخطوة 1: البريد الإلكتروني
        if email_step == 'email':
            email = user_message.strip().lower()
            
            if not email or '@' not in email:
                msg = 'البريد الإلكتروني غير صحيح!' if language == 'ar' else 'Invalid email address!'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'creating_email': True,
                    'email_step': 'email',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            # التحقق من أن البريد خاص بعارض
            user = User.query.filter_by(email=email).first()
            if not user or user.role != 'exhibitor':
                msg = 'هذا البريد الإلكتروني ليس خاص بعارض!' if language == 'ar' else 'This email is not registered as an exhibitor!'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'creating_email': True,
                    'email_step': 'email',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            email_data['email'] = email
            email_data['company_name'] = user.company_name
            user_state['email_data'] = email_data
            user_state['email_step'] = 'subject'
            
            msg = 'ممتاز! الآن ما هو موضوع الرسالة؟' if language == 'ar' else 'Great! What is the subject of the email?'
            return jsonify({
                'status': 'success',
                'response': msg,
                'creating_email': True,
                'email_step': 'subject',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # الخطوة 2: الموضوع
        elif email_step == 'subject':
            if len(user_message.strip()) < 3:
                msg = 'الموضوع قصير جداً!' if language == 'ar' else 'Subject is too short!'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'creating_email': True,
                    'email_step': 'subject',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            email_data['subject'] = user_message.strip()
            user_state['email_data'] = email_data
            user_state['email_step'] = 'generating'
            
            # توليد محتوى الرسالة باستخدام الذكاء الاصطناعي
            generating_msg = 'جاري توليد محتوى الرسالة باستخدام الذكاء الاصطناعي...' if language == 'ar' else 'Generating email content using AI...'
            
            return jsonify({
                'status': 'success',
                'response': generating_msg,
                'creating_email': True,
                'email_step': 'generating',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # الخطوة 3: توليد المحتوى
        elif email_step == 'generating':
            # توليد محتوى الرسالة
            subject = email_data['subject']
            company_name = email_data['company_name']
            
            email_body = generate_company_email(subject, company_name, language)
            
            email_data['body'] = email_body
            user_state['email_data'] = email_data
            user_state['email_step'] = 'confirm'
            
            # عرض الرسالة المولدة
            if language == 'ar':
                preview = f"""📧 **الرسالة المولدة بواسطة الذكاء الاصطناعي:**

إلى: {email_data['company_name']} ({email_data['email']})
الموضوع: {email_data['subject']}

المحتوى:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
{email_body}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

هل تريد قبول هذه الرسالة؟ (نعم/لا)
أم تريد تعديل الموضوع وإعادة التوليد؟ (اكتب: عدّل)"""
            else:
                preview = f"""📧 **AI-Generated Email:**

To: {email_data['company_name']} ({email_data['email']})
Subject: {email_data['subject']}

Body:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
{email_body}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do you want to accept this email? (yes/no)
Or do you want to modify the subject and regenerate? (type: edit)"""
            
            return jsonify({
                'status': 'success',
                'response': preview,
                'creating_email': True,
                'email_step': 'confirm',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # الخطوة 4: التأكيد
        elif email_step == 'confirm':
            user_input = user_message.strip().lower()
            
            if language == 'ar':
                is_confirmed = user_input in ['نعم', 'yes', 'ok', 'حسناً', 'نعم اكمل', 'تمام']
                is_edit = user_input in ['عدل', 'edit', 'غير', 'modify', 'تعديل']
            else:
                is_confirmed = user_input in ['yes', 'نعم', 'ok', 'sure', 'yes please', 'accept']
                is_edit = user_input in ['edit', 'عدل', 'modify', 'change', 'redo']
            
            if is_confirmed:
                # إنشاء الرسالة
                message_id = f"email_{email_data['email']}_{int(datetime.now().timestamp())}"
                email_draft = {
                    'to': email_data['email'],
                    'company_name': email_data['company_name'],
                    'subject': email_data['subject'],
                    'body': email_data['body'],
                    'created_at': datetime.now().isoformat(),
                    'from_chatbot': True,
                    'generated_by_ai': True,
                    'status': 'draft'
                }
                
                message_drafts[message_id] = email_draft
                
                # رسالة النجاح
                if language == 'ar':
                    success_msg = f"""✅ **تم إنشاء الرسالة البريدية بنجاح!**

📧 **بيانات الرسالة:**
- إلى: {email_data['company_name']} ({email_data['email']})
- الموضوع: {email_data['subject']}
- نوع المحتوى: 🤖 تم توليده بواسطة الذكاء الاصطناعي

📝 **محتوى الرسالة:**
{email_data['body']}

---

📌 **التعليمات:**
1. نسخ محتوى الرسالة أعلاه
2. افتح بريدك الإلكتروني
3. أرسل الرسالة إلى: support@foodexhibit.com

معرف الرسالة: `{message_id}`
"""
                else:
                    success_msg = f"""✅ **Email Created Successfully!**

📧 **Email Details:**
- To: {email_data['company_name']} ({email_data['email']})
- Subject: {email_data['subject']}
- Content Type: 🤖 AI Generated

📝 **Email Body:**
{email_data['body']}

---

📌 **Instructions:**
1. Copy the email content above
2. Open your email client
3. Send to: support@foodexhibit.com

Message ID: `{message_id}`
"""
                
                # تنظيف الحالة
                user_state['creating_email'] = False
                user_state['email_data'] = {}
                user_state['email_step'] = None
                
                return jsonify({
                    'status': 'success',
                    'response': success_msg,
                    'message_created': True,
                    'message_id': message_id,
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            elif is_edit:
                # العودة لخطوة الموضوع للتعديل
                user_state['email_step'] = 'subject'
                
                msg = 'تمام! ما هو الموضوع الجديد للرسالة؟' if language == 'ar' else 'What is the new subject for the email?'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'creating_email': True,
                    'email_step': 'subject',
                    'timestamp': datetime.now().isoformat()
                }), 200
            
            else:
                # إلغاء عملية الإنشاء
                user_state['creating_email'] = False
                user_state['email_data'] = {}
                user_state['email_step'] = None
                
                msg = 'تم إلغاء عملية إنشاء الرسالة. كيف يمكنني مساعدتك؟' if language == 'ar' else 'Email creation cancelled. How can I help you?'
                return jsonify({
                    'status': 'success',
                    'response': msg,
                    'creating_email': False,
                    'timestamp': datetime.now().isoformat()
                }), 200
    
    except Exception as e:
        logger.error(f"Error handling email creation: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


def format_exhibitor_summary(data: dict, language: str) -> str:
    """Format exhibitor registration data with company details"""
    
    # Get specialization and package names
    spec_name = "N/A"
    if data.get('specialization_id'):
        spec = Specialization.query.get(data['specialization_id'])
        spec_name = spec.name if spec else "N/A"
    
    pkg_name = "N/A"
    if data.get('package_id'):
        pkg = Package.query.get(data['package_id'])
        pkg_name = f"{pkg.name} ({pkg.price})" if pkg else "N/A"
    
    if language == 'ar':
        return f"""
📋 **ملخص بيانات العارض:**

👤 **البيانات الشخصية:**
- البريد الإلكتروني: {data.get('email')}
- الاسم الأول: {data.get('first_name')}
- الاسم الأخير: {data.get('last_name')}
- الهاتف: {data.get('phone', 'لم يتم تحديده')}
- الدولة: {data.get('country')}

🏢 **بيانات الشركة:**
- اسم الشركة: {data.get('company_name')}
- التخصص: {spec_name}
- الباقة المختارة: {pkg_name}
"""
    else:
        return f"""
📋 **Exhibitor Registration Summary:**

👤 **Personal Information:**
- Email: {data.get('email')}
- First Name: {data.get('first_name')}
- Last Name: {data.get('last_name')}
- Phone: {data.get('phone', 'Not set')}
- Country: {data.get('country')}

🏢 **Company Information:**
- Company Name: {data.get('company_name')}
- Specialization: {spec_name}
- Selected Package: {pkg_name}
"""


def create_account_from_registration(reg_data: dict, session_id: str, language: str) -> tuple:
    """
    Create user account from registration data
    Handles both regular users and exhibitors with full company details
    
    Args:
        reg_data: Dictionary with user registration data
        session_id: Session ID for cleanup
        language: User's language preference
        
    Returns:
        JSON response with status
    """
    try:
        # Validate data
        validation = validate_registration_data(reg_data)
        if not validation['valid']:
            error_msg = ', '.join(validation['errors'])
            return jsonify({
                'status': 'error',
                'response': error_msg if language == 'en' else error_msg,
                'registration_mode': True,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=reg_data['email']).first()
        if existing_user:
            msg = 'هذا البريد الإلكتروني مسجل بالفعل!' if language == 'ar' else 'This email is already registered!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'registration_mode': True,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Validate exhibitor-specific data if needed
        if reg_data.get('role') == 'exhibitor':
            if not reg_data.get('company_name'):
                msg = 'اسم الشركة مطلوب!' if language == 'ar' else 'Company name is required!'
                return jsonify({
                    'status': 'error',
                    'response': msg,
                    'registration_mode': True,
                    'timestamp': datetime.now().isoformat()
                }), 400
            
            if not reg_data.get('specialization_id'):
                msg = 'التخصص مطلوب!' if language == 'ar' else 'Specialization is required!'
                return jsonify({
                    'status': 'error',
                    'response': msg,
                    'registration_mode': True,
                    'timestamp': datetime.now().isoformat()
                }), 400
            
            if not reg_data.get('package_id'):
                msg = 'الباقة مطلوبة!' if language == 'ar' else 'Package is required!'
                return jsonify({
                    'status': 'error',
                    'response': msg,
                    'registration_mode': True,
                    'timestamp': datetime.now().isoformat()
                }), 400
            
            # Verify package exists and is active
            package = Package.query.get(reg_data['package_id'])
            if not package or not package.is_active:
                msg = 'الباقة المختارة غير متاحة!' if language == 'ar' else 'Selected package is not available!'
                return jsonify({
                    'status': 'error',
                    'response': msg,
                    'registration_mode': True,
                    'timestamp': datetime.now().isoformat()
                }), 400
            
            # Verify specialization exists
            specialization = Specialization.query.get(reg_data['specialization_id'])
            if not specialization:
                msg = 'التخصص غير موجود!' if language == 'ar' else 'Specialization not found!'
                return jsonify({
                    'status': 'error',
                    'response': msg,
                    'registration_mode': True,
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        # Create new user
        new_user = User(
            email=reg_data['email'],
            password=generate_password_hash(reg_data['password'], method='scrypt'),
            first_name=reg_data['first_name'],
            last_name=reg_data['last_name'],
            role=reg_data.get('role', 'user'),
            phone=reg_data.get('phone', ''),
            country=reg_data['country'],
            is_active=True if reg_data.get('role') == 'user' else False  # Exhibitors need approval
        )
        
        # Add exhibitor-specific fields
        if reg_data.get('role') == 'exhibitor':
            new_user.company_name = reg_data.get('company_name')
            new_user.specialization_id = reg_data.get('specialization_id')
            new_user.package_id = reg_data.get('package_id')
        
        db.session.add(new_user)
        db.session.commit()
        
        # Clean up registration state
        if session_id in registration_state:
            del registration_state[session_id]
        
        # Success message
        if language == 'ar':
            if reg_data.get('role') == 'exhibitor':
                pkg = Package.query.get(reg_data['package_id'])
                pkg_name = pkg.name if pkg else 'الباقة'
                response_msg = f"""✅ **تم إنشاء حساب العارض بنجاح!**

مرحباً {reg_data['first_name']}،

🏢 **تفاصيل حسابك:**
- اسم الشركة: {reg_data['company_name']}
- الباقة المختارة: {pkg_name}
- حالة الحساب: ⏳ في انتظار موافقة الإدارة

سيتم مراجعة طلبك وإرسال بريد تأكيد إلى: {reg_data['email']}

شكراً لك على الانضمام! 🎉"""
            else:
                response_msg = f"""✅ **تم إنشاء الحساب بنجاح!**

مرحباً {reg_data['first_name']}،

يمكنك الآن تسجيل الدخول واستخدام المنصة.
سيتم إرسال بريد تأكيد إلى: {reg_data['email']}

شكراً لك! 🎉"""
        else:
            if reg_data.get('role') == 'exhibitor':
                pkg = Package.query.get(reg_data['package_id'])
                pkg_name = pkg.name if pkg else 'Package'
                response_msg = f"""✅ **Exhibitor Account Created Successfully!**

Hello {reg_data['first_name']},

🏢 **Account Details:**
- Company Name: {reg_data['company_name']}
- Selected Package: {pkg_name}
- Account Status: ⏳ Pending Admin Approval

Your request will be reviewed and a confirmation email will be sent to: {reg_data['email']}

Thank you for joining! 🎉"""
            else:
                response_msg = f"""✅ **Account Created Successfully!**

Hello {reg_data['first_name']},

You can now log in and use the platform.
A confirmation email will be sent to: {reg_data['email']}

Thank you! 🎉"""
        
        return jsonify({
            'status': 'success',
            'response': response_msg,
            'registration_complete': True,
            'user_email': reg_data['email'],
            'user_role': reg_data.get('role', 'user'),
            'company_name': reg_data.get('company_name', 'N/A'),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating account: {str(e)}")
        msg = f'خطأ في إنشاء الحساب: {str(e)}' if language == 'ar' else f'Error creating account: {str(e)}'
        return jsonify({
            'status': 'error',
            'response': msg,
            'registration_mode': True,
            'timestamp': datetime.now().isoformat()
        }), 500


@chatbot_bp.route('/quick-answer', methods=['POST'])
def quick_answer():
    """
    Quick answer endpoint for simple questions
    Used for instant feedback without full conversation context
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400
        
        try:
            chatbot = get_chatbot()
            response = chatbot.get_response(message)
            
            return jsonify({
                'status': 'success',
                'answer': response.get('response') if response.get('success') else response.get('response')
            }), 200
            
        except Exception as e:
            logger.error(f"Error in quick answer: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@chatbot_bp.route('/conversation-history', methods=['GET'])
@login_required
def get_conversation_history():
    """
    Get conversation history for the logged-in user
    """
    try:
        # Get all messages where user is involved with chatbot
        messages = ChatMessage.query.filter(
            db.or_(
                ChatMessage.sender_id == current_user.id,
                ChatMessage.receiver_id == current_user.id
            )
        ).filter(
            db.or_(
                ChatMessage.sender_id.is_(None),
                ChatMessage.receiver_id.is_(None)
            )
        ).order_by(ChatMessage.timestamp).all()
        
        history = []
        for msg in messages:
            history.append({
                'message': msg.message,
                'sender': 'user' if msg.sender_id == current_user.id else 'bot',
                'timestamp': msg.timestamp.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'history': history,
            'count': len(history)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching conversation history: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@chatbot_bp.route('/clear-history', methods=['POST'])
@login_required
def clear_conversation_history():
    """
    Clear conversation history for the logged-in user
    """
    try:
        # Delete all messages for this user with bot
        ChatMessage.query.filter(
            db.or_(
                ChatMessage.sender_id == current_user.id,
                ChatMessage.receiver_id == current_user.id
            )
        ).filter(
            db.or_(
                ChatMessage.sender_id.is_(None),
                ChatMessage.receiver_id.is_(None)
            )
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'تم حذف السجل'
        }), 200
        
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@chatbot_bp.route('/info', methods=['GET'])
def get_chatbot_info():
    """
    Get information about the chatbot
    """
    try:
        try:
            chatbot = get_chatbot()
            provider = chatbot.provider_name
        except:
            provider = 'unknown'
        
        return jsonify({
            'status': 'success',
            'name': 'Esco Fairs AI Assistant',
            'provider': provider,
            'languages': ['ar', 'en'],
            'available': True,
            'message_ar': 'مرحباً! أنا مساعدك الذكي لمعرض Esco Fairs. كيف يمكنني مساعدتك؟',
            'message_en': 'Hello! I\'m your intelligent assistant for Esco Fairs. How can I help you?'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chatbot info: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@chatbot_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for chatbot service"""
    try:
        try:
            chatbot = get_chatbot()
            is_healthy = chatbot.provider is not None
        except:
            is_healthy = False
        
        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat()
        }), 200 if is_healthy else 503
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@chatbot_bp.route('/check-account-status', methods=['POST'])
def check_account_status():
    """
    التحقق من حالة تفعيل حساب العارض
    Check if exhibitor account is activated by admin
    
    Request JSON:
    {
        "email": "exhibitor@example.com"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No email provided'
            }), 400
        
        email = data.get('email', '').strip().lower()
        language = detect_language(email)
        
        if not email or '@' not in email:
            msg = 'البريد الإلكتروني غير صحيح!' if language == 'ar' else 'Invalid email address!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # البحث عن المستخدم
        user = User.query.filter_by(email=email).first()
        
        if not user:
            msg = 'البريد الإلكتروني غير مسجل في النظام!' if language == 'ar' else 'Email not found in the system!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'found': False,
                'timestamp': datetime.now().isoformat()
            }), 404
        
        # التحقق من أن المستخدم عارض
        if user.role != 'exhibitor':
            msg = 'هذا الحساب ليس حساب عارض!' if language == 'ar' else 'This account is not an exhibitor account!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'is_exhibitor': False,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # التحقق من حالة التفعيل
        if user.is_active:
            # تم الموافقة
            pkg_name = user.package.name if user.package else 'N/A'
            if language == 'ar':
                response_msg = f"""✅ **تم تفعيل حسابك بنجاح!**

مرحباً {user.first_name}،

🏢 **معلومات حسابك:**
- الشركة: {user.company_name}
- الباقة: {pkg_name}
- الحالة: ✅ مفعل وجاهز للاستخدام

يمكنك الآن تسجيل الدخول واستخدام جميع ميزات المنصة.

رابط تسجيل الدخول: [رابط المنصة]"""
            else:
                response_msg = f"""✅ **Your Account Has Been Activated!**

Hello {user.first_name},

🏢 **Account Information:**
- Company: {user.company_name}
- Package: {pkg_name}
- Status: ✅ Active and Ready to Use

You can now log in and use all platform features.

Login Link: [Platform Link]"""
            
            return jsonify({
                'status': 'success',
                'response': response_msg,
                'account_active': True,
                'company_name': user.company_name,
                'package_name': pkg_name,
                'timestamp': datetime.now().isoformat()
            }), 200
        
        else:
            # في انتظار الموافقة
            if language == 'ar':
                response_msg = f"""⏳ **حسابك في انتظار الموافقة**

مرحباً {user.first_name}،

🏢 **معلومات حسابك:**
- الشركة: {user.company_name}
- الباقة: {user.package.name if user.package else 'N/A'}
- الحالة: ⏳ قيد المراجعة

فريق الإدارة يقوم حالياً بمراجعة طلبك. 
سيتم إرسال بريد إلكتروني لتأكيد التفعيل عندما يتم الموافقة عليه.

استقصاء الحالة: يمكنك التحقق مرة أخرى بعد بضع ساعات"""
            else:
                response_msg = f"""⏳ **Your Account is Pending Approval**

Hello {user.first_name},

🏢 **Account Information:**
- Company: {user.company_name}
- Package: {user.package.name if user.package else 'N/A'}
- Status: ⏳ Under Review

The admin team is currently reviewing your request.
You will receive a confirmation email once your account is activated.

Check Status: You can verify again after a few hours"""
            
            return jsonify({
                'status': 'success',
                'response': response_msg,
                'account_active': False,
                'company_name': user.company_name,
                'timestamp': datetime.now().isoformat()
            }), 200
        
    except Exception as e:
        logger.error(f"Error checking account status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@chatbot_bp.route('/create-company-email', methods=['POST'])
def create_company_email():
    """
    إنشاء رسالة بريدية للشركة باستخدام الذكاء الاصطناعي
    Create a company email draft using AI
    
    Request JSON:
    {
        "email": "exhibitor@example.com",
        "subject": "subject of the email"
    }
    """
    try:
        from ai_chatbot import generate_company_email
        
        data = request.get_json()
        
        if not data or 'email' not in data or 'subject' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Email and subject are required'
            }), 400
        
        exhibitor_email = data.get('email', '').strip().lower()
        subject = data.get('subject', '').strip()
        language = data.get('language', detect_language(subject or exhibitor_email))
        
        # التحقق من البيانات
        if not exhibitor_email or '@' not in exhibitor_email:
            msg = 'البريد الإلكتروني غير صحيح!' if language == 'ar' else 'Invalid email address!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if not subject:
            msg = 'الموضوع مطلوب!' if language == 'ar' else 'Subject is required!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # البحث عن المستخدم
        user = User.query.filter_by(email=exhibitor_email).first()
        
        if not user:
            msg = 'البريد الإلكتروني غير مسجل في النظام!' if language == 'ar' else 'Email not found in the system!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'timestamp': datetime.now().isoformat()
            }), 404
        
        # التحقق من أن المستخدم عارض
        if user.role != 'exhibitor':
            msg = 'هذا الحساب ليس حساب عارض!' if language == 'ar' else 'This account is not an exhibitor account!'
            return jsonify({
                'status': 'error',
                'response': msg,
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # توليد الرسالة باستخدام الذكاء الاصطناعي
        email_body = generate_company_email(subject, user.company_name, language)
        
        # إنشاء الرسالة
        message_id = f"email_{exhibitor_email}_{int(datetime.now().timestamp())}"
        email_draft = {
            'to': exhibitor_email,
            'company_name': user.company_name,
            'subject': subject,
            'body': email_body,
            'created_at': datetime.now().isoformat(),
            'from_chatbot': True,
            'generated_by_ai': True,
            'status': 'draft'
        }
        
        message_drafts[message_id] = email_draft
        
        # إرجاع النتيجة
        if language == 'ar':
            response_msg = f"""✅ **تم إنشاء الرسالة البريدية بنجاح!**

📧 **بيانات الرسالة:**
- إلى: {user.company_name} ({exhibitor_email})
- الموضوع: {subject}
- نوع المحتوى: 🤖 تم توليده بواسطة الذكاء الاصطناعي

📝 **محتوى الرسالة:**
{email_body}

---

📌 **التعليمات:**
1. نسخ محتوى الرسالة أعلاه
2. افتح بريدك الإلكتروني
3. أرسل الرسالة إلى: support@foodexhibit.com

معرف الرسالة: `{message_id}`
"""
        else:
            response_msg = f"""✅ **Email Created Successfully!**

📧 **Email Details:**
- To: {user.company_name} ({exhibitor_email})
- Subject: {subject}
- Content Type: 🤖 AI Generated

📝 **Email Body:**
{email_body}

---

📌 **Instructions:**
1. Copy the email content above
2. Open your email client
3. Send to: support@foodexhibit.com

Message ID: `{message_id}`
"""
        
        return jsonify({
            'status': 'success',
            'response': response_msg,
            'message_id': message_id,
            'email_draft': email_draft,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating company email: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Register blueprint with app
def register_chatbot_routes(app):
    """Register chatbot routes with Flask app"""
    app.register_blueprint(chatbot_bp)
