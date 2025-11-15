"""
AI-powered Chatbot Service for Food Exhibit Platform
دعم Gemini و ChatGPT
Auto Language Detection - الكشف التلقائي عن اللغة
"""

import os
import json
import re
from typing import Optional, List, Dict
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load guidelines from file
GUIDELINES_PATH = os.path.join(os.path.dirname(__file__), 'chatbot_guidelines.txt')


def detect_language(text: str) -> str:
    """
    Detect language from text
    Returns 'ar' for Arabic, 'en' for English
    Default: 'ar'
    """
    if not text:
        return 'ar'
    
    # Count Arabic and English characters
    arabic_pattern = r'[\u0600-\u06FF]'  # Arabic Unicode range
    english_pattern = r'[a-zA-Z]'
    
    arabic_count = len(re.findall(arabic_pattern, text))
    english_count = len(re.findall(english_pattern, text))
    
    # If more Arabic characters, return Arabic
    if arabic_count > english_count:
        return 'ar'
    # If more English characters, return English
    elif english_count > arabic_count:
        return 'en'
    # Default to Arabic if equal or no specific characters
    else:
        return 'ar'


class AIProvider:
    """Base class for AI providers"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.guidelines = self._load_guidelines()
    
    def _load_guidelines(self) -> str:
        """Load guidelines from file"""
        try:
            with open(GUIDELINES_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Guidelines file not found at {GUIDELINES_PATH}")
            return "You are a helpful assistant for Food Exhibit Platform."
    
    def get_response(self, user_message: str, conversation_history: List[Dict] = None) -> Optional[str]:
        """Get response from AI provider - to be implemented by subclasses"""
        raise NotImplementedError


class GeminiProvider(AIProvider):
    """Google Gemini AI Provider"""
    
    def __init__(self, api_key: str):
        try:
            import google.generativeai as genai
            self.genai = genai
            self.genai.configure(api_key=api_key)
            # Use the latest fast model available
            self.model = self.genai.GenerativeModel('gemini-2.0-flash')
        except ImportError:
            logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {str(e)}")
            raise
        
        super().__init__(api_key)
        self.registration_state = {}  # Track user registration state
    
    def get_response(self, user_message: str, conversation_history: List[Dict] = None, language: str = 'ar') -> Optional[str]:
        """Get response from Gemini with auto language detection"""
        try:
            # Auto-detect language from user message
            language = detect_language(user_message)
            
            # Build system prompt based on detected language
            if language == 'en':
                system_prompt = f"""You are a professional and helpful AI assistant for the Esco Fairs Platform.
These are the system guidelines:

{self.guidelines}

Response Instructions:
1. Reply naturally and friendly to any general question (like "Hello" or "How are you?")
2. If the question is related to the platform, use the information from the trained data above
3. Be professional and friendly in all responses
4. If you don't know the answer to a specific question about the platform, say: "Sorry, I don't have complete information about this topic. Please contact our support team"
5. ALWAYS respond in English - NEVER respond in Arabic
6. Keep responses short and helpful"""
            else:  # Arabic (ar)
                system_prompt = f"""أنت مساعد ذكي محترف لمنصة معرض Esco Fairs.
هذه معلومات النظام الأساسية:

{self.guidelines}

تعليمات الرد:
1. رد بشكل طبيعي وودود على أي سؤال عام (مثل "مرحباً" أو "كيفك؟")
2. إذا كان السؤال متعلقاً بالمنصة، استخدم المعلومات من البيانات المدربة أعلاه
3. كن محترفاً وودوداً في كل الردود
4. إذا لم تعرف الإجابة على سؤال معين عن المنصة، قل: "عذراً، لا أملك معلومات كاملة عن هذا الموضوع. يرجى التواصل مع فريق الدعم"
5. يجب الرد دائماً باللغة العربية - لا تترجم إلى لغات أخرى
6. اجعل الردود قصيرة ومفيدة"""
            
            # Build message history for context (last 10 messages)
            messages = []
            
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({
                        "role": msg.get('role', 'user'),
                        "content": msg.get('content', '')
                    })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Create chat session for faster responses
            chat = self.model.start_chat(history=[])
            
            # Send message with system prompt
            full_prompt = f"{system_prompt}\n\nالرسالة: {user_message}"
            response = chat.send_message(full_prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return "عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة مرة أخرى."
                
        except Exception as e:
            logger.error(f"Error getting response from Gemini: {str(e)}")
            return f"عذراً، حدث خطأ: {str(e)}"


class ChatGPTProvider(AIProvider):
    """OpenAI ChatGPT Provider"""
    
    def __init__(self, api_key: str):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            logger.error("openai not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ChatGPT: {str(e)}")
            raise
        
        super().__init__(api_key)
    
    def get_response(self, user_message: str, conversation_history: List[Dict] = None, language: str = 'ar') -> Optional[str]:
        """Get response from ChatGPT with auto language detection"""
        try:
            # Auto-detect language from user message
            language = detect_language(user_message)
            
            # Build system prompt with guidelines based on detected language
            if language == 'en':
                system_prompt = f"""You are a helpful and professional customer support assistant for the Esco Fairs Platform.

