import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import hashlib
import re
from contextlib import contextmanager

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
    "MIN_ADVANCE_HOURS": 1,  # Минимум за 1 час до начала
    "MIN_CANCEL_MINUTES": 30,  # Отмена минимум за 30 минут
    "MAX_DAYS_AHEAD": 30,  # Максимум на 30 дней вперёд
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

# ============================================================================
# СТИЛИЗАЦИЯ
# ============================================================================

def load_custom_css():
    """Загрузка кастомных CSS стилей"""
    st.markdown("""
        <style>
        .main {
            padding: 0rem 1rem;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }
        
        .stButton>button {
            width: 100%;
            border-radius: 12px;
            height: 3.2em;
            background: linear-gradient(135deg, #88c8bc 0%, #6ba292 100%);
            color: white;
            font-weight: 500;
            border: none;
            box-shadow: 0 4px 15px rgba(136, 200, 188, 0.3);
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(136, 200, 188, 0.4);
        }
        
        .stButton>button:disabled {
            background: #cccccc !important;
            color: #666666 !important;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;
        }
        
        .booking-card {
            padding: 1.8rem;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.95);
            margin-bottom: 1.2rem;
            border-left: 4px solid #88c8bc;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            transition: transform 0.2s ease;
        }
        
        .booking-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 25px rgba(0, 0, 0, 0.12);
        }
        
        .stat-card {
            padding: 1.8rem;
            border-radius: 16px;
            background: linear-gradient(135deg, #88c8bc 0%, #a8d5ba 100%);
            color: white;
            text-align: center;
            box-shadow: 0 6px 20px rgba(136, 200, 188, 0.3);
        }
        
        .success-message {
            padding: 2rem;
            border-radius: 16px;
            background: linear-gradient(135deg, #a8d5ba 0%, #88c8bc 100%);
            color: white;
            box-shadow: 0 6px 20px rgba(136, 200, 188, 0.3);
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .info-box {
            background: white;
            border-radius: 16px;
            padding: 1.8rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
            border-left: 4px solid #88c8bc;
        }
        
        .warning-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            color: #856404;
        }
        
        .welcome-header {
            background: linear-gradient(135deg, #88c8bc 0%, #a8d5ba 100%);
            color: white;
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            text-align: center;
            animation: slideDown 0.5s ease-out;
        }
        
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .quick-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }
        
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .time-slot-btn {
            transition: all 0.2s ease;
        }
        
        .time-slot-btn:hover {
            transform: scale(1.05);
        }
        </style>
    """, unsafe_allow_html=True)

# ============================================================================
# УТИЛИТЫ И ХЕЛПЕРЫ
# ============================================================================

@contextmanager
def get_db_connection():
    """Context manager для безопасной работы с БД"""
    conn = sqlite3.connect('bookings.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def normalize_phone(phone: str) -> str:
    """Нормализация номера телефона"""
    return re.sub(r'\D', '', phone)

def format_date(date_str: str, format_str: str = '%d.%m.%Y') -> str:
    """Форматирование даты"""
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
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}м")
    
    return " ".join(parts)

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
# ============================================================================

st.set_page_config(**PAGE_CONFIG)
load_custom_css()

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
        'show_new_booking_form': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ============================================================================

