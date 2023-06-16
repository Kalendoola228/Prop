import telegram
import sqlite3
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters, CallbackQueryHandler

# Создание объекта Bot с указанием токена доступа
bot = telegram.Bot('5939437359:AAFwkeJxSr7aNNsfK5zGSZz0CY3j2duixuo')
TOKEN = '5939437359:AAFwkeJxSr7aNNsfK5zGSZz0CY3j2duixuo'

# Подключение к базе данных SQLite
conn = sqlite3.connect('visitors.db')
cursor = conn.cursor()
user_data = {}
updater = Updater(token = TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Определение функции для обработки команды /stop
def stop_bot(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Остановка бота...")
    updater.stop()

# Создание таблицы visitors (если еще не создана)
def create_table():
    conn = sqlite3.connect('visitors.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            time TEXT,
            to_whom TEXT,
            room TEXT,
            car_brand TEXT,
            car_number TEXT,
            requested_by TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_table()

def callback_dispatcher(update: Update, context: CallbackContext):
    query = update.callback_query

    print('Received callback data:', query.data)

    if query.data == 'save_visitor':
        save_visitor_callback(update, context)
    elif query.data == 'soglas_1': # Добавленный обработчик callback-запросов для команды "soglas_1"
        soglas_1_callback(update, context)
        print('Soglas_1 callback executed')
    else:
        context.bot.answer_callback_query(callback_query_id=query.id)

# Определение функции для проверки сообщения на текстовый формат
def is_text(update: Update, context: CallbackContext) -> bool:
    """Return True if the message is a text message."""
    return update.message and update.message.text

# Функция для вывода клавиатуры при старте бота
def initial_keyboard(update, context: CallbackContext):
    # Создание кнопок для сохранения данных
    buttons = [
        [
            InlineKeyboardButton(text="Согласовать с 1", callback_data="soglas_1_callback"),
            InlineKeyboardButton(text="Согласовать с 2", callback_data="soglas_2")
        ]
    ]

    # Создание объекта клавиатуры
    keyboard = InlineKeyboardMarkup(buttons)

    # Отправка клавиатуры пользователю
    context.bot.send_message(chat_id=update.effective_chat.id, text="С кем согласовать:", reply_markup=keyboard)

# Функция для обработки команды /start
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Чтобы зарегистрировать посетителя, напишите его ФИО, время посещения, к кому он идёт, номер кабинета, марку автомобиля и гос. номер через запятую. Например: Иванов Иван Иванович, 10:00, директор, 101, BMW, А123ВВ")
    initial_keyboard(update, context)

# Функция для обработки команды /help
def help_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Список доступных команд:\n/show_visitors - Показать список посетителей\n/save_visitor - Зарегистрировать посетителя")
    initial_keyboard(update, context)

# Функция для отображения списка посетителей
def show_visitors(update, context):
    # Получение списка всех посетителей из базы данных
    conn = sqlite3.connect('visitors.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM visitors''')
    rows = cursor.fetchall()

    # Формирование текста сообщения со списком посетителей
    message = "Список посетителей:\n\n"
    for row in rows:
        message += "{}\nДата: {}\nВремя: {}\nК кому: {}\nКабинет: {}\nМарка автомобиля: {}\nГос. номер: {}\n\n".format(row[1], row[2], row[3], row[4], row[5], row[6], row[7])
        
    print(message)
    # Отправка сообщения с данными о посетителях
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    initial_keyboard(update, context)
    conn.close()

# Функция для сохранения данных о посетителе
def save_visitor(update, context):
    # Запрос на ввод данных о посетителе
    context.bot.send_message(chat_id=update.effective_chat.id, text="Введите данные о посетителе (ФИО, дата, время, к кому, кабинет, марка автомобиля, гос. номер), разделенные запятыми:")
    
    # Установка обработчика сообщений с текстом
    text_handler = MessageHandler(Filters.text & ~Filters.command, handle_message)
    context.dispatcher.add_handler(text_handler)

    # Добавление клавиатуры выбора согласующего
    initial_soglas(update, context)

    # Добавление информации о том, кто запросил согласование
    user_id = update.message.chat_id
    requested_by = update.message.from_user.username
    context.user_data[user_id].append(requested_by)

def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text
    user_id = update.message.chat_id
    
    # проверяем, что пользователь уже был добавлен в словарь
    if user_id not in context.user_data:
        context.user_data[user_id] = []
    
    # разбиваем текст сообщения на части и добавляем в список данных пользователя
    user_data_parts = message_text.split(',')
    context.user_data[user_id].extend(user_data_parts)
    
    context.bot.send_message(chat_id=update.effective_chat.id, text="Данные сохранены")
    initial_keyboard(update, context)
    print(len(context.user_data[user_id]))

# Функция для получения данных из словаря
def get_data_from_dict(data_dict):
    data_list = []
    for data in data_dict.values():
        data_list.append(",".join(data))
    return data_list

# Функция для отправки запроса на согласование
def send_approval_request(visitor_data, requested_by, approval_function):
    # Создание текста запроса на согласование
    message_text = f"Пропуск на согласование:\nФИО: {visitor_data['name']}\nДата: {visitor_data['date']}\nВремя посещения: {visitor_data['time']}\nКому: {visitor_data['to_whom']}\nКабинет: {visitor_data['room']}"
    if visitor_data['car_brand']:
        message_text += f"\nМарка автомобиля: {visitor_data['car_brand']}"
    if visitor_data['car_number']:
        message_text += f"\nГос. номер: {visitor_data['car_number']}"
    message_text += f"\nЗапрошено пользователем: {requested_by}"

    # Отправка запроса на согласование
    approval_function(message_text)

# Функция для обработки команды /soglas_1
# Определение функции для обработки нажатия на кнопку "Согласовать с 1"
#(def soglas_1_callback(update: Update, context: CallbackContext):
#    print(context.user_data)
#    print('111')
#    user_id = update.callback_query.from_user.id
#    user_data = context.user_data.get(user_id)
#
#    if not user_data or len(user_data) < 5:
#        context.bot.send_message(chat_id=update.effective_chat.id, text="Недостаточно данных для согласования")
#        initial_keyboard(update, context)
#        return

def soglas_1_callback(update, context):
    query = update.callback_query
    print('Кнопка "Согласовать с 1" была нажата') # Добавляем эту строку для логирования
    query.answer()
    query.message.reply_text('Команда /soglas_1 была вызвана')
    context.bot.send_message(chat_id=query.message.chat_id, text='/soglas_1')

    # Формирование текста сообщения
    message_text = f"Пропуск на согласование: {user_data[0]}\nДата: {user_data[1]}\nВремя: {user_data[2]}\nКому: {user_data[3]}\nКабинет: {user_data[4]}"
    
    # Отправка сообщения для согласования пользователю с ID 359155951
    context.bot.send_message(chat_id=359155951, text=message_text)

    # Создание inline клавиатуры с кнопками "Да" и "Нет"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="yes"),
         InlineKeyboardButton("Нет", callback_data="no")]
    ])

    # Отправка сообщения с inline клавиатурой пользователю
    context.bot.send_message(chat_id=user_id, text='Сообщение отправлено на согласование.', reply_markup=reply_markup)

    initial_keyboard(update, context)
    