{self.guidelines}

IMPORTANT: 
- ALWAYS respond in English
- NEVER respond in Arabic
- Be friendly and professional
- Provide clear and concise answers
- If you don't know something, suggest contacting support
- Keep responses brief and helpful"""
            else:  # Arabic (ar)
                system_prompt = f"""أنت مساعد خدمة عملاء مفيد واحترافي لمنصة معرض Esco Fairs.

{self.guidelines}

تعليمات مهمة:
- الرد دائماً باللغة العربية - لا تترجم
- كن ودياً واحترافياً
- قدم إجابات واضحة ومختصرة
- إذا لم تعرف شيء، اقترح التواصل مع الدعم
- اجعل الردود قصيرة ومفيدة"""
            
            # Build message history
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]
            
            if conversation_history:
                # Add last 5 messages for context
                for msg in conversation_history[-5:]:
                    messages.append({
                        "role": msg.get('role', 'user'),
                        "content": msg.get('content', '')
                    })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Get response from ChatGPT
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            if response and response.choices:
                return response.choices[0].message.content.strip()
            else:
                logger.warning("Empty response from ChatGPT")
                return None
                
        except Exception as e:
            logger.error(f"Error getting response from ChatGPT: {str(e)}")
            return None


class ChatbotManager:
    """Main chatbot manager that handles AI provider selection and responses"""
    
    def __init__(self, provider: str = 'gemini', api_key: str = None):
        """
        Initialize chatbot manager
        
        Args:
            provider: 'gemini' or 'chatgpt'
            api_key: API key for the selected provider
        """
        self.provider_name = provider.lower()
        self.api_key = api_key or self._get_api_key_from_env()
        self.provider = None
        self.conversation_history: List[Dict] = []
        
        if not self.api_key:
            raise ValueError(f"API key for {provider} not provided")
        
        self._initialize_provider()
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variables"""
        if self.provider_name == 'gemini':
            return os.environ.get('GOOGLE_API_KEY')
        elif self.provider_name == 'chatgpt':
            return os.environ.get('OPENAI_API_KEY')
        return None
    
    def _initialize_provider(self):
        """Initialize the selected AI provider"""
        try:
            if self.provider_name == 'gemini':
                self.provider = GeminiProvider(self.api_key)
                logger.info("Initialized Gemini provider")
            elif self.provider_name == 'chatgpt':
                self.provider = ChatGPTProvider(self.api_key)
                logger.info("Initialized ChatGPT provider")
            else:
                raise ValueError(f"Unknown provider: {self.provider_name}")
        except Exception as e:
            logger.error(f"Failed to initialize {self.provider_name}: {str(e)}")
            raise
    
    def get_response(self, user_message: str, user_id: int = None, language: str = None) -> Dict:
        """
        Get AI response to user message with auto language detection
        
        Args:
            user_message: The user's message
            user_id: Optional user ID for tracking
            language: Optional language override (if None, auto-detect)
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Auto-detect language if not provided
            if not language:
                language = detect_language(user_message)
            
            # Add user message to history
            self.conversation_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Get response from provider (language will be detected again in provider)
            ai_response = self.provider.get_response(
                user_message,
                self.conversation_history
            )
            
            if not ai_response:
                # Default error message based on detected language
                if language == 'en':
                    ai_response = "Sorry, there was an error getting the response. Please try again or contact support."
                else:
                    ai_response = "عذراً، حدث خطأ في الحصول على الرد. يرجى محاولة مرة أخرى أو التواصل مع الدعم الفني."
            
            # Add AI response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'response': ai_response,
                'provider': self.provider_name,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            return {
                'success': False,
                'response': f"عذراً، حدث خطأ: {str(e)}",
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def clear_history(self, user_id: int = None):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info(f"Cleared history for user {user_id or 'unknown'}")
    
    def get_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history


# Factory function to create chatbot
def create_chatbot(provider: str = None, api_key: str = None) -> ChatbotManager:
    """
    Factory function to create a chatbot instance
    
    Args:
        provider: 'gemini' (default) or 'chatgpt'
        api_key: API key (if not provided, will look in environment)
        
    Returns:
        ChatbotManager instance
    """
    provider = provider or os.environ.get('AI_PROVIDER', 'gemini')
    return ChatbotManager(provider=provider, api_key=api_key)


# Singleton instance for the application
_chatbot_instance: Optional[ChatbotManager] = None


def get_chatbot() -> ChatbotManager:
    """Get or create the global chatbot instance"""
    global _chatbot_instance
    
    if _chatbot_instance is None:
        try:
            _chatbot_instance = create_chatbot()
        except Exception as e:
            logger.error(f"Failed to initialize chatbot: {str(e)}")
            raise
    
    return _chatbot_instance


def handle_user_registration(user_message: str, user_id: int = None) -> Dict:
    """
    Handle user registration through chatbot
    Detects registration requests and guides user through registration process
    
    Returns:
        Dictionary with registration data or request for next info
    """
    language = detect_language(user_message)
    
    # Registration keywords
    ar_keywords = ['تسجيل', 'حساب جديد', 'انشاء حساب', 'عضو جديد', 'مستخدم جديد', 'اريد حساب', 'ابدأ']
    en_keywords = ['register', 'sign up', 'create account', 'new account', 'new user', 'join', 'account']
    
    user_message_lower = user_message.lower()
    
    # Check if user wants to register
    if language == 'ar':
        wants_to_register = any(keyword in user_message_lower for keyword in ar_keywords)
    else:
        wants_to_register = any(keyword in user_message_lower for keyword in en_keywords)
    
    if wants_to_register:
        if language == 'en':
            return {
                'action': 'start_registration',
                'language': 'en',
                'step': 'email',
                'message': 'Great! I\'ll help you create an account. What is your email address?',
                'next_field': 'email'
            }
        else:
            return {
                'action': 'start_registration',
                'language': 'ar',
                'step': 'email',
                'message': 'حسناً! سأساعدك في إنشاء حساب. ما هو عنوان بريدك الإلكتروني؟',
                'next_field': 'email'
            }
    
    return {'action': 'none'}


def detect_account_status_request(user_message: str) -> bool:
    """
    الكشف عن طلب التحقق من حالة الحساب
    Detect if user is asking about account approval status
    """
    ar_keywords = ['حالة', 'موافقة', 'تفعيل', 'حسابي', 'الموافقة', 'متى', 'تم تفعيل', 'هل تم الموافقة', 'حسابي']
    en_keywords = ['status', 'approval', 'active', 'activate', 'approved', 'account', 'when', 'check']
    
    user_message_lower = user_message.lower()
    
    ar_check = any(keyword in user_message_lower for keyword in ar_keywords)
    en_check = any(keyword in user_message_lower for keyword in en_keywords)
    
    return ar_check or en_check


def detect_email_request(user_message: str) -> bool:
    """
    الكشف عن طلب إنشاء رسالة بريدية
    Detect if user is asking to create a company email
    """
    ar_keywords = ['رسالة', 'بريد', 'رسالة بريدية', 'أرسل رسالة', 'اكتب رسالة', 'أكتب بريد', 'تواصل']
    en_keywords = ['email', 'message', 'compose', 'send email', 'write message', 'draft', 'write email']
    
    user_message_lower = user_message.lower()
    
    ar_check = any(keyword in user_message_lower for keyword in ar_keywords)
    en_check = any(keyword in user_message_lower for keyword in en_keywords)
    
    return ar_check or en_check


def generate_company_email(subject: str, company_name: str, language: str = 'ar') -> str:
    """
    توليد محتوى الرسالة البريدية باستخدام الذكاء الاصطناعي
    Generate email body using AI
    
    Args:
        subject: موضوع الرسالة
        company_name: اسم الشركة
        language: اللغة (ar أو en)
        
    Returns:
        محتوى الرسالة المولد
    """
    try:
        # استخدام نفس الـ API للـ Gemini
        import google.generativeai as genai
        
        # إنشاء طلب احترافي للـ AI لكتابة الرسالة
        if language == 'ar':
            prompt = f"""أنت متخصص في كتابة الرسائل البريدية الاحترافية.
            