def init_database():
    """Создание и настройка базы данных"""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Таблица настроек
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (id INTEGER PRIMARY KEY CHECK (id = 1),
                      work_start TEXT DEFAULT '09:00',
                      work_end TEXT DEFAULT '18:00',
                      session_duration INTEGER DEFAULT 60,
                      break_duration INTEGER DEFAULT 15)''')
        c.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")
        
        # Таблица блокировок
        c.execute('''CREATE TABLE IF NOT EXISTS blocked_slots
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      block_date DATE NOT NULL,
                      block_time TEXT,
                      reason TEXT,
                      UNIQUE(block_date, block_time))''')
        
        # Таблица записей
        c.execute('''CREATE TABLE IF NOT EXISTS bookings
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      client_name TEXT NOT NULL,
                      client_phone TEXT NOT NULL,
                      client_email TEXT,
                      client_telegram TEXT,
                      booking_date DATE NOT NULL,
                      booking_time TEXT NOT NULL,
                      notes TEXT,
                      status TEXT DEFAULT 'confirmed',
                      phone_hash TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      UNIQUE(booking_date, booking_time))''')
        
        # Добавляем колонку phone_hash если её нет
        try:
            c.execute("ALTER TABLE bookings ADD COLUMN phone_hash TEXT")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()

init_database()

# ============================================================================
# БИЗНЕС-ЛОГИКА: НАСТРОЙКИ
# ============================================================================

def get_settings():
    """Получение настроек системы"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT work_start, work_end, session_duration, break_duration FROM settings WHERE id = 1")
        return c.fetchone()

def update_settings(work_start: str, work_end: str, session_duration: int):
    """Обновление настроек системы"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE settings SET work_start = ?, work_end = ?, session_duration = ? WHERE id = 1", 
                  (work_start, work_end, session_duration))
        conn.commit()

# ============================================================================
# БИЗНЕС-ЛОГИКА: КЛИЕНТЫ
# ============================================================================

def get_client_info(phone: str):
    """Получение информации о клиенте"""
    with get_db_connection() as conn:
        phone_hash = hash_password(normalize_phone(phone))
        query = """SELECT client_name, client_email, client_telegram 
                   FROM bookings 
                   WHERE phone_hash = ? 
                   ORDER BY created_at DESC 
                   LIMIT 1"""
        c = conn.cursor()
        c.execute(query, (phone_hash,))
        result = c.fetchone()
        
        if result:
            return {
                'name': result[0],
                'email': result[1],
                'telegram': result[2]
            }
        return None

def update_client_profile(phone: str, name: str = None, email: str = None, telegram: str = None):
    """Обновление профиля клиента"""
    with get_db_connection() as conn:
        phone_hash = hash_password(normalize_phone(phone))
        c = conn.cursor()
        
        updates = []
        params = []
        
        if name:
            updates.append("client_name = ?")
            params.append(name)
        if email is not None:
            updates.append("client_email = ?")
            params.append(email)
        if telegram is not None:
            updates.append("client_telegram = ?")
            params.append(telegram)
        
        if updates:
            params.append(phone_hash)
            query = f"UPDATE bookings SET {', '.join(updates)} WHERE phone_hash = ?"
            c.execute(query, params)
            conn.commit()
            return True
        return False

def has_active_booking(phone: str) -> bool:
    """Проверка наличия активной записи"""
    with get_db_connection() as conn:
        phone_hash = hash_password(normalize_phone(phone))
        query = """SELECT COUNT(*) FROM bookings 
                   WHERE phone_hash = ? 
                   AND status = 'confirmed' 
                   AND booking_date >= date('now')"""
        c = conn.cursor()
        c.execute(query, (phone_hash,))
        return c.fetchone()[0] > 0

def get_client_bookings(phone: str):
    """Получение всех записей клиента"""
    with get_db_connection() as conn:
        phone_hash = hash_password(normalize_phone(phone))
        query = """SELECT id, client_name, booking_date, booking_time, notes, status, created_at 
                   FROM bookings 
                   WHERE phone_hash = ? 
                   ORDER BY booking_date DESC, booking_time DESC"""
        return pd.read_sql_query(query, conn, params=(phone_hash,))

def get_upcoming_client_booking(phone: str):
    """Получение ближайшей записи клиента"""
    with get_db_connection() as conn:
        phone_hash = hash_password(normalize_phone(phone))
        query = """SELECT id, client_name, booking_date, booking_time, notes, status 
                   FROM bookings 
                   WHERE phone_hash = ? AND booking_date >= date('now') AND status = 'confirmed'
                   ORDER BY booking_date, booking_time 
                   LIMIT 1"""
        c = conn.cursor()
        c.execute(query, (phone_hash,))
        return c.fetchone()

def get_all_clients():
    """Получение списка всех уникальных клиентов"""
    with get_db_connection() as conn:
        query = """
        SELECT 
            phone_hash,
            client_name,
            client_phone,
            client_email,
            client_telegram,
            COUNT(*) as total_bookings,
            SUM(CASE WHEN status = 'confirmed' AND booking_date >= date('now') THEN 1 ELSE 0 END) as upcoming_bookings,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_bookings,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_bookings,
            MIN(created_at) as first_booking,
            MAX(created_at) as last_booking
        FROM bookings 
        GROUP BY phone_hash, client_name, client_phone, client_email, client_telegram
        ORDER BY last_booking DESC
        """
        return pd.read_sql_query(query, conn)

def get_client_booking_history(phone_hash):
    """Получение истории записей конкретного клиента"""
    with get_db_connection() as conn:
        query = """
        SELECT 
            id,
            booking_date,
            booking_time,
            status,
            notes,
            created_at
        FROM bookings 
        WHERE phone_hash = ?
        ORDER BY booking_date DESC, booking_time DESC
        """
        return pd.read_sql_query(query, conn, params=(phone_hash,))

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
    settings = get_settings()
    work_start = datetime.strptime(settings[0], '%H:%M').time()
    work_end = datetime.strptime(settings[1], '%H:%M').time()
    session_duration = settings[2]
    
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Проверка блокировки дня
        c.execute("SELECT id FROM blocked_slots WHERE block_date = ? AND block_time IS NULL", (date,))
        if c.fetchone():
            return []
        
        slots = []
        current_time = datetime.combine(datetime.today(), work_start)
        end_time = datetime.combine(datetime.today(), work_end)
        
        while current_time < end_time:
            time_slot = current_time.strftime('%H:%M')
            
            # Проверки
            c.execute("SELECT id FROM bookings WHERE booking_date = ? AND booking_time = ? AND status != 'cancelled'", 
                     (date, time_slot))
            is_booked = c.fetchone() is not None
            
            c.execute("SELECT id FROM blocked_slots WHERE block_date = ? AND block_time = ?", 
                     (date, time_slot))
            is_blocked = c.fetchone() is not None
            
            time_available, _ = is_time_available(date, time_slot)
            
            if not is_booked and not is_blocked and time_available:
                slots.append(time_slot)
            
            current_time += timedelta(minutes=session_duration)
        
        return slots

def create_booking(client_name: str, client_phone: str, client_email: str, 
                  client_telegram: str, date: str, time_slot: str, notes: str = "") -> tuple:
    """Создание записи"""
    # Проверка активной записи
    if has_active_booking(client_phone):
        return False, "❌ У вас уже есть активная запись"
    
    # Проверка доступности времени
    time_available, reason = is_time_available(date, time_slot)
    if not time_available:
        return False, reason
    
    with get_db_connection() as conn:
        try:
            c = conn.cursor()
            phone_hash = hash_password(normalize_phone(client_phone))
            c.execute("""INSERT INTO bookings 
                        (client_name, client_phone, client_email, client_telegram, 
                         booking_date, booking_time, notes, phone_hash) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (client_name, client_phone, client_email, client_telegram, 
                       date, time_slot, notes, phone_hash))
            conn.commit()
            return True, "✅ Запись успешно создана"
        except sqlite3.IntegrityError:
            return False, "❌ Это время уже занято"

def create_booking_by_admin(client_name: str, client_phone: str, client_email: str, 
                           client_telegram: str, date: str, time_slot: str, notes: str = ""):
    """Создание записи администратором (без ограничений)"""
    with get_db_connection() as conn:
        try:
            c = conn.cursor()
            phone_hash = hash_password(normalize_phone(client_phone))
            c.execute("""INSERT INTO bookings 
                        (client_name, client_phone, client_email, client_telegram, 
                         booking_date, booking_time, notes, phone_hash) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (client_name, client_phone, client_email, client_telegram, 
                       date, time_slot, notes, phone_hash))
            conn.commit()
            return True, "✅ Запись успешно создана"
        except sqlite3.IntegrityError:
            return False, "❌ Это время уже занято"

def cancel_booking(booking_id: int, phone: str) -> tuple:
    """Отмена записи"""
    with get_db_connection() as conn:
        phone_hash = hash_password(normalize_phone(phone))
        c = conn.cursor()
        
        # Получаем информацию о записи
        c.execute("SELECT booking_date, booking_time FROM bookings WHERE id = ? AND phone_hash = ?", 
                  (booking_id, phone_hash))
        booking = c.fetchone()
        
        if not booking:
            return False, "Запись не найдена"
        
        # Проверяем время до начала
        time_until = calculate_time_until(booking[0], booking[1])
        min_cancel = BOOKING_RULES["MIN_CANCEL_MINUTES"] * 60
        
        if time_until.total_seconds() < min_cancel:
            return False, f"Отмена возможна не позднее чем за {BOOKING_RULES['MIN_CANCEL_MINUTES']} минут"
        
        # Отменяем
        c.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
        conn.commit()
        return True, "Запись успешно отменена"

def delete_booking(booking_id: int):
    """Удаление записи (для админа)"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()

def get_all_bookings(date_from: str = None, date_to: str = None):
    """Получение всех записей с поддержкой фильтрации по дате"""
    with get_db_connection() as conn:
        if date_from and date_to:
            query = """SELECT id, client_name, client_phone, client_email, client_telegram, 
                             booking_date, booking_time, notes, status 
                       FROM bookings 
                       WHERE booking_date BETWEEN ? AND ?
                       ORDER BY booking_date, booking_time"""
            return pd.read_sql_query(query, conn, params=(date_from, date_to))
        elif date_from:
            query = """SELECT id, client_name, client_phone, client_email, client_telegram, 
                             booking_date, booking_time, notes, status 
                       FROM bookings 
                       WHERE booking_date >= ?
                       ORDER BY booking_date, booking_time"""
            return pd.read_sql_query(query, conn, params=(date_from,))
        else:
            query = """SELECT id, client_name, client_phone, client_email, client_telegram, 
                             booking_date, booking_time, notes, status 
                       FROM bookings 
                       ORDER BY booking_date DESC, booking_time DESC"""
            return pd.read_sql_query(query, conn)

# ============================================================================
# БИЗНЕС-ЛОГИКА: УПРАВЛЕНИЕ ЗАПИСЯМИ (админ)
# ============================================================================

def update_booking_datetime(booking_id: int, new_date: str, new_time: str):
    """Обновление даты и времени записи"""
    with get_db_connection() as conn:
        try:
            c = conn.cursor()
            c.execute("UPDATE bookings SET booking_date = ?, booking_time = ? WHERE id = ?", 
                     (new_date, new_time, booking_id))
            conn.commit()
            return True, "✅ Время записи обновлено"
        except sqlite3.IntegrityError:
            return False, "❌ Это время уже занято"

def update_booking_notes(booking_id: int, new_notes: str):
    """Обновление комментария к записи"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE bookings SET notes = ? WHERE id = ?", (new_notes, booking_id))
        conn.commit()
        return True, "✅ Комментарий обновлен"

def update_booking_status(booking_id: int, new_status: str):
    """Обновление статуса записи"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
        conn.commit()
        return True, f"✅ Статус изменен на {STATUS_DISPLAY[new_status]['text']}"

# ============================================================================
# БИЗНЕС-ЛОГИКА: БЛОКИРОВКИ
# ============================================================================

def block_date(date: str, reason: str = "Выходной") -> bool:
    """Блокировка дня"""
    with get_db_connection() as conn:
        try:
            c = conn.cursor()
            c.execute("INSERT INTO blocked_slots (block_date, reason) VALUES (?, ?)", (date, reason))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def unblock_date(date: str):
    """Разблокировка дня"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM blocked_slots WHERE block_date = ? AND block_time IS NULL", (date,))
        conn.commit()

def get_blocked_dates():
    """Получение заблокированных дат"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT block_date, reason FROM blocked_slots WHERE block_time IS NULL ORDER BY block_date")
        return c.fetchall()

def block_time_slot(date: str, time_slot: str, reason: str = "Технические работы") -> bool:
    """Блокировка временного слота"""
    with get_db_connection() as conn:
        try:
            c = conn.cursor()
            c.execute("INSERT INTO blocked_slots (block_date, block_time, reason) VALUES (?, ?, ?)", 
                      (date, time_slot, reason))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def unblock_time_slot(block_id: int):
    """Разблокировка временного слота"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM blocked_slots WHERE id = ?", (block_id,))
        conn.commit()

def get_blocked_slots():
    """Получение заблокированных слотов"""
    with get_db_connection() as conn:
        query = """SELECT id, block_date, block_time, reason FROM blocked_slots 
                   WHERE block_time IS NOT NULL ORDER BY block_date, block_time"""
        return pd.read_sql_query(query, conn)

# ============================================================================
# СТАТИСТИКА И АНАЛИТИКА
# ============================================================================

@st.cache_data(ttl=60)
def get_stats():
    """Получение основной статистики"""
    with get_db_connection() as conn:
        total = pd.read_sql_query("SELECT COUNT(*) as count FROM bookings", conn).iloc[0]['count']
        
        upcoming = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM bookings WHERE booking_date >= date('now') AND status = 'confirmed'", 
            conn
        ).iloc[0]['count']
        
        this_month = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM bookings WHERE strftime('%Y-%m', booking_date) = strftime('%Y-%m', 'now')", 
            conn
        ).iloc[0]['count']
        
        this_week = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM bookings WHERE booking_date >= date('now', '-7 days')",
            conn
        ).iloc[0]['count']
        
        return total, upcoming, this_month, this_week

@st.cache_data(ttl=300)
def get_analytics_data():
    """Получение данных для аналитики"""
    with get_db_connection() as conn:
        monthly_stats = pd.read_sql_query("""
            SELECT 
                strftime('%Y-%m', booking_date) as month,
                COUNT(*) as bookings_count,
                COUNT(DISTINCT client_phone) as unique_clients
            FROM bookings 
            WHERE status != 'cancelled'
            GROUP BY strftime('%Y-%m', booking_date)
            ORDER BY month
        """, conn)
        
        weekday_stats = pd.read_sql_query("""
            SELECT 
                strftime('%w', booking_date) as weekday,
                COUNT(*) as bookings_count
            FROM bookings 
            WHERE status != 'cancelled'
            GROUP BY strftime('%w', booking_date)
            ORDER BY weekday
        """, conn)
        
        time_stats = pd.read_sql_query("""
            SELECT 
                substr(booking_time, 1, 2) as hour,
                COUNT(*) as bookings_count
            FROM bookings 
            WHERE status != 'cancelled'
            GROUP BY substr(booking_time, 1, 2)
            ORDER BY hour
        """, conn)
        
        return monthly_stats, weekday_stats, time_stats

# ============================================================================
# АВТОРИЗАЦИЯ
# ============================================================================

def check_admin_password(password: str) -> bool:
    """Проверка пароля администратора"""
    return hash_password(password) == ADMIN_PASSWORD_HASH

def client_login(phone: str) -> bool:
    """Авторизация клиента"""
    phone_hash = hash_password(normalize_phone(phone))
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT client_name FROM bookings WHERE phone_hash = ? ORDER BY created_at DESC LIMIT 1", 
                  (phone_hash,))
        result = c.fetchone()
        
        if result:
            st.session_state.client_logged_in = True
            st.session_state.client_phone = phone
            st.session_state.client_name = result[0]
            return True
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
    """Отрисовка карточки записи с использованием чистого Streamlit"""
    status_info = STATUS_DISPLAY.get(row['status'], STATUS_DISPLAY['confirmed'])
    
    # Создаем уникальный ключ с датой и временем
    unique_key = f"delete_{date}_{row['booking_time']}_{row['id']}"
    
    # Создаем контейнер с кастомным стилем
    with st.container():
        col1, col2 = st.columns([4, 1]) if show_actions else st.columns([1])
        
        with col1:
            # Заголовок с временем и именем
            st.markdown(f"**{status_info['emoji']} {row['booking_time']} - {row['client_name']}**")
            
            # Основная информация
            st.text(f"📱 {row['client_phone']}")
            
            if row.get('client_email'):
                st.text(f"📧 {row['client_email']}")
                
            if row.get('client_telegram'):
                st.text(f"💬 {row['client_telegram']}")
                
            if row.get('notes'):
                st.text(f"💭 {row['notes']}")
            
            # Статус с цветом
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
    st.info("💡 Доступные для записи временные слоты")
    
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
        # Клиентское меню
        if st.session_state.client_name:
            st.markdown(f"### 👋 {st.session_state.client_name}!")
        
        tabs = st.radio(
            "Меню:",
            ["📅 Запись", "👁️ Текущая запись", "📊 История", "👤 Профиль"],
            key="client_tabs"
        )
        st.session_state.current_tab = tabs
        
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            client_logout()
            st.rerun()
    
    elif st.session_state.admin_logged_in:
        # Админское меню
        st.markdown("### 📊 Статистика")
        total, upcoming, this_month, this_week = get_stats()
        st.metric("📋 Всего", total)
        st.metric("⏰ Предстоящих", upcoming)
        st.metric("📅 За месяц", this_month)
        
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            admin_logout()
            st.rerun()
    
    else:
        # Гостевое меню
        st.markdown("### 👤 Клиентская зона")
        st.info("Для записи используйте основную страницу")
    
    # Кнопка входа администратора всегда внизу
    st.markdown("---")
    st.markdown("### 👩‍💼 Администратор")
    
    if st.session_state.admin_logged_in:
        st.success("✅ Вы вошли как администратор")
    else:
        if st.button("🔐 Вход для администратора", use_container_width=True, type="secondary"):
            st.session_state.show_admin_login = True
            st.rerun()
    
    if st.session_state.show_admin_login:
        st.markdown("---")
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
# ГЛАВНАЯ СТРАНИЦА: АДМИН-ПАНЕЛЬ
# ============================================================================

if st.session_state.admin_logged_in:
    st.title("👩‍💼 Панель управления")
    
    tabs = st.tabs(["📋 Записи", "👥 Клиенты", "⚙️ Настройки", "🚫 Блокировки", "📊 Аналитика"])
    
    # ========== ВКЛАДКА: ЗАПИСИ ==========
    with tabs[0]:
        st.markdown("### 📋 Управление записями")
        
        # Фильтры для записей
        col1, col2 = st.columns([2, 1])
        with col1:
            date_filter = st.selectbox(
                "📅 Период отображения",
                ["Все даты", "Сегодня", "На неделю", "На месяц"]
            )
        with col2:
            if st.button("🔄 Обновить данные", use_container_width=True):
                get_stats.clear()
                st.rerun()
        
        # Применяем фильтры
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
        
        # Получаем данные с учетом фильтров
        df = get_all_bookings()
        
        if not df.empty:
            # Фильтрация по дате
            if date_from and date_to:
                df = df[(df['booking_date'] >= date_from) & (df['booking_date'] <= date_to)]
            elif date_from:
                df = df[df['booking_date'] >= date_from]
            
            # Сортировка
            df = df.sort_values(['booking_date', 'booking_time'], ascending=[True, True])
            
            # Статистика по фильтру
            st.info(f"📊 Найдено записей: {len(df)}")
            
            if not df.empty:
                df['booking_date'] = pd.to_datetime(df['booking_date']).dt.strftime('%d.%m.%Y')
                
                for date in sorted(df['booking_date'].unique()):
                    st.markdown(f"#### 📅 {date}")
                    date_bookings = df[df['booking_date'] == date]
                    
                    for idx, row in date_bookings.iterrows():
                        # Передаем дату для создания уникального ключа
                        render_booking_card(row, date)
                    
                    st.markdown("---")
            else:
                st.info("📭 Нет записей для отображения по выбранным фильтрам")
        else:
            st.info("📭 Нет записей для отображения")
    
    # ========== ВКЛАДКА: КЛИЕНТЫ ==========
    with tabs[1]:
        st.markdown("### 👥 База клиентов")
        
        # Поиск и фильтры
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            search_query = st.text_input("🔍 Поиск по имени или телефону", placeholder="Введите имя или телефон...")
        with col2:
            show_only_active = st.checkbox("Только с предстоящими", value=False)
        with col3:
            if st.button("🔄 Обновить", use_container_width=True):
                st.rerun()
        with col4:
            if st.button("➕ Новая запись", use_container_width=True, type="primary"):
                st.session_state.show_new_booking_form = True
        
        # Форма создания новой записи
        if st.session_state.get('show_new_booking_form'):
            st.markdown("---")
            st.markdown("#### 📝 Создание новой записи")
            
            with st.form("new_booking_admin_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    new_client_name = st.text_input("👤 Имя клиента *", placeholder="Иван Иванов")
                    new_client_email = st.text_input("📧 Email", placeholder="example@mail.com")
                    booking_date = st.date_input("📅 Дата", min_value=datetime.now().date(), 
                                               max_value=datetime.now().date() + timedelta(days=30))
                with col_b:
                    new_client_phone = st.text_input("📱 Телефон *", placeholder="+7 (999) 123-45-67")
                    new_client_telegram = st.text_input("💬 Telegram", placeholder="@username")
                    booking_time = st.time_input("🕐 Время", value=datetime.strptime("09:00", "%H:%M").time())
                
                booking_notes = st.text_area("💭 Причина встречи / комментарий", height=100)
                
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
            
            # Отображаем клиентов
            for idx, client in clients_df.iterrows():
                with st.expander(f"👤 {client['client_name']} - 📱 {client['client_phone']}", expanded=False):
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
    
    # ========== ВКЛАДКА: НАСТРОЙКИ ==========
    with tabs[2]:
        st.markdown("### ⚙️ Настройки расписания")
        
        settings = get_settings()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            work_start = st.time_input("🕐 Начало", value=datetime.strptime(settings[0], '%H:%M').time())
        with col2:
            work_end = st.time_input("🕐 Конец", value=datetime.strptime(settings[1], '%H:%M').time())
        with col3:
            session_duration = st.number_input("⏱️ Длительность (мин)", 
                                              min_value=15, max_value=180, value=settings[2], step=15)
        
        if st.button("💾 Сохранить настройки", use_container_width=True):
            update_settings(work_start.strftime('%H:%M'), work_end.strftime('%H:%M'), session_duration)
            st.success("✅ Настройки сохранены!")
            st.rerun()
    
    # ========== ВКЛАДКА: БЛОКИРОВКИ ==========
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
                for block_date, reason in blocked_dates:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.info(f"**{format_date(block_date)}** - {reason}")
                    with col_b:
                        if st.button("🗑️", key=f"unblock_{block_date}", use_container_width=True):
                            unblock_date(block_date)
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
    
    # ========== ВКЛАДКА: АНАЛИТИКА ==========
    with tabs[4]:
        st.markdown("### 📊 Аналитика")
        
        # Основные метрики
        total, upcoming, this_month, this_week = get_stats()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Всего", total)
        col2.metric("⏰ Предстоящих", upcoming)
        col3.metric("📅 За месяц", this_month)
        col4.metric("📆 За неделю", this_week)
        
        st.markdown("---")
        
        # Графики
        monthly_stats, weekday_stats, time_stats = get_analytics_data()
        
        if not monthly_stats.empty:
            fig_monthly = px.bar(monthly_stats, x='month', y='bookings_count',
                               title='📈 Записи по месяцам',
                               labels={'month': 'Месяц', 'bookings_count': 'Записи'})
            fig_monthly.update_traces(marker_color='#88c8bc')
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        if not weekday_stats.empty:
            weekday_stats['weekday_name'] = weekday_stats['weekday'].map(WEEKDAY_MAP)
            fig_weekday = px.pie(weekday_stats, values='bookings_count', names='weekday_name',
                                title='📅 По дням недели')
            st.plotly_chart(fig_weekday, use_container_width=True)

# ============================================================================
# ГЛАВНАЯ СТРАНИЦА: КЛИЕНТСКАЯ ЧАСТЬ
# ============================================================================

elif not st.session_state.client_logged_in:
    # ========== ФОРМА ЗАПИСИ ДЛЯ ГОСТЕЙ ==========
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
                with col_b:
                    client_phone = st.text_input("📱 Телефон *", placeholder="+7 (999) 123-45-67")
                    client_telegram = st.text_input("💬 Telegram", placeholder="@username")
                
                notes = st.text_area("💭 Комментарий (необязательно)", height=80)
                submit = st.form_submit_button("✅ Подтвердить запись", use_container_width=True)
                
                if submit:
                    if not client_name or not client_phone:
                        st.error("❌ Заполните имя и телефон")
                    elif has_active_booking(client_phone):
                        st.error("❌ У вас уже есть активная запись")
                    else:
                        success, message = create_booking(client_name, client_phone, client_email, 
                                                         client_telegram, str(selected_date), selected_time, notes)
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
                            </div>
                            """, unsafe_allow_html=True)
                            st.rerun()
                        else:
                            st.error(message)
    
    with col2:
        settings = get_settings()
        st.markdown(f"""
        <div class="info-box">
            <h4>ℹ️ Информация</h4>
            <p><strong>⏰ Рабочее время:</strong><br>{settings[0]} - {settings[1]}</p>
            <p><strong>⏱️ Длительность:</strong><br>{settings[2]} минут</p>
            <p><strong>💻 Формат:</strong><br>Онлайн или в кабинете</p>
            <hr>
            <h4>📞 Контакты</h4>
            <p>📱 +7 (999) 123-45-67<br>
            📧 hello@psychologist.ru<br>
            🌿 psychologist.ru</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# ГЛАВНАЯ СТРАНИЦА: ЛИЧНЫЙ КАБИНЕТ
# ============================================================================

else:
    st.title("👤 Личный кабинет")
    
    # Приветствие
    client_info = get_client_info(st.session_state.client_phone)
    st.markdown(f"""
    <div class="welcome-header">
        <h1>👋 Здравствуйте, {st.session_state.client_name}!</h1>
        <p>Рады видеть вас снова!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== ТЕКУЩАЯ ЗАПИСЬ ==========
    if st.session_state.current_tab == "👁️ Текущая запись":
        st.markdown("### 👁️ Текущая запись")
        
        upcoming = get_upcoming_client_booking(st.session_state.client_phone)
        
        if upcoming:
            booking_id, name, date, time, notes, status = upcoming
            time_until = calculate_time_until(date, time)
            
            st.markdown(f"""
            <div class="booking-card">
                <h3>🕐 Ближайшая консультация</h3>
                <p><strong>📅 Дата:</strong> {format_date(date)}</p>
                <p><strong>🕐 Время:</strong> {time}</p>
                <p><strong>⏱️ До начала:</strong> {format_timedelta(time_until)}</p>
                {f"<p><strong>💭 Комментарий:</strong> {notes}</p>" if notes else ""}
            </div>
            """, unsafe_allow_html=True)
            
            if time_until.total_seconds() > BOOKING_RULES["MIN_CANCEL_MINUTES"] * 60:
                if st.button("❌ Отменить запись", type="secondary", use_container_width=True):
                    success, message = cancel_booking(booking_id, st.session_state.client_phone)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning(f"⚠️ Отмена возможна за {BOOKING_RULES['MIN_CANCEL_MINUTES']}+ минут")
        else:
            st.info("📭 Нет предстоящих консультаций")
    
    # ========== ИСТОРИЯ ==========
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
    
    # ========== ПРОФИЛЬ ==========
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
                    if update_client_profile(st.session_state.client_phone, name=new_name.strip(),
                                           email=new_email.strip() or None, 
                                           telegram=new_telegram.strip() or None):
                        st.success("✅ Профиль обновлен!")
                        st.session_state.client_name = new_name.strip()
                        st.rerun()
    
    # ========== НОВАЯ ЗАПИСЬ ==========
    else:
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
                            success, message = create_booking(client_info['name'], 
                                                            st.session_state.client_phone,
                                                            client_info.get('email', ''),
                                                            client_info.get('telegram', ''),
                                                            str(selected_date), selected_time, notes)
                            if success:
                                st.balloons()
                                st.success("🎉 Запись создана!")
                                st.rerun()
                            else:
                                st.error(message)
            
            with col2:
                settings = get_settings()
                st.markdown(f"""
                <div class="info-box">
                    <h4>ℹ️ Информация</h4>
                    <p><strong>⏰ Рабочее время:</strong><br>{settings[0]} - {settings[1]}</p>
                    <p><strong>⏱️ Длительность:</strong><br>{settings[2]} минут</p>
                </div>
                """, unsafe_allow_html=True)