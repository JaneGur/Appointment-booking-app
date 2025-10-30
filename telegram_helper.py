# telegram_helper.py
# Вспомогательный файл для отправки уведомлений из Streamlit

import asyncio
from telegram import Bot

# Токен бота (должен совпадать с bot.py)
BOT_TOKEN = "1781045290:AAHpvq7zsIcew9MOPtdHbV-l36rHCQOD2Mk"

def get_chat_id_by_username(username):
    """Получить chat_id по username из базы"""
    import sqlite3
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    
    username_clean = username.lower().replace('@', '')
    c.execute("SELECT chat_id FROM telegram_users WHERE username = ?", (username_clean,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None

async def send_telegram_message(chat_id, message):
    """Отправить сообщение в Telegram"""
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=message)
        return True
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return False

def notify_new_booking(username, booking_details):
    """Уведомить о новой записи"""
    if not username:
        return False
    
    chat_id = get_chat_id_by_username(username)
    if not chat_id:
        print(f"Пользователь @{username} не найден в Telegram")
        return False
    
    from datetime import datetime
    date_obj = datetime.strptime(booking_details['date'], '%Y-%m-%d')
    date_formatted = date_obj.strftime('%d.%m.%Y')
    
    message = (
        "✅ Вы успешно записаны на консультацию!\n\n"
        f"📅 Дата: {date_formatted}\n"
        f"🕐 Время: {booking_details['time']}\n"
        f"👤 Имя: {booking_details['name']}\n"
    )
    
    if booking_details.get('notes'):
        message += f"\n💬 {booking_details['notes']}\n"
    
    message += "\n❗️ Я пришлю напоминание за день до встречи!"
    
    # Запускаем асинхронную отправку
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(send_telegram_message(chat_id, message))
        loop.close()
        return result
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def notify_booking_cancelled(username, booking_details):
    """Уведомить об отмене записи"""
    if not username:
        return False
    
    chat_id = get_chat_id_by_username(username)
    if not chat_id:
        return False
    
    from datetime import datetime
    date_obj = datetime.strptime(booking_details['date'], '%Y-%m-%d')
    date_formatted = date_obj.strftime('%d.%m.%Y')
    
    message = (
        "❌ Ваша запись отменена консультантом\n\n"
        f"📅 Дата: {date_formatted}\n"
        f"🕐 Время: {booking_details['time']}\n\n"
        "Свяжитесь с консультантом для уточнения деталей."
    )
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(send_telegram_message(chat_id, message))
        loop.close()
        return result
    except Exception as e:
        print(f"Ошибка: {e}")
        return False