def soglas_1_decision_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    # Отправка сообщения пользователю о решении по согласованию
    if query.data == 'yes':
        context.bot.send_message(chat_id=user_id, text="Пропуск согласован")
        user_data = context.user_data.get(user_id)
        visitor_data = {
            "name": user_data[0],
            "date": user_data[1],
            "time": user_data[2],
            "to_whom": user_data[3],
            "room": user_data[4],
            "car_brand": user_data[5] if len(user_data) > 5 and user_data[5] else None,
            "car_number": user_data[6] if len(user_data) > 6 and user_data[6] else None
        }
        save_visitor_to_db(visitor_data, query.from_user.username)
    elif query.data == 'no':
        context.bot.send_message(chat_id=user_id, text="Пропуск не согласован")

    # Удаление данных пользователя из словаря

    initial_keyboard(update, context)

# Функция для сохранения данных о посетителе в базу данных
def save_visitor_to_db(visitor_data, requested_by):
    conn = sqlite3.connect('visitors.db')
    cursor = conn.cursor()

    # Вставка данных о посетителе в таблицу visitors
    cursor.execute('''INSERT INTO visitors(name, date, time, to_whom, room, car_brand, car_number, requested_by) VALUES(?,?,?,?,?,?,?,?)''', (visitor_data['name'], visitor_data['date'], visitor_data['time'], visitor_data['to_whom'], visitor_data['room'], visitor_data['car_brand'], visitor_data['car_number'], requested_by))

    # Сохранение изменений в базе данных
    conn.commit()
    conn.close()

# Функция для обработки команды /save_visitor
def save_visitor_command(update, context: CallbackContext):
    # Получение данных о посетителе из словаря
    user_id = update.message.chat_id
    user_data = context.user_data.get(user_id)
    
    if not user_data or len(user_data) < 5:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Отсутствуют данные о посетителе")
        initial_keyboard(update, context)
        return
    
    visitor_data = {
        "name": user_data[0],
        "date": user_data[1],
        "time": user_data[2],
        "to_whom": user_data[3],
        "room": user_data[4],
        "car_brand": user_data[5] if len(user_data) > 5 and user_data[5] else None,
        "car_number": user_data[6] if len(user_data) > 6 and user_data[6] else None
    }

    # Сохранение данных о посетителе в базе данных
    save_visitor_to_db(visitor_data, update.message.from_user.username)

    # Очистка словаря
    context.user_data.pop(user_id)

    context.bot.send_message(chat_id=update.effective_chat.id, text="Данные сохранены в базе данных")
    initial_keyboard(update, context)

# Создание объекта Updater и добавление обработчиков команд
updater = Updater(token='5939437359:AAFwkeJxSr7aNNsfK5zGSZz0CY3j2duixuo', use_context=True)

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('help', help_command))
updater.dispatcher.add_handler(CommandHandler('stop', stop_bot))
updater.dispatcher.add_handler(CommandHandler('show_visitors', show_visitors))
updater.dispatcher.add_handler(CommandHandler('save_visitor', save_visitor_command))
#updater.dispatcher.add_handler(CommandHandler('soglas_1', soglas_1_callback))
#updater.dispatcher.add_handler(CommandHandler('soglas_2', soglas_2))
updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
# Добавление обработчика команды "/soglas_1"
updater.dispatcher.add_handler(CommandHandler('soglas_1', soglas_1_callback))
updater.dispatcher.add_handler(CallbackQueryHandler(soglas_1_decision_callback))
soglas_1_handler = CallbackQueryHandler(soglas_1_callback)
dispatcher.add_handler(soglas_1_handler)


# Добавление обработчика callback-запросов для команды "soglas_1"
updater.dispatcher.add_handler(CallbackQueryHandler(soglas_1_callback, pattern='soglas_1_callback'))


# Запуск бота
updater.start_polling()

# Запуск бесконечного цикла для работы бота
updater.idle()