اكتب رسالة بريدية احترافية بالعربية للشركة: {company_name}

موضوع الرسالة: {subject}

المتطلبات:
- اجعل الرسالة احترافية وودية
- اجتعل الرسالة واضحة وموجزة (3-5 فقرات)
- ضمن معلومات مفيدة ذات صلة بالموضوع
- ختم الرسالة بطريقة احترافية

الرسالة:"""
        else:
            prompt = f"""You are a professional email writer.

Write a professional email in English for the company: {company_name}

Email Subject: {subject}

Requirements:
- Make the email professional and friendly
- Keep it clear and concise (3-5 paragraphs)
- Include relevant and useful information about the subject
- End with a professional closing

Email Body:"""
        
        # استخدام Gemini لتوليد الرسالة
        genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        else:
            # فالب: رسالة افتراضية
            if language == 'ar':
                return f"""السلام عليكم ورحمة الله وبركاته

تحية طيبة إلى شركة {company_name}،

فيما يتعلق بـ {subject}، نود التواصل معكم بخصوص هذا الموضوع المهم.

نتطلع إلى تعاون مثمر معكم وتحقيق الأهداف المشتركة.

مع أطيب التحيات،
إدارة المنصة"""
            else:
                return f"""Dear {company_name},

We hope this message finds you well.

