import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import re
import os
import requests
import threading
from supabase import create_client, Client
from dotenv import load_dotenv
import time

# Загрузка переменных окружения
load_dotenv()

# ============================================================================
# КОНФИГУРАЦИЯ И КОНСТАНТЫ
# ============================================================================

PAGE_CONFIG = {
    "page_title": "Психолог | Система записи",
    "page_icon": "🌿",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"  # admin123

BOOKING_RULES = {
    "MIN_ADVANCE_HOURS": 1,
    "MIN_CANCEL_MINUTES": 30,
    "MAX_DAYS_AHEAD": 30,
}

STATUS_DISPLAY = {
    'confirmed': {'emoji': '✅', 'text': 'Подтверждена', 'color': '#88c8bc', 'bg_color': '#f0f9f7'},
    'cancelled': {'emoji': '❌', 'text': 'Отменена', 'color': '#ff6b6b', 'bg_color': '#fff5f5'},
    'completed': {'emoji': '✅', 'text': 'Завершена', 'color': '#6ba292', 'bg_color': '#f0f9f7'}
}

WEEKDAY_MAP = {
    '0': 'Вс', '1': 'Пн', '2': 'Вт', 
    '3': 'Ср', '4': 'Чт', '5': 'Пт', '6': 'Сб'
}

TELEGRAM_CONFIG = {
    'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
    'admin_chat_id': os.getenv('TELEGRAM_ADMIN_CHAT_ID', ''),
    'bot_username': os.getenv('TELEGRAM_BOT_USERNAME', 'Jenyhelperbot'),
    'enabled': True
}

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ SUPABASE
# ============================================================================

@st.cache_resource
def init_supabase():
    """Инициализация клиента Supabase"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            st.error("❌ SUPABASE_URL и SUPABASE_KEY не настроены в переменных окружения")
            return None
            
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"❌ Ошибка подключения к Supabase: {e}")
        return None

# ============================================================================
# УЛУЧШЕННАЯ СТИЛИЗАЦИЯ С АНИМАЦИЯМИ И MODERN UI
# ============================================================================

def load_custom_css():
    """Загрузка улучшенных CSS стилей с современными эффектами"""
    st.markdown("""
        <style>
        /* ===== ОБЩИЕ СТИЛИ ===== */
        .main {
            padding: 0rem 1rem;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }
        
        /* ===== КНОПКИ С УЛУЧШЕННОЙ АНИМАЦИЕЙ ===== */
        .stButton>button {
            width: 100%;
            border-radius: 12px;
            height: 3.2em;
            background: linear-gradient(135deg, #88c8bc 0%, #6ba292 100%);
            color: white;
            font-weight: 600;
            border: none;
            box-shadow: 0 4px 15px rgba(136, 200, 188, 0.3);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-size: 1rem;
            position: relative;
            overflow: hidden;
        }
        
        .stButton>button::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }
        
        .stButton>button:hover::before {
            width: 300px;
            height: 300px;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(136, 200, 188, 0.5);
            background: linear-gradient(135deg, #6ba292 0%, #88c8bc 100%);
        }
        
        .stButton>button:active {
            transform: translateY(0);
            box-shadow: 0 4px 15px rgba(136, 200, 188, 0.3);
        }
        
        /* ===== КАРТОЧКИ ЗАПИСЕЙ ===== */
        .booking-card {
            padding: 2rem;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.98);
            margin-bottom: 1.5rem;
            border-left: 5px solid #88c8bc;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .booking-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(136, 200, 188, 0.1), transparent);
            transition: left 0.5s;
        }
        
        .booking-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
        }
        
        .booking-card:hover::before {
            left: 100%;
        }
        
        /* ===== ИНФОРМАЦИОННЫЕ ПАНЕЛИ ===== */
        .info-box {
            background: white;
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
            border-left: 5px solid #88c8bc;
            transition: all 0.3s ease;
            animation: fadeInUp 0.5s ease-out;
        }
        
        .info-box:hover {
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* ===== ПРИВЕТСТВЕННЫЙ ХЕДЕР ===== */
        .welcome-header {
            background: linear-gradient(135deg, #88c8bc 0%, #a8d5ba 100%);
            color: white;
            padding: 3rem 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 10px 40px rgba(136, 200, 188, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .welcome-header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: rotate 20s linear infinite;
        }
        
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .welcome-header h1 {
            position: relative;
            z-index: 1;
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        
        .welcome-header p {
            position: relative;
            z-index: 1;
            margin: 0.5rem 0 0 0;
            font-size: 1.2rem;
            opacity: 0.95;
        }
        
        /* ===== СООБЩЕНИЯ О УСПЕХЕ ===== */
        .success-message {
            background: linear-gradient(135deg, #f0f9f7 0%, #e8f5f1 100%);
            border-left: 5px solid #88c8bc;
            padding: 2rem;
            border-radius: 16px;
            margin: 1.5rem 0;
            box-shadow: 0 8px 30px rgba(136, 200, 188, 0.2);
            animation: slideInRight 0.5s ease-out;
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .success-message h3 {
            color: #88c8bc;
            margin-top: 0;
        }
        
        /* ===== TELEGRAM СТАТУСЫ ===== */
        .telegram-connected {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-left: 5px solid #0088cc;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            animation: fadeIn 0.5s ease-out;
        }
        
        .telegram-disconnected {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            border-left: 5px solid #ff9800;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            animation: fadeIn 0.5s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        /* ===== ВРЕМЕННЫЕ СЛОТЫ ===== */
        .time-slot-button {
            transition: all 0.2s ease;
        }
        
        .time-slot-button:hover {
            transform: scale(1.05);
        }
        
        /* ===== МЕТРИКИ ===== */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
            color: #88c8bc;
        }
        
        /* ===== ФОРМЫ ===== */
        .stTextInput>div>div>input,
        .stTextArea>div>div>textarea,
        .stSelectbox>div>div>select {
            border-radius: 10px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s ease;
        }
        
        .stTextInput>div>div>input:focus,
        .stTextArea>div>div>textarea:focus,
        .stSelectbox>div>div>select:focus {
            border-color: #88c8bc;
            box-shadow: 0 0 0 3px rgba(136, 200, 188, 0.1);
        }
        
        /* ===== ЭКСПАНДЕРЫ ===== */
        .streamlit-expanderHeader {
            background: white;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            transition: all 0.3s ease;
        }
        
        .streamlit-expanderHeader:hover {
            background: #f8f9fa;
            border-color: #88c8bc;
        }
        
        /* ===== ТАБЫ ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 12px 24px;
            background: white;
            border: 2px solid #e0e0e0;
            transition: all 0.3s ease;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background: #f8f9fa;
            border-color: #88c8bc;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #88c8bc 0%, #6ba292 100%);
            color: white !important;
            border-color: #88c8bc;
        }
        
        /* ===== ПРОГРЕСС БАР ===== */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #88c8bc 0%, #6ba292 100%);
        }
        
        /* ===== АЛЕРТЫ ===== */
        .stAlert {
            border-radius: 12px;
            animation: slideInLeft 0.3s ease-out;
        }
        
        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        /* ===== САЙДБАР ===== */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
        }
        
        /* ===== СКРОЛЛБАР ===== */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #88c8bc 0%, #6ba292 100%);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #6ba292 0%, #88c8bc 100%);
        }
        
        /* ===== LOADING SPINNER ===== */
        .stSpinner > div {
            border-top-color: #88c8bc !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ============================================================================
# УТИЛИТЫ И ХЕЛПЕРЫ (УЛУЧШЕННЫЕ)
# ============================================================================

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def normalize_phone(phone: str) -> str:
    """Нормализация номера телефона"""
    return re.sub(r'\D', '', phone)

def format_phone(phone: str) -> str:
    """Форматирование телефона для отображения"""
    clean = normalize_phone(phone)
    if len(clean) == 11 and clean.startswith('7'):
        return f"+7 ({clean[1:4]}) {clean[4:7]}-{clean[7:9]}-{clean[9:]}"
    elif len(clean) == 10:
        return f"+7 ({clean[0:3]}) {clean[3:6]}-{clean[6:8]}-{clean[8:]}"
    return phone

def validate_phone(phone: str) -> tuple:
    """Валидация телефона с детальной проверкой"""
    clean = normalize_phone(phone)
    if len(clean) < 10:
        return False, "❌ Номер слишком короткий"
    if len(clean) > 11:
        return False, "❌ Номер слишком длинный"
    if not clean.isdigit():
        return False, "❌ Только цифры"
    if len(clean) == 11 and not clean.startswith('7'):
        return False, "❌ Неверный формат (должен начинаться с 7)"
    return True, "✅ Корректный номер"

def validate_email(email: str) -> tuple:
    """Валидация email с детальной проверкой"""
    if not email:
        return True, "ℹ️ Email не обязателен"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, "✅ Email корректен"
    return False, "❌ Неверный формат email"

def format_date(date_str: str, format_str: str = '%d.%m.%Y') -> str:
    """Форматирование даты с обработкой ошибок"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime(format_str)
    except:
        return date_str

def calculate_time_until(date_str: str, time_str: str) -> timedelta:
    """Вычисление времени до события"""
    try:
        event_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return event_datetime - datetime.now()
    except:
        return timedelta(0)

def format_timedelta(td: timedelta) -> str:
    """Форматирование timedelta в читаемый вид"""
    if td.total_seconds() < 0:
        return "Прошло"
    
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} дн.")
    if hours > 0:
        parts.append(f"{hours} ч.")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} мин.")
    
    return " ".join(parts)

def get_month_end(year: int, month: int) -> str:
    """Получение последнего дня месяца"""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    month_end = next_month - timedelta(days=1)
    return month_end.strftime('%Y-%m-%d')

def get_weekday_name(date_str: str) -> str:
    """Получение названия дня недели"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return weekday_names[date_obj.weekday()]
    except:
        return ""

def format_datetime_relative(date_str: str, time_str: str) -> str:
    """Форматирование даты/времени относительно текущего момента"""
    try:
        event_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        now = datetime.now()
        
        if event_datetime.date() == now.date():
            return f"Сегодня в {time_str}"
        elif event_datetime.date() == (now + timedelta(days=1)).date():
            return f"Завтра в {time_str}"
        elif event_datetime.date() == (now - timedelta(days=1)).date():
            return f"Вчера в {time_str}"
        else:
            return f"{format_date(date_str)} в {time_str}"
    except:
        return f"{date_str} {time_str}"

# ============================================================================
# TELEGRAM БОТ ДЛЯ УВЕДОМЛЕНИЙ
# ============================================================================

class TelegramBotService:
    def __init__(self):
        self.bot_token = TELEGRAM_CONFIG['bot_token']
        self.admin_chat_id = TELEGRAM_CONFIG['admin_chat_id']
        self.bot_username = TELEGRAM_CONFIG['bot_username']
        self.enabled = TELEGRAM_CONFIG['enabled']
    
    def _send_message(self, chat_id: str, message: str, parse_mode: str = 'HTML') -> bool:
        """Базовая отправка сообщения в Telegram"""
        try:
            if not self.enabled or not self.bot_token:
                return False
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ Ошибка Telegram ({response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")
            return False
    
    def send_to_admin(self, message: str) -> bool:
        """Отправка сообщения администратору"""
        return self._send_message(self.admin_chat_id, message)
    
    def send_to_client(self, client_chat_id: str, message: str) -> bool:
        """Отправка сообщения клиенту"""
        return self._send_message(client_chat_id, message)
    
    def check_client_connection(self, chat_id: str) -> bool:
        """Проверка подключения клиента к боту"""
        try:
            test_message = "🔍 Проверка подключения..."
            return self._send_message(chat_id, test_message)
        except:
            return False
    
    def get_bot_link(self, client_phone: str = None) -> str:
        """Получение ссылки на бота с параметрами"""
        base_url = f"https://t.me/{self.bot_username}"
        if client_phone:
            return f"{base_url}?start=connect_{hash_password(client_phone)[:10]}"
        return base_url
    
    # ============================================================================
    # УВЕДОМЛЕНИЯ О ЗАПИСИ
    # ============================================================================
    
    def notify_booking_created_admin(self, booking_data: dict) -> bool:
        """Уведомление админу о новой записи"""
        name = booking_data.get('client_name', 'Клиент')
        phone = booking_data.get('client_phone', 'Не указан')
        date = format_date(booking_data.get('booking_date', ''))
        time = booking_data.get('booking_time', '')
        
        message = f"""
📅 <b>НОВАЯ ЗАПИСЬ НА КОНСУЛЬТАЦИЮ</b>

👤 <b>Клиент:</b> {name}
📱 <b>Телефон:</b> <code>{phone}</code>
📅 <b>Дата:</b> {date}
🕐 <b>Время:</b> {time}

⏰ <i>Напоминание будет отправлено за 1 час до консультации</i>
        """
        
        return self.send_to_admin(message)
    
    def notify_booking_created_client(self, client_chat_id: str, booking_data: dict) -> bool:
        """Уведомление клиенту о подтверждении записи"""
        name = booking_data.get('client_name', '')
        date = format_date(booking_data.get('booking_date', ''))
        time = booking_data.get('booking_time', '')
        
        message = f"""
✅ <b>ВАША ЗАПИСЬ ПОДТВЕРЖДЕНА</b>

Добрый день, {name}!

📅 <b>Дата:</b> {date}
🕐 <b>Время:</b> {time}

Мы ждем вас на консультацию!

⏰ <i>Мы напомним вам за 1 час до начала</i>

Если у вас возникли вопросы, ответьте на это сообщение.
        """
        
        return self.send_to_client(client_chat_id, message)
    
    def notify_booking_cancelled_admin(self, booking_data: dict) -> bool:
        """Уведомление админу об отмене записи"""
        name = booking_data.get('client_name', 'Клиент')
        phone = booking_data.get('client_phone', 'Не указан')
        date = format_date(booking_data.get('booking_date', ''))
        
        message = f"""
❌ <b>ОТМЕНА ЗАПИСИ</b>

👤 <b>Клиент:</b> {name}
📱 <b>Телефон:</b> <code>{phone}</code>
📅 <b>Дата:</b> {date}

🚫 <i>Запись отменена клиентом</i>
        """
        
        return self.send_to_admin(message)
    
    def notify_booking_cancelled_client(self, client_chat_id: str, booking_data: dict) -> bool:
        """Уведомление клиенту об отмене записи"""
        name = booking_data.get('client_name', '')
        date = format_date(booking_data.get('booking_date', ''))
        
        message = f"""
❌ <b>ЗАПИСЬ ОТМЕНЕНА</b>

Уважаемый(ая) {name},

Ваша запись на {date} отменена.

Если вы хотите записаться на другое время, ответьте на это сообщение.

С уважением,
Ваш психолог
        """
        
        return self.send_to_client(client_chat_id, message)
    
    def notify_reminder_admin(self, booking_data: dict) -> bool:
        """Напоминание админу за 1 час"""
        name = booking_data.get('client_name', 'Клиент')
        phone = booking_data.get('client_phone', 'Не указан')
        time = booking_data.get('booking_time', '')
        
        message = f"""
⏰ <b>НАПОМИНАНИЕ О КОНСУЛЬТАЦИИ</b>

Через 1 час у вас консультация:

👤 <b>Клиент:</b> {name}
📱 <b>Телефон:</b> <code>{phone}</code>
🕐 <b>Время:</b> {time}

Подготовьтесь к встрече!
        """
        
        return self.send_to_admin(message)
    
    def notify_reminder_client(self, client_chat_id: str, booking_data: dict) -> bool:
        """Напоминание клиенту за 1 час"""
        name = booking_data.get('client_name', '')
        time = booking_data.get('booking_time', '')
        
        message = f"""
⏰ <b>НАПОМИНАНИЕ О КОНСУЛЬТАЦИИ</b>

Добрый день, {name}!

Через 1 час у вас консультация в {time}.

Пожалуйста, подготовьтесь к встрече.

Ждем вас!
        """
        
        return self.send_to_client(client_chat_id, message)
    
    def send_welcome_notification(self, client_chat_id: str, client_name: str, upcoming_bookings: list):
        """Приветственное уведомление после подключения"""
        message = f"""
👋 <b>ДОБРО ПОЖАЛОВАТЬ, {client_name}!</b>

✅ <b>Вы успешно подключили уведомления!</b>

Теперь вы будете получать:
• ✅ Подтверждения новых записей
• ⏰ Напоминания за 1 час до консультаций
• ❌ Уведомления об отменах
        """
        
        # Добавляем информацию о предстоящих записях
        if upcoming_bookings:
            message += "\n\n📅 <b>Ваши предстоящие консультации:</b>\n"
            for booking in upcoming_bookings:
                date = format_date(booking.get('booking_date', ''))
                time = booking.get('booking_time', '')
                message += f"• {date} в {time}\n"
        
        message += "\nС уважением,\nВаш психолог 🌿"
        
        return self.send_to_client(client_chat_id, message)
    
    def send_upcoming_bookings_notification(self, client_chat_id: str, client_name: str, bookings: list):
        """Уведомление о предстоящих записях"""
        if not bookings:
            return False
        
        message = f"""
📅 <b>ВАШИ ПРЕДСТОЯЩИЕ КОНСУЛЬТАЦИИ</b>

Уважаемый(ая) {client_name},

У вас запланированы консультации:
        """
        
        for booking in bookings:
            date = format_date(booking.get('booking_date', ''))
            time = booking.get('booking_time', '')
            message += f"\n• {date} в {time}"
        
        message += "\n\n⏰ Мы напомним вам за 1 час до каждой консультации!"
        
        return self.send_to_client(client_chat_id, message)
    
    def schedule_reminder(self, booking_data: dict, client_chat_id: str):
        """Планирование напоминания за 1 час до консультации"""
        try:
            booking_date = booking_data.get('booking_date')
            booking_time = booking_data.get('booking_time')
            
            if not booking_date or not booking_time:
                return
            
            # Создаем datetime объекта консультации
            consultation_datetime = datetime.strptime(
                f"{booking_date} {booking_time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Вычисляем время напоминания (за 1 час)
            reminder_time = consultation_datetime - timedelta(hours=1)
            
            # Вычисляем задержку в секундах
            now = datetime.now()
            delay_seconds = (reminder_time - now).total_seconds()
            
            # Если напоминание должно быть в будущем
            if delay_seconds > 0:
                # Запускаем в отдельном потоке
                timer = threading.Timer(
                    delay_seconds, 
                    self._send_reminder, 
                    [booking_data, client_chat_id]
                )
                timer.daemon = True
                timer.start()
                
                print(f"⏰ Напоминание запланировано на {reminder_time}")
            else:
                print("⚠️ Время консультации уже прошло, напоминание не планируется")
                
        except Exception as e:
            print(f"❌ Ошибка планирования напоминания: {e}")
    
    def _send_reminder(self, booking_data: dict, client_chat_id: str):
        """Отправка запланированного напоминания"""
        try:
            print("🔔 Отправка запланированного напоминания...")
            
            # Отправляем админу
            self.notify_reminder_admin(booking_data)
            
            # Отправляем клиенту
            self.notify_reminder_client(client_chat_id, booking_data)
            
            print("✅ Напоминания отправлены!")
                
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания: {e}")

# Создаем экземпляр бота
telegram_bot = TelegramBotService()

# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С TELEGRAM В БАЗЕ
# ============================================================================

def save_telegram_chat_id(phone: str, chat_id: str):
    """Сохранение Telegram chat_id клиента"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        
        # Обновляем все записи клиента
        response = supabase.table('bookings')\
            .update({'telegram_chat_id': chat_id})\
            .eq('phone_hash', phone_hash)\
            .execute()
        
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения chat_id: {e}")
        return False

def get_client_telegram_chat_id(phone: str):
    """Получение Telegram chat_id клиента"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        
        response = supabase.table('bookings')\
            .select('telegram_chat_id')\
            .eq('phone_hash', phone_hash)\
            .not_.is_('telegram_chat_id', None)\
            .limit(1)\
            .execute()
        
        if response.data and response.data[0]['telegram_chat_id']:
            return response.data[0]['telegram_chat_id']
        return None
    except Exception as e:
        print(f"❌ Ошибка получения chat_id: {e}")
        return None

def get_upcoming_bookings_with_telegram(phone: str):
    """Получение предстоящих записей клиента"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        
        response = supabase.table('bookings')\
            .select('*')\
            .eq('phone_hash', phone_hash)\
            .eq('status', 'confirmed')\
            .gte('booking_date', datetime.now().date().isoformat())\
            .order('booking_date')\
            .order('booking_time')\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Ошибка получения записей: {e}")
        return []

def send_telegram_connection_test(chat_id: str, client_name: str):
    """Отправка тестового уведомления после подключения"""
    try:
        message = f"""
🔔 <b>ТЕСТОВОЕ УВЕДОМЛЕНИЕ</b>

Привет, {client_name}!

Это тестовое сообщение подтверждает, что вы успешно подключили уведомления в Telegram.

Теперь вы будете получать:
✅ Подтверждения записей
⏰ Напоминания за 1 час
❌ Уведомления об отменах

Отлично! Уведомления работают! 🎉
        """
        
        return telegram_bot.send_to_client(chat_id, message)
    except Exception as e:
        print(f"❌ Ошибка отправки тестового уведомления: {e}")
        return False

# ============================================================================
# МЕНЕДЖЕР УВЕДОМЛЕНИЙ
# ============================================================================

class NotificationManager:
    def __init__(self):
        self.bot = telegram_bot
    
    def notify_booking_created(self, booking_data: dict, client_chat_id: str = None):
        """Полный цикл уведомлений о новой записи"""
        results = {}
        
        # Уведомление администратору
        results['admin_notified'] = self.bot.notify_booking_created_admin(booking_data)
        
        # Уведомление клиенту (если указан chat_id)
        if client_chat_id:
            results['client_notified'] = self.bot.notify_booking_created_client(client_chat_id, booking_data)
            
            # Планируем напоминание за 1 час
            self.bot.schedule_reminder(booking_data, client_chat_id)
            results['reminder_scheduled'] = True
        
        return results
    
    def notify_booking_cancelled(self, booking_data: dict, client_chat_id: str = None):
        """Уведомления об отмене записи"""
        results = {}
        
        # Уведомление администратору
        results['admin_notified'] = self.bot.notify_booking_cancelled_admin(booking_data)
        
        # Уведомление клиенту (если указан chat_id)
        if client_chat_id:
            results['client_notified'] = self.bot.notify_booking_cancelled_client(client_chat_id, booking_data)
        
        return results
    
    def connect_client_telegram(self, phone: str, chat_id: str, client_name: str):
        """Подключение клиента к Telegram уведомлениям"""
        try:
            # Сохраняем chat_id в базе
            save_success = save_telegram_chat_id(phone, chat_id)
            
            if not save_success:
                return False
            
            # Получаем предстоящие записи
            upcoming_bookings = get_upcoming_bookings_with_telegram(phone)
            
            # Отправляем приветственное уведомление
            welcome_success = self.bot.send_welcome_notification(chat_id, client_name, upcoming_bookings)
            
            # Отправляем тестовое уведомление
            test_success = send_telegram_connection_test(chat_id, client_name)
            
            # Планируем напоминания для предстоящих записей
            for booking in upcoming_bookings:
                self.bot.schedule_reminder(booking, chat_id)
            
            return welcome_success or test_success
            
        except Exception as e:
            print(f"❌ Ошибка подключения Telegram: {e}")
            return False
    
    def send_upcoming_bookings(self, phone: str):
        """Отправка уведомления о предстоящих записях"""
        try:
            chat_id = get_client_telegram_chat_id(phone)
            if not chat_id:
                return False
            
            upcoming_bookings = get_upcoming_bookings_with_telegram(phone)
            if not upcoming_bookings:
                return False
            
            client_name = st.session_state.client_name
            
            return self.bot.send_upcoming_bookings_notification(chat_id, client_name, upcoming_bookings)
            
        except Exception as e:
            print(f"❌ Ошибка отправки предстоящих записей: {e}")
            return False

# Создаем менеджер уведомлений
notifier = NotificationManager()

# ============================================================================
# РАЗДЕЛ TELEGRAM В ЛИЧНОМ КАБИНЕТЕ
# ============================================================================

def render_telegram_section():
    """Отображение секции подключения Telegram"""
    st.markdown("### 💬 Уведомления в Telegram")
    
    # Получаем текущий chat_id клиента
    current_chat_id = get_client_telegram_chat_id(st.session_state.client_phone)
    
    if current_chat_id:
        # Telegram уже подключен
        st.markdown("""
        <div class="telegram-connected">
            <h4>✅ Telegram подключен!</h4>
            <p>Вы получаете уведомления о всех событиях</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.info("""
            **Вы получаете:**
            • ✅ Подтверждения новых записей
            • ⏰ Напоминания за 1 час до консультаций  
            • ❌ Уведомления об отменах
            """)
        
        with col2:
            if st.button("🔄 Отправить тест", use_container_width=True):
                if send_telegram_connection_test(current_chat_id, st.session_state.client_name):
                    st.success("✅ Тестовое уведомление отправлено!")
                else:
                    st.error("❌ Ошибка отправки")
        
        with col3:
            if st.button("📋 Мои записи", use_container_width=True):
                if notifier.send_upcoming_bookings(st.session_state.client_phone):
                    st.success("✅ Список записей отправлен!")
                else:
                    st.error("❌ Нет предстоящих записей")
        
        # Информация о предстоящих записях
        upcoming_bookings = get_upcoming_bookings_with_telegram(st.session_state.client_phone)
        if upcoming_bookings:
            st.markdown("#### 📅 Ваши предстоящие консультации:")
            for booking in upcoming_bookings:
                date = format_date(booking['booking_date'])
                time = booking['booking_time']
                st.write(f"• {date} в {time}")
        
    else:
        # Telegram не подключен
        st.markdown("""
        <div class="telegram-disconnected">
            <h4>⚠️ Telegram не подключен</h4>
            <p>Вы не получаете уведомления о записях и напоминания</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        ### 📱 Подключите Telegram за 2 минуты!
        
        **После подключения вы будете получать:**
        • ✅ Мгновенные подтверждения записей
        • ⏰ Автоматические напоминания за 1 час
        • ❌ Уведомления об отменах записей
        
        **Как подключить:**
        1. Нажмите кнопку "Подключить Telegram" ниже
        2. Откроется Telegram с нашим ботом
        3. Нажмите кнопку START / ЗАПУСТИТЬ
        4. Вернитесь сюда и введите ваш Chat ID
        """)
        
        # Ссылка на бота
        bot_link = telegram_bot.get_bot_link(st.session_state.client_phone)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(f"""
            <a href="{bot_link}" target="_blank">
                <button style="
                    background: #0088cc; 
                    color: white; 
                    padding: 15px; 
                    border: none; 
                    border-radius: 10px; 
                    font-size: 16px; 
                    cursor: pointer;
                    width: 100%;
                ">
                    📱 Подключить Telegram
                </button>
            </a>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            **После подключения:**
            1. Скопируйте ваш **Chat ID** из Telegram
            2. Вставьте в поле ниже
            3. Нажмите "Сохранить"
            
            *Как найти Chat ID?*
            - Напишите боту [@userinfobot](https://t.me/userinfobot) и он покажет ваш Chat ID
            """)
            
            with st.form("connect_telegram_form"):
                chat_id = st.text_input(
                    "Ваш Chat ID из Telegram:",
                    placeholder="123456789",
                    help="Цифровой ID, который вам выдаст бот"
                )
                
                submitted = st.form_submit_button("💾 Сохранить и подключить", use_container_width=True)
                
                if submitted:
                    if not chat_id:
                        st.error("❌ Введите Chat ID")
                    elif not chat_id.isdigit():
                        st.error("❌ Chat ID должен содержать только цифры")
                    else:
                        # Проверяем подключение
                        if telegram_bot.check_client_connection(chat_id):
                            # Сохраняем и подключаем
                            success = notifier.connect_client_telegram(
                                st.session_state.client_phone,
                                chat_id,
                                st.session_state.client_name
                            )
                            
                            if success:
                                st.success("🎉 Telegram успешно подключен! Вы будете получать уведомления.")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Ошибка при сохранении настроек")
                        else:
                            st.error("""
                            ❌ Не удалось подключиться!
                            
                            **Возможные причины:**
                            • Вы не нажали START в боте
                            • Неверный Chat ID
                            • Бот заблокирован
                            
                            **Что делать:**
                            1. Нажмите "Подключить Telegram"
                            2. В открывшемся боте нажмите START
                            3. Получите Chat ID командой `/id`
                            4. Введите его снова
                            """)
        
        # Альтернативный способ получения Chat ID
        with st.expander("🔍 Как получить Chat ID?"):
            st.markdown("""
            **Способ 1: Через нашего бота**
            1. Нажмите "Подключить Telegram" выше
            2. В открывшемся боте напишите `/id`
            3. Бот пришлет ваш Chat ID
            
            **Способ 2: Через @userinfobot**
            1. Найдите в Telegram `@userinfobot`
            2. Начните с ним диалог
            3. Он покажет ваш Chat ID
            
            **Способ 3: Вручную**
            - Откройте наш бот
            - Нажмите START
            - Скопируйте цифры из ссылки или напишите `/id`
            """)

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
# ============================================================================

st.set_page_config(**PAGE_CONFIG)
load_custom_css()

# Инициализация Supabase
supabase = init_supabase()

# Инициализация session state
def init_session_state():
    """Инициализация всех переменных session state"""
    defaults = {
        'admin_logged_in': False,
        'client_logged_in': False,
        'client_phone': "",
        'client_name': "",
        'current_tab': "Запись",
        'show_admin_login': False,
        'selected_time': None,
        'booking_date': None,
        'selected_client': None,
        'selected_client_name': None,
        'show_new_booking_form': False,
        'show_stats': False,
        'confirm_delete': {},
        'search_query': '',
        'auto_refresh': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================================================
# БИЗНЕС-ЛОГИКА: НАСТРОЙКИ
# ============================================================================

@st.cache_data(ttl=300)
def get_settings():
    """Получение настроек системы"""
    try:
        response = supabase.table('settings').select('*').eq('id', 1).execute()
        if response.data:
            settings = response.data[0]
            
            # Добавляем поля информационной панели, если их нет в БД
            default_info_settings = {
                'info_title': 'ℹ️ Информация',
                'info_work_hours': '🕐 Рабочее время:\n09:00 - 18:00',
                'info_session_duration': '⏱️ Длительность консультации:\n60 минут',
                'info_format': '💻 Формат:\nОнлайн или в кабинете',
                'info_contacts': '📞 Контакты:\n📱 +7 (999) 123-45-67\n📧 hello@psychologist.ru\n🌿 psychologist.ru',
                'info_additional': ''
            }
            
            for key, value in default_info_settings.items():
                if key not in settings:
                    settings[key] = value
            
            return settings
        else:
            # Создаем настройки по умолчанию
            default_settings = {
                'work_start': '09:00',
                'work_end': '18:00', 
                'session_duration': 60,
                'break_duration': 15,
                'info_title': 'ℹ️ Информация',
                'info_work_hours': '🕐 Рабочее время:\n09:00 - 18:00',
                'info_session_duration': '⏱️ Длительность консультации:\n60 минут',
                'info_format': '💻 Формат:\nОнлайн или в кабинете',
                'info_contacts': '📞 Контакты:\n📱 +7 (999) 123-45-67\n📧 hello@psychologist.ru\n🌿 psychologist.ru',
                'info_additional': ''
            }
            
            try:
                supabase.table('settings').insert({**default_settings, 'id': 1}).execute()
                return default_settings
            except Exception as insert_error:
                # Если не удалось вставить все поля, пробуем только основные
                basic_settings = {
                    'work_start': '09:00',
                    'work_end': '18:00', 
                    'session_duration': 60,
                    'break_duration': 15
                }
                supabase.table('settings').insert({**basic_settings, 'id': 1}).execute()
                return {**basic_settings, **default_info_settings}
                
    except Exception as e:
        st.error(f"❌ Ошибка получения настроек: {e}")
        # Возвращаем настройки по умолчанию
        return {
            'work_start': '09:00',
            'work_end': '18:00', 
            'session_duration': 60,
            'break_duration': 15,
            'info_title': 'ℹ️ Информация',
            'info_work_hours': '🕐 Рабочее время:\n09:00 - 18:00',
            'info_session_duration': '⏱️ Длительность консультации:\n60 минут',
            'info_format': '💻 Формат:\nОнлайн или в кабинете',
            'info_contacts': '📞 Контакты:\n📱 +7 (999) 123-45-67\n📧 hello@psychologist.ru\n🌿 psychologist.ru',
            'info_additional': ''
        }

def update_settings(work_start: str, work_end: str, session_duration: int):
    """Обновление настроек системы"""
    try:
        update_data = {
            'work_start': work_start,
            'work_end': work_end,
            'session_duration': session_duration
        }
        
        # Проверяем существование полей перед обновлением
        current_settings = get_settings()
        filtered_data = {k: v for k, v in update_data.items() if k in current_settings}
        
        if filtered_data:
            supabase.table('settings').update(filtered_data).eq('id', 1).execute()
            st.cache_data.clear()
            return True
        else:
            return False
    except Exception as e:
        st.error(f"❌ Ошибка обновления настроек: {e}")
        return False

def update_info_settings(info_data: dict):
    """Обновление настроек информационной панели"""
    try:
        # Сначала получаем текущие настройки
        current_settings = get_settings()
        
        # Обновляем только существующие поля
        update_data = {}
        for key, value in info_data.items():
            if key in current_settings:
                update_data[key] = value
        
        if update_data:
            supabase.table('settings').update(update_data).eq('id', 1).execute()
            st.cache_data.clear()
            return True
        else:
            st.error("❌ Нет полей для обновления")
            return False
            
    except Exception as e:
        st.error(f"❌ Ошибка обновления настроек информации: {e}")
        return False

def render_info_panel():
    """Отображение информационной панели с настраиваемым содержимым"""
    settings = get_settings()
    if not settings:
        return
    
    # Безопасное получение значений с fallback
    title = settings.get('info_title', 'ℹ️ Информация')
    work_hours = settings.get('info_work_hours', '🕐 Рабочее время:\n09:00 - 18:00')
    session_duration = settings.get('info_session_duration', '⏱️ Длительность консультации:\n60 минут')
    format_info = settings.get('info_format', '💻 Формат:\nОнлайн или в кабинете')
    contacts = settings.get('info_contacts', '📞 Контакты:\n📱 +7 (999) 123-45-67\n📧 hello@psychologist.ru\n🌿 psychologist.ru')
    additional = settings.get('info_additional', '')
    
    # Формируем HTML содержимое
    info_html = f"""
    <div class="info-box">
        <h4>{title}</h4>
        <p><strong>{work_hours.replace(chr(10), '<br>')}</strong></p>
        <p><strong>{session_duration.replace(chr(10), '<br>')}</strong></p>
        <p><strong>{format_info.replace(chr(10), '<br>')}</strong></p>
        <hr>
        <h4>📞 Контакты</h4>
        <p>{contacts.replace(chr(10), '<br>')}</p>
    """
    
    if additional and additional.strip():
        info_html += f'<p>{additional.replace(chr(10), "<br>")}</p>'
    
    info_html += "</div>"
    
    st.markdown(info_html, unsafe_allow_html=True)

# ============================================================================
# БИЗНЕС-ЛОГИКА: КЛИЕНТЫ
# ============================================================================

@st.cache_data(ttl=60)
def get_client_info(phone: str):
    """Получение информации о клиенте"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        response = supabase.table('bookings').select('client_name, client_email, client_telegram')\
            .eq('phone_hash', phone_hash)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data:
            result = response.data[0]
            return {
                'name': result['client_name'],
                'email': result['client_email'],
                'telegram': result['client_telegram']
            }
        return None
    except Exception as e:
        st.error(f"❌ Ошибка получения информации о клиенте: {e}")
        return None

def has_active_booking(phone: str) -> bool:
    """Проверка наличия активной записи"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        response = supabase.table('bookings')\
            .select('id', count='exact')\
            .eq('phone_hash', phone_hash)\
            .eq('status', 'confirmed')\
            .gte('booking_date', datetime.now().date().isoformat())\
            .execute()
        
        return response.count > 0
    except Exception as e:
        st.error(f"❌ Ошибка проверки активных записей: {e}")
        return False

@st.cache_data(ttl=60)
def get_client_bookings(phone: str):
    """Получение всех записей клиента"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        response = supabase.table('bookings')\
            .select('*')\
            .eq('phone_hash', phone_hash)\
            .order('booking_date', desc=True)\
            .order('booking_time', desc=True)\
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Ошибка получения записей клиента: {e}")
        return pd.DataFrame()

def get_upcoming_client_booking(phone: str):
    """Получение ближайшей записи клиента"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        response = supabase.table('bookings')\
            .select('*')\
            .eq('phone_hash', phone_hash)\
            .eq('status', 'confirmed')\
            .gte('booking_date', datetime.now().date().isoformat())\
            .order('booking_date')\
            .order('booking_time')\
            .limit(1)\
            .execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"❌ Ошибка получения ближайшей записи: {e}")
        return None

@st.cache_data(ttl=120)
def get_all_clients():
    """Получение списка всех уникальных клиентов"""
    try:
        response = supabase.table('bookings')\
            .select('client_name, client_phone, client_email, client_telegram, phone_hash')\
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            clients_df = df.groupby('phone_hash').first().reset_index()
            
            clients_data = []
            for phone_hash in clients_df['phone_hash'].unique():
                client_row = clients_df[clients_df['phone_hash'] == phone_hash].iloc[0]
                
                bookings_response = supabase.table('bookings')\
                    .select('id, status, booking_date')\
                    .eq('phone_hash', phone_hash)\
                    .execute()
                
                if bookings_response.data:
                    bookings_df = pd.DataFrame(bookings_response.data)
                    total = len(bookings_df)
                    upcoming = len(bookings_df[bookings_df['status'] == 'confirmed']) if 'status' in bookings_df.columns else 0
                    completed = len(bookings_df[bookings_df['status'] == 'completed']) if 'status' in bookings_df.columns else 0
                    cancelled = len(bookings_df[bookings_df['status'] == 'cancelled']) if 'status' in bookings_df.columns else 0
                    first_booking = bookings_df['booking_date'].min() if 'booking_date' in bookings_df.columns else ''
                    last_booking = bookings_df['booking_date'].max() if 'booking_date' in bookings_df.columns else ''
                else:
                    total = upcoming = completed = cancelled = 0
                    first_booking = last_booking = ''
                
                client_data = {
                    'phone_hash': phone_hash,
                    'client_name': client_row['client_name'],
                    'client_phone': format_phone(client_row['client_phone']),
                    'client_email': client_row['client_email'],
                    'client_telegram': client_row['client_telegram'],
                    'total_bookings': total,
                    'upcoming_bookings': upcoming,
                    'completed_bookings': completed,
                    'cancelled_bookings': cancelled,
                    'first_booking': first_booking,
                    'last_booking': last_booking
                }
                clients_data.append(client_data)
            
            return pd.DataFrame(clients_data)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Ошибка получения списка клиентов: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_client_booking_history(phone_hash: str):
    """Получение истории записей конкретного клиента"""
    try:
        response = supabase.table('bookings')\
            .select('*')\
            .eq('phone_hash', phone_hash)\
            .order('booking_date', desc=True)\
            .order('booking_time', desc=True)\
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Ошибка получения истории записей: {e}")
        return pd.DataFrame()

# ============================================================================
# БИЗНЕС-ЛОГИКА: ЗАПИСИ
# ============================================================================

def is_time_available(selected_date: str, time_slot: str) -> tuple:
    """Проверка доступности времени"""
    try:
        booking_datetime = datetime.strptime(f"{selected_date} {time_slot}", "%Y-%m-%d %H:%M")
        time_diff = (booking_datetime - datetime.now()).total_seconds()
        
        min_advance = BOOKING_RULES["MIN_ADVANCE_HOURS"] * 3600
        
        if time_diff < 0:
            return False, "❌ Это время уже прошло"
        elif time_diff < min_advance:
            return False, f"❌ Запись возможна не менее чем за {BOOKING_RULES['MIN_ADVANCE_HOURS']} час до начала"
        else:
            return True, "✅ Время доступно"
    except ValueError:
        return False, "❌ Неверный формат времени"

def get_available_slots(date: str) -> list:
    """Получение доступных временных слотов"""
    try:
        settings = get_settings()
        if not settings:
            return []
            
        work_start = datetime.strptime(settings['work_start'], '%H:%M').time()
        work_end = datetime.strptime(settings['work_end'], '%H:%M').time()
        session_duration = settings['session_duration']
        
        # Проверка блокировки дня
        blocked_response = supabase.table('blocked_slots')\
            .select('id')\
            .eq('block_date', date)\
            .is_('block_time', None)\
            .execute()
        
        if blocked_response.data:
            return []
        
        # Получаем занятые слоты
        booked_response = supabase.table('bookings')\
            .select('booking_time')\
            .eq('booking_date', date)\
            .neq('status', 'cancelled')\
            .execute()
        
        booked_slots = [item['booking_time'] for item in booked_response.data] if booked_response.data else []
        
        # Получаем заблокированные слоты
        blocked_slots_response = supabase.table('blocked_slots')\
            .select('block_time')\
            .eq('block_date', date)\
            .not_.is_('block_time', None)\
            .execute()
        
        blocked_slots = [item['block_time'] for item in blocked_slots_response.data] if blocked_slots_response.data else []
        
        # Генерируем доступные слоты
        slots = []
        current_time = datetime.combine(datetime.today(), work_start)
        end_time = datetime.combine(datetime.today(), work_end)
        
        while current_time < end_time:
            time_slot = current_time.strftime('%H:%M')
            
            time_available, _ = is_time_available(date, time_slot)
            
            if (time_slot not in booked_slots and 
                time_slot not in blocked_slots and 
                time_available):
                slots.append(time_slot)
            
            current_time += timedelta(minutes=session_duration)
        
        return slots
    except Exception as e:
        st.error(f"❌ Ошибка получения доступных слотов: {e}")
        return []

def create_booking(client_name: str, client_phone: str, client_email: str, 
                  client_telegram: str, date: str, time_slot: str, notes: str = "",
                  client_chat_id: str = None) -> tuple:
    """Создание записи с уведомлениями"""
    try:
        # Проверка активной записи
        if has_active_booking(client_phone):
            return False, "❌ У вас уже есть активная запись"
        
        # Проверка доступности времени
        time_available, reason = is_time_available(date, time_slot)
        if not time_available:
            return False, reason
        
        phone_hash = hash_password(normalize_phone(client_phone))
        
        response = supabase.table('bookings').insert({
            'client_name': client_name,
            'client_phone': client_phone,
            'client_email': client_email,
            'client_telegram': client_telegram,
            'booking_date': date,
            'booking_time': time_slot,
            'notes': notes,
            'phone_hash': phone_hash,
            'status': 'confirmed',
            'telegram_chat_id': client_chat_id  # 🔥 СОХРАНЯЕМ CHAT_ID
        }).execute()
        
        if response.data:
            booking_data = response.data[0]
            
            # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЯ О НОВОЙ ЗАПИСИ
            notification_results = notifier.notify_booking_created(booking_data, client_chat_id)
            
            # Показываем статус уведомлений
            if notification_results.get('admin_notified'):
                st.success("✅ Администратор уведомлен")
            if notification_results.get('client_notified') and client_chat_id:
                st.success("✅ Уведомление отправлено в Telegram")
            if notification_results.get('reminder_scheduled') and client_chat_id:
                st.success("✅ Напоминание запланировано за 1 час")
            
            return True, "✅ Запись успешно создана"
        else:
            return False, "❌ Ошибка при создании записи"
            
    except Exception as e:
        if "duplicate key" in str(e) or "unique constraint" in str(e):
            return False, "❌ Это время уже занято"
        return False, f"❌ Ошибка: {str(e)}"

def create_booking_by_admin(client_name: str, client_phone: str, client_email: str, 
                           client_telegram: str, date: str, time_slot: str, notes: str = ""):
    """Создание записи администратором"""
    try:
        phone_hash = hash_password(normalize_phone(client_phone))
        
        response = supabase.table('bookings').insert({
            'client_name': client_name,
            'client_phone': client_phone,
            'client_email': client_email,
            'client_telegram': client_telegram,
            'booking_date': date,
            'booking_time': time_slot,
            'notes': notes,
            'phone_hash': phone_hash,
            'status': 'confirmed'
        }).execute()
        
        if response.data:
            booking_data = response.data[0]
            
            # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЯ АДМИНУ
            notifier.notify_booking_created(booking_data)
            
            return True, "✅ Запись успешно создана"
        else:
            return False, "❌ Ошибка при создании записи"
            
    except Exception as e:
        if "duplicate key" in str(e) or "unique constraint" in str(e):
            return False, "❌ Это время уже занято"
        return False, f"❌ Ошибка: {str(e)}"

def cancel_booking(booking_id: int, phone: str, client_chat_id: str = None) -> tuple:
    """Отмена записи с уведомлениями"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        
        # Получаем информацию о записи
        response = supabase.table('bookings')\
            .select('*')\
            .eq('id', booking_id)\
            .eq('phone_hash', phone_hash)\
            .execute()
        
        if not response.data:
            return False, "Запись не найдена"
        
        booking = response.data[0]
        
        # Проверяем время до начала
        time_until = calculate_time_until(booking['booking_date'], booking['booking_time'])
        min_cancel = BOOKING_RULES["MIN_CANCEL_MINUTES"] * 60
        
        if time_until.total_seconds() < min_cancel:
            return False, f"Отмена возможна не позднее чем за {BOOKING_RULES['MIN_CANCEL_MINUTES']} минут"
        
        # Отменяем запись
        supabase.table('bookings')\
            .update({'status': 'cancelled'})\
            .eq('id', booking_id)\
            .execute()
        
        # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЯ ОБ ОТМЕНЕ
        updated_booking = {**booking, 'status': 'cancelled'}
        notification_results = notifier.notify_booking_cancelled(updated_booking, client_chat_id)
        
        # Показываем статус уведомлений
        if notification_results.get('admin_notified'):
            st.success("✅ Администратор уведомлен об отмене")
        if notification_results.get('client_notified') and client_chat_id:
            st.success("✅ Клиент уведомлен об отмене")
        
        return True, "Запись успешно отменена"
        
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

def delete_booking(booking_id: int):
    """Удаление записи (для админа)"""
    try:
        supabase.table('bookings').delete().eq('id', booking_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Ошибка удаления записи: {e}")
        return False

def get_all_bookings(date_from: str = None, date_to: str = None):
    """Получение всех записей"""
    try:
        query = supabase.table('bookings').select('*')
        
        if date_from and date_to:
            query = query.gte('booking_date', date_from).lte('booking_date', date_to)
        elif date_from:
            query = query.gte('booking_date', date_from)
        else:
            query = query.order('booking_date', desc=True).order('booking_time', desc=True)
        
        response = query.execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Ошибка получения записей: {e}")
        return pd.DataFrame()

# ============================================================================
# БИЗНЕС-ЛОГИКА: УПРАВЛЕНИЕ ЗАПИСЯМИ (админ)
# ============================================================================

def update_booking_datetime(booking_id: int, new_date: str, new_time: str):
    """Обновление даты и времени записи"""
    try:
        response = supabase.table('bookings').update({
            'booking_date': new_date,
            'booking_time': new_time
        }).eq('id', booking_id).execute()
        
        if response.data:
            return True, "✅ Время записи обновлено"
        else:
            return False, "❌ Ошибка обновления времени"
    except Exception as e:
        if "duplicate key" in str(e) or "unique constraint" in str(e):
            return False, "❌ Это время уже занято"
        return False, f"❌ Ошибка: {str(e)}"

def update_booking_notes(booking_id: int, new_notes: str):
    """Обновление комментария к записи"""
    try:
        supabase.table('bookings').update({'notes': new_notes}).eq('id', booking_id).execute()
        return True, "✅ Комментарий обновлен"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

def update_booking_status(booking_id: int, new_status: str):
    """Обновление статуса записи"""
    try:
        # Получаем текущие данные
        response = supabase.table('bookings')\
            .select('*')\
            .eq('id', booking_id)\
            .execute()
        
        if not response.data:
            return False, "Запись не найдена"
        
        old_booking = response.data[0]
        
        # Обновляем статус
        supabase.table('bookings').update({'status': new_status}).eq('id', booking_id).execute()
        
        # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЯ
        updated_booking = {**old_booking, 'status': new_status}
        
        if new_status == 'completed':
            notifier.notify_booking_cancelled(updated_booking)
        elif new_status == 'cancelled':
            notifier.notify_booking_cancelled(updated_booking)
        
        return True, f"✅ Статус изменен на {STATUS_DISPLAY[new_status]['text']}"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

# ============================================================================
# БИЗНЕС-ЛОГИКА: БЛОКИРОВКИ
# ============================================================================

def block_date(date: str, reason: str = "Выходной") -> bool:
    """Блокировка дня"""
    try:
        response = supabase.table('blocked_slots').insert({
            'block_date': date,
            'reason': reason
        }).execute()
        
        return bool(response.data)
    except Exception as e:
        if "duplicate key" in str(e) or "unique constraint" in str(e):
            return False
        st.error(f"❌ Ошибка блокировки дня: {e}")
        return False

def unblock_date(date: str):
    """Разблокировка дня"""
    try:
        supabase.table('blocked_slots')\
            .delete()\
            .eq('block_date', date)\
            .is_('block_time', None)\
            .execute()
    except Exception as e:
        st.error(f"❌ Ошибка разблокировки дня: {e}")

def get_blocked_dates():
    """Получение заблокированных дат"""
    try:
        response = supabase.table('blocked_slots')\
            .select('block_date, reason')\
            .is_('block_time', None)\
            .order('block_date')\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Ошибка получения заблокированных дат: {e}")
        return []

def block_time_slot(date: str, time_slot: str, reason: str = "Технические работы") -> bool:
    """Блокировка временного слота"""
    try:
        response = supabase.table('blocked_slots').insert({
            'block_date': date,
            'block_time': time_slot,
            'reason': reason
        }).execute()
        
        return bool(response.data)
    except Exception as e:
        if "duplicate key" in str(e) or "unique constraint" in str(e):
            return False
        st.error(f"❌ Ошибка блокировки времени: {e}")
        return False

def unblock_time_slot(block_id: int):
    """Разблокировка временного слота"""
    try:
        supabase.table('blocked_slots').delete().eq('id', block_id).execute()
    except Exception as e:
        st.error(f"❌ Ошибка разблокировки времени: {e}")

def get_blocked_slots():
    """Получение заблокированных слотов"""
    try:
        response = supabase.table('blocked_slots')\
            .select('*')\
            .not_.is_('block_time', None)\
            .order('block_date')\
            .order('block_time')\
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Ошибка получения заблокированных слотов: {e}")
        return pd.DataFrame()

# ============================================================================
# СТАТИСТИКА И АНАЛИТИКА
# ============================================================================

@st.cache_data(ttl=60)
def get_stats():
    """Получение основной статистики"""
    try:
        # Общее количество записей
        total_response = supabase.table('bookings').select('id', count='exact').execute()
        total = total_response.count or 0
        
        # Предстоящие записи
        upcoming_response = supabase.table('bookings')\
            .select('id', count='exact')\
            .eq('status', 'confirmed')\
            .gte('booking_date', datetime.now().date().isoformat())\
            .execute()
        upcoming = upcoming_response.count or 0
        
        # Записи за текущий месяц
        current_date = datetime.now()
        month_start = current_date.replace(day=1).date().isoformat()
        month_end = get_month_end(current_date.year, current_date.month)
        
        monthly_response = supabase.table('bookings')\
            .select('id', count='exact')\
            .gte('booking_date', month_start)\
            .lte('booking_date', month_end)\
            .execute()
        this_month = monthly_response.count or 0
        
        # Записи за последние 7 дней
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        weekly_response = supabase.table('bookings')\
            .select('id', count='exact')\
            .gte('booking_date', week_ago)\
            .execute()
        this_week = weekly_response.count or 0
        
        return total, upcoming, this_month, this_week
    except Exception as e:
        st.error(f"❌ Ошибка получения статистики: {e}")
        return 0, 0, 0, 0

# ============================================================================
# АВТОРИЗАЦИЯ
# ============================================================================

def check_admin_password(password: str) -> bool:
    """Проверка пароля администратора"""
    return hash_password(password) == ADMIN_PASSWORD_HASH

def client_login(phone: str) -> bool:
    """Авторизация клиента"""
    try:
        phone_hash = hash_password(normalize_phone(phone))
        response = supabase.table('bookings')\
            .select('client_name')\
            .eq('phone_hash', phone_hash)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data:
            st.session_state.client_logged_in = True
            st.session_state.client_phone = phone
            st.session_state.client_name = response.data[0]['client_name']
            return True
        return False
    except Exception as e:
        st.error(f"❌ Ошибка авторизации: {e}")
        return False

def client_logout():
    """Выход клиента"""
    st.session_state.client_logged_in = False
    st.session_state.client_phone = ""
    st.session_state.client_name = ""
    st.session_state.current_tab = "Запись"

def admin_login():
    """Вход администратора"""
    st.session_state.admin_logged_in = True
    st.session_state.show_admin_login = False

def admin_logout():
    """Выход администратора"""
    st.session_state.admin_logged_in = False

# ============================================================================
# UI КОМПОНЕНТЫ
# ============================================================================

def render_booking_card(row, date, show_actions=True):
    """Отрисовка карточки записи"""
    status_info = STATUS_DISPLAY.get(row['status'], STATUS_DISPLAY['confirmed'])
    
    unique_key = f"delete_{date}_{row['booking_time']}_{row['id']}"
    
    with st.container():
        col1, col2 = st.columns([4, 1]) if show_actions else st.columns([1])
        
        with col1:
            st.markdown(f"**{status_info['emoji']} {row['booking_time']} - {row['client_name']}**")
            st.text(f"📱 {row['client_phone']}")
            
            if row.get('client_email'):
                st.text(f"📧 {row['client_email']}")
                
            if row.get('client_telegram'):
                st.text(f"💬 {row['client_telegram']}")
                
            if row.get('notes'):
                st.text(f"💭 {row['notes']}")
            
            st.markdown(f"**Статус:** <span style='color: {status_info['color']};'>{status_info['text']}</span>", 
                       unsafe_allow_html=True)
        
        if show_actions and col2:
            with col2:
                if st.button("🗑️ Удалить", key=unique_key, use_container_width=True):
                    delete_booking(row['id'])
                    st.success("✅ Удалено!")
                    st.rerun()
        
        st.markdown("---")

def render_time_slots(available_slots, key_prefix="slot"):
    """Отрисовка временных слотов"""
    if not available_slots:
        st.warning("😔 На выбранную дату нет свободных слотов")
        return None
    
    st.markdown("#### 🕐 Выберите время")
    st.info("💡 Доступные для записи временные слотов")
    
    cols = st.columns(4)
    for idx, time_slot in enumerate(available_slots):
        with cols[idx % 4]:
            if st.button(f"🕐 {time_slot}", key=f"{key_prefix}_{time_slot}", 
                        use_container_width=True, type="primary"):
                st.session_state.selected_time = time_slot
                st.rerun()
    
    return st.session_state.get('selected_time')

# ============================================================================
# БОКОВАЯ ПАНЕЛЬ
# ============================================================================

with st.sidebar:
    st.markdown("# 🌿 Навигация")
    
    if st.session_state.client_logged_in:
        # КЛИЕНТ ВОШЕЛ В СИСТЕМУ
        if st.session_state.client_name:
            st.markdown(f"### 👋 {st.session_state.client_name}!")
        
        # 🔥 ОБНОВЛЯЕМ МЕНЮ - ДОБАВЛЯЕМ ВКЛАДКУ "УВЕДОМЛЕНИЯ"
        tabs = st.radio(
            "Меню:",
            ["👁️ Текущая запись", "👤 Профиль", "💬 Уведомления", "📅 Новая запись", "📊 История записей"],  # 🔥 ДОБАВИЛИ
            key="client_tabs"
        )
        st.session_state.current_tab = tabs
        
        # Показываем статус Telegram
        telegram_connected = get_client_telegram_chat_id(st.session_state.client_phone)
        if telegram_connected:
            st.success("🔔 Уведомления подключены")
        else:
            st.warning("🔕 Нет уведомлений")
        
        st.markdown("---")
        st.markdown("### 🔐 Безопасность")
        st.info("👤 Режим клиента")
        
        if st.button("🚪 Выйти", use_container_width=True):
            client_logout()
            st.rerun()
    
    elif st.session_state.admin_logged_in:
        # АДМИНИСТРАТОР ВОШЕЛ В СИСТЕМУ
        st.markdown("### 📊 Статистика")
        total, upcoming, this_month, this_week = get_stats()
        st.metric("📋 Всего", total)
        st.metric("⏰ Предстоящих", upcoming)
        st.metric("📅 За месяц", this_month)
        
        st.markdown("---")
        st.markdown("### 👩‍💼 Администратор")
        st.success("✅ Вы зашли как администратор")
        
        if st.button("🚪 Выйти", use_container_width=True):
            admin_logout()
            st.rerun()
    
    else:
        # НИКТО НЕ ВОШЕЛ В СИСТЕМУ
        st.markdown("### 👤 Для пользователя")
        st.info("Для записи выберите время и заполните форму или войдите в личный кабинет")
    
    # РАЗДЕЛ АДМИНИСТРАТОРА
    st.markdown("---")
    
    if not st.session_state.client_logged_in and not st.session_state.admin_logged_in:
        st.markdown("### 👩‍💼 Администратор")
        
        if st.button("🔐 Вход для администратора", use_container_width=True, type="secondary"):
            st.session_state.show_admin_login = True
            st.rerun()
        
        if st.session_state.show_admin_login:
            with st.form("admin_sidebar_login", clear_on_submit=True):
                password = st.text_input("Пароль администратора", type="password")
                submit = st.form_submit_button("Войти", use_container_width=True)
                
                if submit:
                    if password and check_admin_password(password):
                        admin_login()
                        st.success("✅ Добро пожаловать!")
                        st.rerun()
                    elif password:
                        st.error("❌ Неверный пароль!")
            
            if st.button("❌ Отмена", use_container_width=True, type="secondary"):
                st.session_state.show_admin_login = False
                st.rerun()

# ============================================================================
# ПРОВЕРКА ПОДКЛЮЧЕНИЯ К SUPABASE
# ============================================================================

if supabase is None:
    st.error("""
    ❌ Не удалось подключиться к Supabase. Пожалуйста, проверьте:
    
    1. **Переменные окружения** SUPABASE_URL и SUPABASE_KEY
    2. **Настройки проекта** в панели управления Supabase
    3. **Сетевые настройки** и доступ к интернету
    
    Для локальной разработки создайте файл `.env` с переменными:
    ```
    SUPABASE_URL=your_project_url
    SUPABASE_KEY=your_anon_key
    ```
    """)
    st.stop()

# ============================================================================
# ГЛАВНАЯ СТРАНИЦА: АДМИН-ПАНЕЛЬ
# ============================================================================

if st.session_state.admin_logged_in:
    st.title("👩‍💼 Панель управления")
    
    tabs = st.tabs(["📋 Записи", "👥 Клиенты", "⚙️ Настройки", "🚫 Блокировки", "📊 Аналитика", "🔔 Уведомления"])
    
    # Вкладка Записи
    with tabs[0]:
        st.markdown("### 📋 Управление записями")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            date_filter = st.selectbox(
                "📅 Период отображения",
                ["Все даты", "Сегодня", "На неделю", "На месяц"]
            )
        with col2:
            if st.button("🔄 Обновить данные", use_container_width=True):
                st.rerun()
        
        today = datetime.now().date()
        
        if date_filter == "Сегодня":
            date_from = str(today)
            date_to = str(today)
        elif date_filter == "На неделю":
            date_from = str(today)
            date_to = str(today + timedelta(days=7))
        elif date_filter == "На месяц":
            date_from = str(today)
            date_to = str(today + timedelta(days=30))
        else:
            date_from = None
            date_to = None
        
        df = get_all_bookings(date_from, date_to)
        
        if not df.empty:
            if date_from and date_to:
                df = df[(df['booking_date'] >= date_from) & (df['booking_date'] <= date_to)]
            elif date_from:
                df = df[df['booking_date'] >= date_from]
            
            df = df.sort_values(['booking_date', 'booking_time'], ascending=[True, True])
            
            st.info(f"📊 Найдено записей: {len(df)}")
            
            if not df.empty:
                df['booking_date'] = pd.to_datetime(df['booking_date']).dt.strftime('%d.%m.%Y')
                
                for date in sorted(df['booking_date'].unique()):
                    st.markdown(f"#### 📅 {date}")
                    date_bookings = df[df['booking_date'] == date]
                    
                    for idx, row in date_bookings.iterrows():
                        render_booking_card(row, date)
                    
                    st.markdown("---")
            else:
                st.info("📭 Нет записей для отображения по выбранным фильтрам")
        else:
            st.info("📭 Нет записей для отображения")
    
    # Вкладка Клиенты
    with tabs[1]:
        st.markdown("### 👥 База клиентов")
        
        # Поиск и фильтры
        st.markdown("#### 🔍 Поиск и фильтры")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("Поиск по имени или телефону", placeholder="Введите имя или телефон...", key="client_search")
        with col2:
            show_only_active = st.checkbox("Только с предстоящими записями", value=False, key="active_filter")
        
        # Кнопки действий
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn1:
            if st.button("🔄 Обновить список", use_container_width=True):
                st.rerun()
        with col_btn2:
            if st.button("📊 Статистика", use_container_width=True):
                st.session_state.show_stats = not st.session_state.get('show_stats', False)
        with col_btn3:
            if st.button("➕ Новая запись", use_container_width=True, type="primary"):
                st.session_state.show_new_booking_form = True
        
        # Форма создания новой записи
        if st.session_state.get('show_new_booking_form'):
            st.markdown("---")
            st.markdown("#### 📝 Создание новой записи")
            
            with st.form("new_booking_admin_form"):
                st.markdown("**Информация о клиенте:**")
                col_a, col_b = st.columns(2)
                with col_a:
                    new_client_name = st.text_input("👤 Имя клиента *", placeholder="Иван Иванов", key="new_client_name")
                    new_client_email = st.text_input("📧 Email", placeholder="example@mail.com", key="new_client_email")
                with col_b:
                    new_client_phone = st.text_input("📱 Телефон *", placeholder="+7 (999) 123-45-67", key="new_client_phone")
                    new_client_telegram = st.text_input("💬 Telegram", placeholder="@username", key="new_client_telegram")
                
                st.markdown("**Детали записи:**")
                col_c, col_d = st.columns(2)
                with col_c:
                    booking_date = st.date_input("📅 Дата записи", min_value=datetime.now().date(), 
                                               max_value=datetime.now().date() + timedelta(days=30), key="admin_booking_date")
                with col_d:
                    booking_time = st.time_input("🕐 Время записи", value=datetime.strptime("09:00", "%H:%M").time(), key="admin_booking_time")
                
                booking_notes = st.text_area("💭 Причина встречи / комментарий", height=100, placeholder="Опишите причину обращения или дополнительные пожелания...", key="admin_booking_notes")
                
                col_submit, col_cancel = st.columns([1, 1])
                with col_submit:
                    submit_booking = st.form_submit_button("✅ Создать запись", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("❌ Отмена", use_container_width=True):
                        st.session_state.show_new_booking_form = False
                        st.rerun()
                
                if submit_booking:
                    if not new_client_name or not new_client_phone:
                        st.error("❌ Заполните имя и телефон клиента")
                    else:
                        success, message = create_booking_by_admin(
                            new_client_name, new_client_phone, new_client_email,
                            new_client_telegram, str(booking_date), booking_time.strftime("%H:%M"), booking_notes
                        )
                        if success:
                            st.success(message)
                            st.session_state.show_new_booking_form = False
                            st.rerun()
                        else:
                            st.error(message)
        
        # Получаем данные о клиентах
        clients_df = get_all_clients()
        
        if not clients_df.empty:
            # Применяем фильтры
            if search_query:
                mask = (clients_df['client_name'].str.contains(search_query, case=False, na=False)) | \
                       (clients_df['client_phone'].str.contains(search_query, case=False, na=False))
                clients_df = clients_df[mask]
            
            if show_only_active:
                clients_df = clients_df[clients_df['upcoming_bookings'] > 0]
            
            st.info(f"📊 Найдено клиентов: {len(clients_df)}")
            
            # Быстрая статистика
            if st.session_state.get('show_stats'):
                st.markdown("---")
                st.markdown("##### 📈 Быстрая статистика")
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                with stat_col1:
                    st.metric("Всего клиентов", len(clients_df))
                with stat_col2:
                    active_clients = len(clients_df[clients_df['upcoming_bookings'] > 0])
                    st.metric("Активных", active_clients)
                with stat_col3:
                    avg_bookings = clients_df['total_bookings'].mean()
                    st.metric("Среднее записей", f"{avg_bookings:.1f}")
                with stat_col4:
                    total_bookings = clients_df['total_bookings'].sum()
                    st.metric("Всего записей", total_bookings)
            
            # Отображаем клиентов
            for idx, client in clients_df.iterrows():
                with st.expander(f"👤 {client['client_name']} - 📱 {client['client_phone']} | 📅 Записей: {client['total_bookings']}", expanded=False):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown("**Контактная информация:**")
                        st.write(f"📧 Email: {client['client_email'] or 'Не указан'}")
                        st.write(f"💬 Telegram: {client['client_telegram'] or 'Не указан'}")
                        
                        st.markdown("**Статистика:**")
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        with col_stat1:
                            st.metric("Всего записей", client['total_bookings'])
                        with col_stat2:
                            st.metric("Предстоящие", client['upcoming_bookings'])
                        with col_stat3:
                            st.metric("Завершено", client['completed_bookings'])
                        with col_stat4:
                            st.metric("Отменено", client['cancelled_bookings'])
                    
                    with col2:
                        st.markdown("**Даты:**")
                        first_booking = datetime.strptime(client['first_booking'][:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                        last_booking = datetime.strptime(client['last_booking'][:10], '%Y-%m-%d').strftime('%d.%m.%Y')
                        st.write(f"📅 Первая запись: {first_booking}")
                        st.write(f"📅 Последняя запись: {last_booking}")
                    
                    with col3:
                        if st.button("📋 История записей", key=f"history_{client['phone_hash']}", use_container_width=True):
                            st.session_state.selected_client = client['phone_hash']
                            st.session_state.selected_client_name = client['client_name']
                    
                    # История записей выбранного клиента
                    if st.session_state.get('selected_client') == client['phone_hash']:
                        st.markdown("---")
                        st.markdown(f"#### 📋 История записей: {client['client_name']}")
                        
                        history_df = get_client_booking_history(client['phone_hash'])
                        if not history_df.empty:
                            # Форматируем даты
                            history_df['booking_date'] = pd.to_datetime(history_df['booking_date'])
                            history_df['formatted_date'] = history_df['booking_date'].dt.strftime('%d.%m.%Y')
                            history_df['created_at'] = pd.to_datetime(history_df['created_at']).dt.strftime('%d.%m.%Y %H:%M')
                            
                            # Отображаем историю с возможностью редактирования
                            for _, booking in history_df.iterrows():
                                status_info = STATUS_DISPLAY.get(booking['status'], STATUS_DISPLAY['confirmed'])
                                
                                with st.container():
                                    col_hist1, col_hist2, col_hist3 = st.columns([3, 1, 1])
                                    
                                    with col_hist1:
                                        st.write(f"**{booking['formatted_date']} {booking['booking_time']}** - {status_info['emoji']} {status_info['text']}")
                                        if booking['notes']:
                                            st.info(f"💭 {booking['notes']}")
                                    
                                    with col_hist2:
                                        st.write(f"📅 Записано: {booking['created_at']}")
                                    
                                    with col_hist3:
                                        # Меню управления записью
                                        with st.popover("⚙️ Управление", use_container_width=True):
                                            # Изменение времени
                                            st.markdown("**🕐 Перенести запись:**")
                                            new_date = st.date_input("Новая дата", 
                                                                   value=booking['booking_date'].date(),
                                                                   min_value=datetime.now().date(),
                                                                   key=f"date_{booking['id']}")
                                            new_time = st.time_input("Новое время", 
                                                                   value=datetime.strptime(booking['booking_time'], "%H:%M").time(),
                                                                   key=f"time_{booking['id']}")
                                            if st.button("🕐 Перенести", key=f"reschedule_{booking['id']}", use_container_width=True):
                                                success, message = update_booking_datetime(
                                                    booking['id'], str(new_date), new_time.strftime("%H:%M")
                                                )
                                                if success:
                                                    st.success(message)
                                                    st.rerun()
                                                else:
                                                    st.error(message)
                                            
                                            st.markdown("---")
                                            
                                            # Изменение комментария
                                            st.markdown("**💭 Изменить комментарий:**")
                                            new_notes = st.text_area("Новый комментарий", 
                                                                   value=booking['notes'] or "",
                                                                   height=80,
                                                                   key=f"notes_{booking['id']}")
                                            if st.button("💾 Сохранить", key=f"save_notes_{booking['id']}", use_container_width=True):
                                                success, message = update_booking_notes(booking['id'], new_notes)
                                                if success:
                                                    st.success(message)
                                                    st.rerun()
                                            
                                            st.markdown("---")
                                            
                                            # Изменение статуса
                                            st.markdown("**📊 Изменить статус:**")
                                            status_options = {
                                                'confirmed': '✅ Подтверждена',
                                                'cancelled': '❌ Отменена', 
                                                'completed': '✅ Завершена'
                                            }
                                            new_status = st.selectbox(
                                                "Статус",
                                                options=list(status_options.keys()),
                                                format_func=lambda x: status_options[x],
                                                index=list(status_options.keys()).index(booking['status']),
                                                key=f"status_{booking['id']}"
                                            )
                                            if st.button("🔄 Обновить статус", key=f"update_status_{booking['id']}", use_container_width=True):
                                                success, message = update_booking_status(booking['id'], new_status)
                                                if success:
                                                    st.success(message)
                                                    st.rerun()
                                    
                                    st.markdown("---")
                        else:
                            st.info("📭 История записей пуста")
            
            # Сводная статистика по всем клиентам
            st.markdown("---")
            st.markdown("### 📊 Сводная статистика по клиентам")
            
            col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
            with col_sum1:
                st.metric("Всего клиентов", len(clients_df))
            with col_sum2:
                active_clients = len(clients_df[clients_df['upcoming_bookings'] > 0])
                st.metric("Активных клиентов", active_clients)
            with col_sum3:
                avg_bookings = clients_df['total_bookings'].mean()
                st.metric("Среднее число записей", f"{avg_bookings:.1f}")
            with col_sum4:
                total_bookings = clients_df['total_bookings'].sum()
                st.metric("Всего записей", total_bookings)
                
        else:
            st.info("📭 В базе нет клиентов")
    
    # Вкладка Настройки
    with tabs[2]:
        st.markdown("### ⚙️ Настройки системы")
        
        settings_tabs = st.tabs(["📅 Расписание", "ℹ️ Информационная панель"])
        
        # Вкладка расписания
        with settings_tabs[0]:
            st.markdown("#### 📅 Настройки расписания")
            
            settings = get_settings()
            if settings:
                col1, col2, col3 = st.columns(3)
                with col1:
                    work_start = st.time_input("🕐 Начало рабочего дня", 
                                             value=datetime.strptime(settings['work_start'], '%H:%M').time())
                with col2:
                    work_end = st.time_input("🕐 Конец рабочего дня", 
                                           value=datetime.strptime(settings['work_end'], '%H:%M').time())
                with col3:
                    session_duration = st.number_input("⏱️ Длительность сессии (мин)", 
                                                      min_value=15, max_value=180, 
                                                      value=settings['session_duration'], step=15)
                
                if st.button("💾 Сохранить настройки расписания", use_container_width=True):
                    if update_settings(work_start.strftime('%H:%M'), work_end.strftime('%H:%M'), session_duration):
                        st.success("✅ Настройки расписания сохранены!")
                        st.rerun()
                    else:
                        st.error("❌ Ошибка сохранения настроек расписания")
        
        # Вкладка информационной панели
        with settings_tabs[1]:
            st.markdown("#### ℹ️ Настройки информационной панели")
            st.info("Здесь вы можете редактировать текст, который видят клиенты в правой панели")
            
            settings = get_settings()
            if settings:
                with st.form("info_panel_settings"):
                    st.markdown("**Основные настройки:**")
                    info_title = st.text_input("📝 Заголовок панели", 
                                             value=settings.get('info_title', 'ℹ️ Информация'))
                    
                    st.markdown("**📋 Содержимое панели:**")
                    info_work_hours = st.text_area("🕐 Рабочее время", 
                                                 value=settings.get('info_work_hours', '🕐 Рабочее время:\n09:00 - 18:00'),
                                                 height=80,
                                                 help="Используйте \\n для переноса строк")
                    
                    info_session_duration = st.text_area("⏱️ Длительность консультации", 
                                                       value=settings.get('info_session_duration', '⏱️ Длительность консультации:\n60 минут'),
                                                       height=80)
                    
                    info_format = st.text_area("💻 Формат консультации", 
                                             value=settings.get('info_format', '💻 Формат:\nОнлайн или в кабинете'),
                                             height=80)
                    
                    info_contacts = st.text_area("📞 Контактная информация", 
                                               value=settings.get('info_contacts', '📞 Контакты:\n📱 +7 (999) 123-45-67\n📧 hello@psychologist.ru\n🌿 psychologist.ru'),
                                               height=100,
                                               help="Укажите телефоны, email, сайт и другие контакты")
                    
                    info_additional = st.text_area("📝 Дополнительная информация", 
                                                 value=settings.get('info_additional', ''),
                                                 height=100,
                                                 placeholder="Любая дополнительная информация для клиентов...",
                                                 help="Необязательное поле")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        submit_info = st.form_submit_button("💾 Сохранить настройки", use_container_width=True)
                    with col2:
                        preview_info = st.form_submit_button("👁️ Предпросмотр", use_container_width=True)
                    
                    if submit_info:
                        info_data = {
                            'info_title': info_title,
                            'info_work_hours': info_work_hours,
                            'info_session_duration': info_session_duration,
                            'info_format': info_format,
                            'info_contacts': info_contacts,
                            'info_additional': info_additional
                        }
                        
                        if update_info_settings(info_data):
                            st.success("✅ Настройки информационной панели сохранены!")
                            st.rerun()
                        else:
                            st.error("❌ Ошибка сохранения настроек. Проверьте структуру базы данных.")
                    
                    if preview_info:
                        st.markdown("---")
                        st.markdown("#### 👁️ Предпросмотр информационной панели")
                        st.markdown(f"""
                        <div class="info-box">
                            <h4>{info_title}</h4>
                            <p><strong>{info_work_hours.replace(chr(10), '<br>')}</strong></p>
                            <p><strong>{info_session_duration.replace(chr(10), '<br>')}</strong></p>
                            <p><strong>{info_format.replace(chr(10), '<br>')}</strong></p>
                            <hr>
                            <h4>📞 Контакты</h4>
                            <p>{info_contacts.replace(chr(10), '<br>')}</p>
                            {f'<p>{info_additional.replace(chr(10), "<br>")}</p>' if info_additional and info_additional.strip() else ''}
                        </div>
                        """, unsafe_allow_html=True)
    
    # Вкладка Блокировки
    with tabs[3]:
        st.markdown("### 🚫 Управление блокировками")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📅 Блокировка дней")
            with st.form("block_day_form"):
                block_date_input = st.date_input("Дата", min_value=datetime.now().date())
                block_reason = st.text_input("Причина", value="Выходной")
                submit_block = st.form_submit_button("🚫 Заблокировать", use_container_width=True)
                
                if submit_block:
                    if block_date(str(block_date_input), block_reason):
                        st.success(f"✅ День заблокирован!")
                        st.rerun()
                    else:
                        st.error("❌ День уже заблокирован")
            
            st.markdown("#### 🕐 Блокировка времени")
            with st.form("block_time_form"):
                time_block_date = st.date_input("Дата", min_value=datetime.now().date(), key="time_date")
                time_block_time = st.time_input("Время", value=datetime.strptime("09:00", "%H:%M").time())
                time_block_reason = st.text_input("Причина", value="Технические работы", key="time_reason")
                submit_time_block = st.form_submit_button("🚫 Заблокировать", use_container_width=True)
                
                if submit_time_block:
                    if block_time_slot(str(time_block_date), time_block_time.strftime("%H:%M"), time_block_reason):
                        st.success(f"✅ Время заблокировано!")
                        st.rerun()
                    else:
                        st.error("❌ Слот уже заблокирован")
        
        with col2:
            st.markdown("#### 📋 Заблокированные дни")
            blocked_dates = get_blocked_dates()
            if blocked_dates:
                for block in blocked_dates:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.info(f"**{format_date(block['block_date'])}** - {block['reason']}")
                    with col_b:
                        if st.button("🗑️", key=f"unblock_{block['block_date']}", use_container_width=True):
                            unblock_date(block['block_date'])
                            st.success("✅ Разблокирован!")
                            st.rerun()
            else:
                st.info("📭 Нет блокировок")
            
            st.markdown("#### 🕐 Заблокированные слоты")
            blocked_slots_df = get_blocked_slots()
            if not blocked_slots_df.empty:
                for idx, row in blocked_slots_df.iterrows():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.warning(f"**{format_date(row['block_date'])} {row['block_time']}** - {row['reason']}")
                    with col_b:
                        if st.button("🗑️", key=f"unblock_slot_{row['id']}", use_container_width=True):
                            unblock_time_slot(row['id'])
                            st.success("✅ Разблокирован!")
                            st.rerun()
            else:
                st.info("📭 Нет заблокированных слотов")
    
    # Вкладка Аналитика
    with tabs[4]:
        st.markdown("### 📊 Аналитика")
        
        total, upcoming, this_month, this_week = get_stats()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Всего", total)
        col2.metric("⏰ Предстоящих", upcoming)
        col3.metric("📅 За месяц", this_month)
        col4.metric("📆 За неделю", this_week)
    
    # Вкладка Уведомления
    with tabs[5]:
        st.markdown("### 🔔 Система уведомлений")
        
        # Статус бота
        st.markdown("#### 🤖 Статус Telegram бота")
        
        if TELEGRAM_CONFIG['bot_token'] and TELEGRAM_CONFIG['admin_chat_id']:
            st.success("✅ Бот настроен и готов к работе")
            
            # Тестирование
            st.markdown("#### 🧪 Тестирование уведомлений")
            
            test_message = st.text_area("Тестовое сообщение", 
                                      "✅ Система уведомлений работает корректно!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Тест админу", use_container_width=True):
                    if telegram_bot.send_to_admin(test_message):
                        st.success("✅ Тест отправлен админу!")
                    else:
                        st.error("❌ Ошибка отправки")
            
            with col2:
                test_chat_id = st.text_input("Chat ID для теста", placeholder="123456789")
                if st.button("📤 Тест клиенту", use_container_width=True):
                    if test_chat_id:
                        if telegram_bot.send_to_client(test_chat_id, test_message):
                            st.success("✅ Тест отправлен клиенту!")
                        else:
                            st.error("❌ Ошибка отправки")
                    else:
                        st.error("❌ Введите Chat ID")
        
        else:
            st.error("❌ Бот не настроен")
            st.markdown("""
            ### ⚙️ Инструкция по настройке:
            
            1. **Создай бота** в Telegram через @BotFather
            2. **Получи токен** и укажи в переменных:
               ```env
               TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
               TELEGRAM_ADMIN_CHAT_ID=123456789
               ```
            3. **Узнай свой Chat ID** через @userinfobot
            4. **Перезапусти приложение**
            """)

# ============================================================================
# ГЛАВНАЯ СТРАНИЦА: КЛИЕНТСКАЯ ЧАСТЬ
# ============================================================================

elif not st.session_state.client_logged_in:
    st.title("🌿 Запись на консультацию")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Форма входа
        st.markdown("#### 🔐 Уже записывались?")
        with st.form("client_login_form"):
            login_phone = st.text_input("📱 Номер телефона", placeholder="+7 (999) 123-45-67")
            login_submit = st.form_submit_button("Войти", use_container_width=True)
            
            if login_submit and login_phone:
                if client_login(login_phone):
                    st.success("✅ Успешный вход!")
                    st.rerun()
                else:
                    st.error("❌ Записей не найдено")
        
        st.markdown("---")
        st.markdown("#### 📅 Новая запись")
        
        # Выбор даты
        min_date = datetime.now().date()
        max_date = min_date + timedelta(days=BOOKING_RULES["MAX_DAYS_AHEAD"])
        
        selected_date = st.date_input("Дата консультации", min_value=min_date, 
                                      max_value=max_date, value=min_date, format="DD.MM.YYYY")
        
        # Получаем слоты
        available_slots = get_available_slots(str(selected_date))
        selected_time = render_time_slots(available_slots, "guest_slot")
        
        if selected_time:
            st.success(f"✅ Выбрано: **{selected_date.strftime('%d.%m.%Y')}** в **{selected_time}**")
            
            st.markdown("#### 👤 Ваши данные")
            with st.form("booking_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    client_name = st.text_input("👤 Имя *", placeholder="Иван Иванов")
                    client_email = st.text_input("📧 Email", placeholder="example@mail.com")
                    # 🔥 НОВОЕ ПОЛЕ
                    client_chat_id = st.text_input("💬 ID Telegram для уведомлений", 
                                                 placeholder="123456789 (опционально)",
                                                 help="Чтобы получать уведомления о записи и напоминания")
                with col_b:
                    client_phone = st.text_input("📱 Телефон *", placeholder="+7 (999) 123-45-67")
                    client_telegram = st.text_input("💬 Telegram username", placeholder="@username")
                
                notes = st.text_area("💭 Комментарий (необязательно)", height=80)
                submit = st.form_submit_button("✅ Подтвердить запись", use_container_width=True)
                
                if submit:
                    if not client_name or not client_phone:
                        st.error("❌ Заполните имя и телефон")
                    elif has_active_booking(client_phone):
                        st.error("❌ У вас уже есть активная запись")
                    else:
                        success, message = create_booking(
                            client_name, client_phone, client_email, 
                            client_telegram, str(selected_date), selected_time, notes,
                            client_chat_id  # 🔥 ПЕРЕДАЕМ CHAT_ID
                        )
                        if success:
                            st.balloons()
                            # Автологин
                            st.session_state.client_logged_in = True
                            st.session_state.client_phone = client_phone
                            st.session_state.client_name = client_name
                            st.session_state.current_tab = "👁️ Текущая запись"
                            
                            st.markdown(f"""
                            <div class="success-message">
                                <h3>🌿 Запись подтверждена!</h3>
                                <p><strong>📅 Дата:</strong> {selected_date.strftime('%d.%m.%Y')}</p>
                                <p><strong>🕐 Время:</strong> {selected_time}</p>
                                <p><strong>🎉 Вы автоматически авторизованы!</strong></p>
                                <p><strong>🔔 Уведомления отправлены!</strong></p>
                            </div>
                            """, unsafe_allow_html=True)
                            st.rerun()
                        else:
                            st.error(message)
    
    with col2:
        render_info_panel()

# ============================================================================
# ГЛАВНАЯ СТРАНИЦА: ЛИЧНЫЙ КАБИНЕТ (ОБНОВЛЕННЫЙ)
# ============================================================================

else:
    st.title("👤 Личный кабинет")
    
    client_info = get_client_info(st.session_state.client_phone)
    st.markdown(f"""
    <div class="welcome-header">
        <h1>👋 Здравствуйте, {st.session_state.client_name}!</h1>
        <p>Рады видеть вас снова!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ОБНОВЛЕННЫЙ ПОРЯДОК ВКЛАДОК - ДОБАВЛЯЕМ TELEGRAM
    if st.session_state.current_tab == "👁️ Текущая запись":
        st.markdown("### 👁️ Текущая запись")
        
        upcoming = get_upcoming_client_booking(st.session_state.client_phone)
        
        if upcoming:
            time_until = calculate_time_until(upcoming['booking_date'], upcoming['booking_time'])
            
            st.markdown(f"""
            <div class="booking-card">
                <h3>🕐 Ближайшая консультация</h3>
                <p><strong>📅 Дата:</strong> {format_date(upcoming['booking_date'])}</p>
                <p><strong>🕐 Время:</strong> {upcoming['booking_time']}</p>
                <p><strong>⏱️ До начала:</strong> {format_timedelta(time_until)}</p>
                {f"<p><strong>💭 Комментарий:</strong> {upcoming['notes']}</p>" if upcoming['notes'] else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # Проверяем подключен ли Telegram
            telegram_connected = get_client_telegram_chat_id(st.session_state.client_phone)
            if not telegram_connected:
                st.warning("""
                ⚠️ **Вы не получаете напоминания!**
                
                Подключите Telegram в разделе "💬 Уведомления" чтобы получать:
                • ⏰ Напоминание за 1 час до консультации
                • ✅ Подтверждения новых записей
                • ❌ Уведомления об отменах
                """)
            
            if time_until.total_seconds() > BOOKING_RULES["MIN_CANCEL_MINUTES"] * 60:
                if st.button("❌ Отменить запись", type="secondary", use_container_width=True):
                    # Получаем chat_id для уведомления
                    chat_id = get_client_telegram_chat_id(st.session_state.client_phone)
                    success, message = cancel_booking(upcoming['id'], st.session_state.client_phone, chat_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning(f"⚠️ Отмена возможна за {BOOKING_RULES['MIN_CANCEL_MINUTES']}+ минут")
        else:
            st.info("📭 Нет предстоящих консультаций")
    
    elif st.session_state.current_tab == "👤 Профиль":
        st.markdown("### 👤 Профиль")
        
        if client_info:
            with st.form("profile_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("👤 Имя *", value=client_info['name'])
                    new_email = st.text_input("📧 Email", value=client_info['email'] or "")
                with col2:
                    st.text_input("📱 Телефон", value=st.session_state.client_phone, disabled=True)
                    new_telegram = st.text_input("💬 Telegram", value=client_info['telegram'] or "")
                
                submit = st.form_submit_button("💾 Сохранить", use_container_width=True)
                
                if submit and new_name.strip():
                    # В Supabase профиль обновляется через создание новой записи с обновленными данными
                    st.info("ℹ️ Данные профиля обновятся при следующей записи")
    
    elif st.session_state.current_tab == "💬 Уведомления":  # 🔥 НОВАЯ ВКЛАДКА
        render_telegram_section()
    
    elif st.session_state.current_tab == "📅 Запись":
        st.markdown("### 📅 Новая запись")
        
        if has_active_booking(st.session_state.client_phone):
            st.warning("⚠️ У вас уже есть активная запись. Перейдите в 'Текущая запись'.")
        else:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                selected_date = st.date_input("Дата", min_value=datetime.now().date(),
                                            max_value=datetime.now().date() + timedelta(days=30),
                                            format="DD.MM.YYYY")
                
                available_slots = get_available_slots(str(selected_date))
                selected_time = render_time_slots(available_slots, "client_slot")
                
                if selected_time:
                    st.success(f"✅ {selected_date.strftime('%d.%m.%Y')} в {selected_time}")
                    
                    with st.form("quick_booking"):
                        notes = st.text_area("💭 Тема консультации", height=80)
                        submit = st.form_submit_button("✅ Записаться", use_container_width=True)
                        
                        if submit:
                            # Получаем chat_id для уведомления
                            chat_id = get_client_telegram_chat_id(st.session_state.client_phone)
                            
                            success, message = create_booking(
                                client_info['name'] if client_info else st.session_state.client_name,
                                st.session_state.client_phone,
                                client_info.get('email', '') if client_info else '',
                                client_info.get('telegram', '') if client_info else '',
                                str(selected_date), selected_time, notes,
                                chat_id  # 🔥 ПЕРЕДАЕМ CHAT_ID
                            )
                            if success:
                                st.balloons()
                                st.success("🎉 Запись создана!")
                                st.rerun()
                            else:
                                st.error(message)
            
            with col2:
                render_info_panel()
    
    elif st.session_state.current_tab == "📊 История":
        st.markdown("### 📊 История записей")
        
        bookings = get_client_bookings(st.session_state.client_phone)
        
        if not bookings.empty:
            for idx, row in bookings.iterrows():
                status_info = STATUS_DISPLAY.get(row['status'], STATUS_DISPLAY['confirmed'])
                date_formatted = format_date(row['booking_date'])
                
                st.markdown(f"""
                <div class="booking-card">
                    <h4>{status_info['emoji']} {date_formatted} в {row['booking_time']}</h4>
                    <p><strong>Статус:</strong> <span style="color: {status_info['color']}">{status_info['text']}</span></p>
                    {f"<p><strong>💭</strong> {row['notes']}</p>" if row['notes'] else ""}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 История пуста")