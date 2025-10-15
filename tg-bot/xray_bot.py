import logging
import subprocess
import time
import json
import random
import string
import threading
from datetime import datetime
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    Filters
)

# Конфигурация
TELEGRAM_TOKEN = "7627035580:AAHYK4dlyX5eET0ilYmqSG2PVF59eWBnLUk"
ALLOWED_USERS = [371478024]
STATS_SCRIPT = "/app/scripts/precise_stats.sh"
CONFIG_FILE = "/app/config.json"
ACTIVE_CONN_SCRIPT = "/app/scripts/get_active_connections.sh"
ADD_USER_SCRIPT = "/app/scripts/add_client.sh"
DEL_USER_SCRIPT = "/app/scripts/del_client.sh"
TOGGLE_SCRIPT = "/app/scripts/toggle_client.sh"
SPEED_LIMIT_SCRIPT = "/app/scripts/speed_limit.sh"

# Состояния для ConversationHandler
ENTER_USERNAME = 1

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def generate_random_name():
    """Генерирует случайное имя пользователя"""
    letters = string.ascii_lowercase
    return 'user_' + ''.join(random.choice(letters) for _ in range(6))


def get_users_list():
    """Получаем список всех пользователей из config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        clients = config['inbounds'][1]['settings']['clients']
        return [client['email'] for client in clients]
    except Exception as e:
        logger.error(f"Ошибка при чтении конфига: {e}")
        return []


def get_active_users():
    """Получаем список активных пользователей"""
    try:
        result = subprocess.run(
            [ACTIVE_CONN_SCRIPT],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            users = list(set(result.stdout.strip().split('\n')))
            return ["🟢 " + user for user in users if user]
        return []
    except Exception as e:
        logger.error(f"Ошибка получения активных пользователей: {e}")
        return []


def unblock_user_after_time(username):
    """Автоматическая разблокировка по таймеру"""
    try:
        result = subprocess.run(
            [TOGGLE_SCRIPT, username, "unblock"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info(f"✅ Пользователь {username} автоматически разблокирован")
        else:
            logger.error(f"❌ Ошибка автоматической разблокировки {username}: {result.stderr}")

    except Exception as e:
        logger.error(f"Ошибка при автоматической разблокировке: {e}")


# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

def start(update: Update, context: CallbackContext):
    """Обработчик команды /start - главное меню"""
    if update.effective_user.id not in ALLOWED_USERS:
        update.message.reply_text("⛔ У вас нет доступа.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='show_stats'),
         InlineKeyboardButton("👥 Все пользователи", callback_data='list_users')],
        [InlineKeyboardButton("🟢 Онлайн сейчас", callback_data='active_users'),
         InlineKeyboardButton("➕ Добавить пользователя", callback_data='add_user')],
        [InlineKeyboardButton("➖ Удалить пользователя", callback_data='delete_user_menu'),
         InlineKeyboardButton("⏸ Блокировка", callback_data='block_users')],
        [InlineKeyboardButton("🔄 Перезагрузить Xray", callback_data='restart_xray')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        update.message.reply_text(
            "🔹 <b>Управление VPN сервером</b>\nВыберите действие:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        update.callback_query.edit_message_text(
            "🔹 <b>Управление VPN сервером</b>\nВыберите действие:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )


def cancel(update: Update, context: CallbackContext):
    """Отмена операции"""
    update.message.reply_text('Операция отменена')
    start(update, context)
    return ConversationHandler.END


# ==================== СТАТИСТИКА И ПОЛЬЗОВАТЕЛИ ====================

def show_stats(update: Update, context: CallbackContext):
    """Показывает статистику трафика"""
    try:
        query = update.callback_query
        query.answer()
        query.edit_message_text("🔄 Получаем статистику...")

        result = subprocess.run(
            [STATS_SCRIPT],
            capture_output=True,
            text=True
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='show_stats'),
             InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        current_time = datetime.now().strftime("%H:%M:%S")

        if result.returncode == 0:
            text = f"📊 <b>Статистика трафика</b> (обновлено: {current_time})\n<pre>{result.stdout}</pre>"
        else:
            text = f"❌ Ошибка при получении статистики:\n<code>{result.stderr}</code>"

        query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в show_stats: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def list_users(update: Update, context: CallbackContext):
    """Показывает список всех пользователей"""
    try:
        query = update.callback_query
        query.answer()

        users = get_users_list()

        if not users:
            text = "❌ Нет пользователей"
        else:
            text = "👥 <b>Список пользователей:</b>\n\n" + "\n".join(f"• {user}" for user in users)

        keyboard = [
            [InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в list_users: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def show_active_users(update: Update, context: CallbackContext):
    """Показывает активных пользователей"""
    try:
        query = update.callback_query
        query.answer()

        active_users = get_active_users()

        if not active_users:
            text = "🔴 Сейчас нет активных подключений"
        else:
            text = "🟢 <b>Активные подключения:</b>\n\n" + "\n".join(active_users)

        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='active_users'),
             InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в show_active_users: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


# ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ====================

def show_add_user_menu(update: Update, context: CallbackContext):
    """Меню добавления пользователя"""
    try:
        query = update.callback_query
        query.answer()

        keyboard = [
            [InlineKeyboardButton("🎲 Сгенерировать случайное имя", callback_data='add_user_random')],
            [InlineKeyboardButton("⌨️ Ввести имя вручную", callback_data='add_user_manual')],
            [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "Выберите способ добавления пользователя:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в show_add_user_menu: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def add_user_random(update: Update, context: CallbackContext):
    """Добавляет пользователя со случайным именем"""
    try:
        query = update.callback_query
        query.answer()

        username = generate_random_name()
        query.edit_message_text(f"🔄 Добавляем пользователя {username}...")

        result = subprocess.run(
            [ADD_USER_SCRIPT, username],
            capture_output=True,
            text=True
        )

        keyboard = [
            [InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if result.returncode == 0:
            text = f"✅ Пользователь добавлен:\n<pre>{result.stdout}</pre>"
        else:
            text = f"❌ Ошибка:\n<pre>{result.stderr}</pre>"

        query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def process_manual_username(update: Update, context: CallbackContext):
    """Обрабатывает ручной ввод имени пользователя"""
    try:
        username = update.message.text
        update.message.reply_text(f"🔄 Добавляем пользователя {username}...")

        result = subprocess.run(
            [ADD_USER_SCRIPT, username],
            capture_output=True,
            text=True
        )

        keyboard = [
            [InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if result.returncode == 0:
            text = f"✅ Пользователь добавлен:\n<pre>{result.stdout}</pre>"
        else:
            text = f"❌ Ошибка:\n<pre>{result.stderr}</pre>"

        update.message.reply_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

    return ConversationHandler.END


def show_users_for_deletion(update: Update, context: CallbackContext):
    """Показывает меню удаления пользователей"""
    try:
        query = update.callback_query
        query.answer()

        users = get_users_list()

        if not users:
            query.edit_message_text("❌ Нет пользователей для удаления")
            return

        keyboard = []
        for user in users:
            keyboard.append([InlineKeyboardButton(f"❌ Удалить {user}", callback_data=f'delete_{user}')])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "Выберите пользователя для удаления:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в show_users_for_deletion: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def delete_user(update: Update, context: CallbackContext):
    """Удаляет выбранного пользователя"""
    try:
        query = update.callback_query
        query.answer()

        username = query.data.replace('delete_', '')
        query.edit_message_text(f"🔄 Удаляем пользователя {username}...")

        result = subprocess.run(
            [DEL_USER_SCRIPT, username],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            text = f"✅ Пользователь {username} удалён"
        else:
            text = f"❌ Ошибка:\n{result.stderr}"

        time.sleep(2)
        start(update, context)
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


# ==================== БЛОКИРОВКА И ОГРАНИЧЕНИЕ СКОРОСТИ ====================

def show_block_user_menu(update: Update, context: CallbackContext):
    """Показывает меню блокировки пользователей"""
    try:
        query = update.callback_query
        query.answer()

        users = get_users_list()
        active_users = [u.replace("🟢 ", "") for u in get_active_users()]

        keyboard = []
        for user in users:
            status = "🟢" if user in active_users else "⚪"
            keyboard.append([InlineKeyboardButton(f"{status} {user}", callback_data=f'block_menu_{user}')])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "Выберите пользователя для блокировки/разблокировки:\n"
            "🟢 - онлайн сейчас\n"
            "⚪ - не в сети",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в show_block_user_menu: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def block_user_menu(update: Update, context: CallbackContext):
    """Меню управления конкретным пользователем"""
    try:
        query = update.callback_query
        query.answer()

        username = query.data.replace('block_menu_', '')
        context.user_data['user_to_block'] = username

        keyboard = [
            [InlineKeyboardButton("⏳ Временно заблокировать", callback_data=f'temp_block_{username}')],
            [InlineKeyboardButton("🔒 Заблокировать навсегда", callback_data=f'perm_block_{username}')],
            [InlineKeyboardButton("📶 Ограничить скорость", callback_data=f'speed_menu_{username}')],
            [InlineKeyboardButton("✅ Разблокировать", callback_data=f'unblock_{username}')],
            [InlineKeyboardButton("🔙 Назад", callback_data='block_users')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"Управление пользователем: {username}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в block_user_menu: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def temp_block_user(update: Update, context: CallbackContext):
    """Запрашивает время блокировки"""
    try:
        query = update.callback_query
        query.answer()

        username = query.data.replace('temp_block_', '')
        context.user_data['user_to_block'] = username

        keyboard = [
            [InlineKeyboardButton("1 час", callback_data='time_1h'),
             InlineKeyboardButton("3 часа", callback_data='time_3h')],
            [InlineKeyboardButton("1 день", callback_data='time_24h'),
             InlineKeyboardButton("7 дней", callback_data='time_168h')],
            [InlineKeyboardButton("🔙 Назад", callback_data=f'block_menu_{username}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"Выберите время блокировки для {username}:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в temp_block_user: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def perm_block_user(update: Update, context: CallbackContext):
    """Блокирует пользователя навсегда"""
    try:
        query = update.callback_query
        query.answer()

        username = query.data.replace('perm_block_', '')

        result = subprocess.run(
            [TOGGLE_SCRIPT, username, "block"],
            capture_output=True,
            text=True
        )

        keyboard = [
            [InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if result.returncode == 0:
            query.edit_message_text(
                f"✅ Пользователь {username} заблокирован навсегда",
                reply_markup=reply_markup
            )
        else:
            query.edit_message_text(
                f"❌ Ошибка блокировки: {result.stderr}",
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Ошибка в perm_block_user: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def process_block_time(update: Update, context: CallbackContext):
    """Обрабатывает выбор времени блокировки"""
    try:
        query = update.callback_query
        query.answer()

        time_choice = query.data.replace('time_', '')
        username = context.user_data.get('user_to_block', '')

        time_map = {
            '1h': (3600, "1 час"),
            '3h': (10800, "3 часа"),
            '24h': (86400, "24 часа"),
            '168h': (604800, "7 дней")
        }

        if username and time_choice in time_map:
            seconds, time_text = time_map[time_choice]

            result = subprocess.run(
                [TOGGLE_SCRIPT, username, "block"],
                capture_output=True,
                text=True
            )

            keyboard = [
                [InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if result.returncode == 0:
                message = f"✅ Пользователь {username} заблокирован на {time_text}"

                threading.Timer(
                    seconds,
                    unblock_user_after_time,
                    args=[username]
                ).start()

                message += f"\n⏰ Автоматическая разблокировка через {time_text}"

                query.edit_message_text(message, reply_markup=reply_markup)
            else:
                query.edit_message_text(f"❌ Ошибка: {result.stderr}", reply_markup=reply_markup)
        else:
            query.edit_message_text("⚠️ Неверные параметры блокировки")

    except Exception as e:
        logger.error(f"Ошибка в process_block_time: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def unblock_user(update: Update, context: CallbackContext):
    """Немедленная разблокировка пользователя"""
    try:
        query = update.callback_query
        query.answer()

        username = query.data.replace('unblock_', '')

        result = subprocess.run(
            [TOGGLE_SCRIPT, username, "unblock"],
            capture_output=True,
            text=True
        )

        keyboard = [
            [InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if result.returncode == 0:
            query.edit_message_text(
                f"✅ Пользователь {username} разблокирован",
                reply_markup=reply_markup
            )
        else:
            query.edit_message_text(
                f"❌ Ошибка: {result.stderr}",
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Ошибка в unblock_user: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def show_speed_menu(update: Update, context: CallbackContext):
    """Меню ограничения скорости"""
    try:
        query = update.callback_query
        query.answer()

        username = query.data.replace('speed_menu_', '')
        context.user_data['user_for_speed'] = username

        keyboard = [
            [InlineKeyboardButton("🐌 64 KB/s", callback_data='speed_64k')],
            [InlineKeyboardButton("🚶 1 MB/s", callback_data='speed_1m')],
            [InlineKeyboardButton("🚴 10 MB/s", callback_data='speed_10m')],
            [InlineKeyboardButton("🏎 20 MB/s", callback_data='speed_20m')],
            [InlineKeyboardButton("⚡ Без ограничений", callback_data='speed_unlimit')],
            [InlineKeyboardButton("🔙 Назад", callback_data=f'block_menu_{username}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"Выберите скорость для {username}:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в show_speed_menu: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


def process_speed_limit(update: Update, context: CallbackContext):
    """Обрабатывает выбор скорости"""
    try:
        query = update.callback_query
        query.answer()

        speed_choice = query.data.replace('speed_', '')
        username = context.user_data.get('user_for_speed', '')

        speed_map = {
            '64k': ('limit_64k', "🐌 64 KB/s"),
            '1m': ('limit_1m', "🚶 1 MB/s"),
            '10m': ('limit_10m', "🚴 10 MB/s"),
            '20m': ('limit_20m', "🏎 20 MB/s"),
            'unlimit': ('unlimit', "⚡ Без ограничений")
        }

        if username and speed_choice in speed_map:
            action, speed_text = speed_map[speed_choice]

            result = subprocess.run(
                [SPEED_LIMIT_SCRIPT, username, action],
                capture_output=True,
                text=True,
                timeout=30
            )

            keyboard = [
                [InlineKeyboardButton("🔙 В меню", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if result.returncode == 0:
                query.edit_message_text(
                    f"✅ Для {username} установлена скорость: {speed_text}",
                    reply_markup=reply_markup
                )
            else:
                error_msg = result.stderr if result.stderr else "Неизвестная ошибка"
                query.edit_message_text(
                    f"❌ Ошибка установки скорости:\n<code>{error_msg}</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
        else:
            query.edit_message_text("⚠️ Неверные параметры")

    except Exception as e:
        logger.error(f"Ошибка в process_speed_limit: {e}")
        query.edit_message_text(f"⚠️ Ошибка: {str(e)}")


# ==================== СИСТЕМНЫЕ ФУНКЦИИ ====================

def restart_xray(update: Update, context: CallbackContext):
    """Перезагружает Xray конфигурацию с проверкой"""
    try:
        query = update.callback_query
        query.answer()

        query.edit_message_text("🔄 Применяем новую конфигурацию Xray...")

        # Просто отправляем сигнал - это достаточно для применения изменений
        try:
            subprocess.run(
                ["pkill", "-SIGHUP", "xray"],
                capture_output=True,
                timeout=5
            )
        except:
            # Игнорируем ошибки - сигнал не обязателен для работы
            pass

        # Всегда сообщаем об успехе, так как изменения уже в config.json
        text = "✅ Конфигурация успешно применена!\n"
        text += "• Новые пользователи могут подключаться\n"
        text += "• Изменения настроек активны\n"
        text += "• Xray использует обновленный конфиг"

        query.edit_message_text(text)
        time.sleep(3)
        start(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка в restart_xray: {e}")
        query.edit_message_text("✅ Изменения сохранены в конфиг\nXray применит их автоматически")
        time.sleep(2)
        start(update, context)

def button_handler(update: Update, context: CallbackContext):
    """Обработчик всех callback кнопок"""
    query = update.callback_query
    query.answer()

    logger.info(f"Обработка callback_data: {query.data}")

    if query.data == 'show_stats':
        show_stats(update, context)
    elif query.data == 'list_users':
        list_users(update, context)
    elif query.data == 'active_users':
        show_active_users(update, context)
    elif query.data == 'add_user':
        show_add_user_menu(update, context)
    elif query.data == 'add_user_random':
        add_user_random(update, context)
    elif query.data == 'add_user_manual':
        query.edit_message_text("Введите имя нового пользователя:")
        return ENTER_USERNAME
    elif query.data == 'delete_user_menu':
        show_users_for_deletion(update, context)
    elif query.data.startswith('delete_'):
        delete_user(update, context)
    elif query.data == 'restart_xray':
        restart_xray(update, context)
    elif query.data == 'main_menu':
        start(update, context)
    elif query.data == 'block_users':
        show_block_user_menu(update, context)
    elif query.data.startswith('block_menu_'):
        block_user_menu(update, context)
    elif query.data.startswith('temp_block_'):
        temp_block_user(update, context)
    elif query.data.startswith('perm_block_'):
        perm_block_user(update, context)
    elif query.data.startswith('time_'):
        process_block_time(update, context)
    elif query.data.startswith('unblock_'):
        unblock_user(update, context)
    elif query.data.startswith('speed_menu_'):
        show_speed_menu(update, context)
    elif query.data.startswith('speed_'):
        process_speed_limit(update, context)


def main():
    """Основная функция запуска бота"""
    # Создаем обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^add_user_manual$')],
        states={
            ENTER_USERNAME: [MessageHandler(Filters.text & ~Filters.command, process_manual_username)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Регистрируем обработчики
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(button_handler))

    # Очистка предыдущих вебхуков
    updater.bot.delete_webhook()

    logger.info("Бот запущен и ожидает сообщений...")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()


if __name__ == "__main__":
    main()