Regarding {subject}, we would like to communicate with you about this important matter.

We look forward to a fruitful cooperation and achieving mutual goals.

Best regards,
Platform Management"""
    
    except Exception as e:
        logger.error(f"Error generating email with AI: {str(e)}")
        # إرجاع رسالة افتراضية في حالة الخطأ
        if language == 'ar':
            return f"""السلام عليكم ورحمة الله وبركاته

تحية طيبة إلى شركة {company_name}،

فيما يتعلق بـ {subject}، نود التواصل معكم بخصوص هذا الموضوع المهم.

نتطلع إلى تعاون مثمر معكم.

مع أطيب التحيات"""
        else:
            return f"""Dear {company_name},

We hope this message finds you well.

Regarding {subject}, we would like to communicate with you about this important matter.

We look forward to a fruitful cooperation.

Best regards"""


def validate_registration_data(data: Dict) -> Dict:
    """
    Validate registration data from chatbot
    
    Args:
        data: Dictionary with registration fields
        
    Returns:
        Dictionary with validation status and errors if any
    """
    errors = []
    
    # Email validation
    if 'email' in data and not data['email']:
        errors.append('Email is required')
    
    # Password validation
    if 'password' in data:
        if not data['password']:
            errors.append('Password is required')
        elif len(data['password']) < 6:
            errors.append('Password must be at least 6 characters')
    
    # First name validation
    if 'first_name' in data and not data['first_name']:
        errors.append('First name is required')
    
    # Last name validation
    if 'last_name' in data and not data['last_name']:
        errors.append('Last name is required')
    
    # Phone validation (basic)
    if 'phone' in data and data['phone'] and len(data['phone']) < 7:
        errors.append('Invalid phone number')
    
    # Country validation
    if 'country' in data and not data['country']:
        errors.append('Country is required')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


if __name__ == "__main__":
    # Test the chatbot
    try:
        chatbot = create_chatbot()
        
        # Test messages
        test_messages = [
            "مرحباً، كيف يمكنني البدء في استخدام المنصة؟",
            "كيف أحجز موعداً مع عارض؟",
            "هل هناك رسوم للتسجيل؟"
        ]
        
        for msg in test_messages:
            print(f"\nUser: {msg}")
            response = chatbot.get_response(msg)
            if response['success']:
                print(f"Bot: {response['response']}")
            else:
                print(f"Error: {response['error']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
