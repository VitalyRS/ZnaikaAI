from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
# import google.generativeai as genai
from openai import OpenAI

from newspaper import Article
import logging # Импортируем модуль logging

# Настройка логирования
# Это настроит Flask для использования логгера, который будет писать в Server log на PythonAnywhere
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Переменные окружения
API_KEY = os.getenv("API_AI")
TG_TOKEN = os.getenv("API_TELEGA")
AUTHORIZED_USER_ID = int(os.getenv("USER_ID"))
WEB_HOOK = os.getenv("WEB_HK")

# Инициализация

# Инициализация
try:
    if not API_KEY:
        raise ValueError("API_AI environment variable is not set.")
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
    logger.info("DeepSeek client configured successfully.")
except Exception as e:
    logger.error(f"Error configuring DeepSeek client: {e}")
    # Вы можете добавить sys.exit(1) здесь, если хотите, чтобы приложение падало при ошибке инициализации

try:
    if not TG_TOKEN:
        raise ValueError("API_TELEGA environment variable is not set.")
    bot = telebot.TeleBot(TG_TOKEN)
    logger.info("TeleBot initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing TeleBot: {e}")
    # Вы можете добавить sys.exit(1) здесь

app = Flask(__name__)

# Установим webhook при запуске
webhook_url = f"{WEB_HOOK}/{TG_TOKEN}"
try:
    bot.remove_webhook()
    logger.info("Existing webhook removed.")
    bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")
except Exception as e:
    logger.error(f"Error setting webhook: {e}")

# Хранилище пользовательских данных
user_data = {}

# ---------- Стили ----------
STYLES = {
    "style1": "разговорный",
    "style2": "ироничный",
    "style3": "инфостиль",
    "style4": "сторителлинг",
    "style5": "научпоп",
    "style6": "падонок",
    "style7": "восхваление политиков",
}

# ---------- Длины ----------
LENGTHS = {
    "short": 500,
    "medium": 1000,
    "long": 1500
}


def call_deepseek(prompt, model="deepseek-chat"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional assistant specializing in writing telegram posts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # print(f"Ошибка при вызове DeepSeek API: {e}")
        return None

# ---------- Генерация промпта ----------
def generate_prompt(text, url, style_key, length_key):
    length = LENGTHS[length_key]
    style = STYLES[style_key]
    logger.info(f"Generating prompt for style: {style_key}, length: {length_key}")

    prompts = {
        "style1": f"Напиши краткий, дружелюбный текст на русском в стиле разговора с другом. "
                  f"Без восклицательных знаков в заголовке, не используй *звёздочки*. "
                  f"Длина — около {length} символов. Добавь ссылку:"
                  f" {url} и 5 испанских хэштегов и 5 русских хэштегов. "
                  f"Вот текст:\n{text}",

        "style2": f"Сделай ироничный пересказ текста на русском. Заголовок — без ! и *. "
                  f"Длина ~{length} символов. В конце ссылка: {url} и 5 испанских хэштегов и 5 русских хэштегов. "
                  f"Текст:\n{text}",

        "style3": f"Сделай информативный пост на русском в инфостиле — ясно, структурно, с абзацами. "
                  f"Заголовок — без ! и *. Длина ~{length} символов. В конце ссылка: {url} и 5 испанских хэштегов и 5 русских хэштегов. "
                  f"Текст:\n{text}",

        "style4": f"Сделай пост в стиле сторителлинга на русском: заголовок, затем история. Без ! и *. "
                  f"Объём ~{length} символов. Формат — рассказ. В конце ссылка: {url} и 5 испанских хэштегов и 5 русских хэштегов. "
                  f"Текст:\n{text}",

        "style5": f"Сделай научно-популярный пересказ на русском — понятно, без упрощений. Стиль спокойный. "
                  f"Без ! и *. Длина ~{length} символов. В конце ссылка: {url} и 5 испанских хэштегов и 5 русских хэштегов. "
                  f"Текст:\n{text}",

        "style6": f"Сделай пост пересказ с заголовком в стиле падонков на русском — смешно и язвительно. "
                  f"Без ! и *. Длина ~{length} символов. В конце ссылка: {url} и 5 испанских хэштегов и 5 русских хэштегов. "
                  f"Текст:\n{text}",
        "style7": f"Сделай пост пересказ с заголовком в стиле восхваления, о как здорово, о как хорошо. Наши политики нас любят, они самые умные"
                  f"Без ! и *. Длина ~{length} символов. В конце ссылка: {url} и 5 испанских хэштегов и 5 русских хэштегов. "
                  f"Текст:\n{text}",
    }

    return prompts.get(style_key, "")

# ---------- Получение сводки ----------
def get_summary(url, style_key, length_key):
    logger.info(f"Attempting to get summary for URL: {url}")
    try:
        article = Article(url)
        article.download()
        logger.info(f"Article downloaded from {url}")
        article.parse()
        logger.info("Article parsed.")
        # print(article.text)
        prompt = generate_prompt(article.text, url, style_key, length_key)
        logger.info(f"Prompt generated. First 20 chars: {prompt[:20]}") # Логируем часть промпта

        # model = genai.GenerativeModel('gemini-2.0-flash')
        logger.info("Calling Gemini API...")
        response = call_deepseek(prompt, model="deepseek-chat")
        # print(response)
        summary = response
        logger.info(f"Summary received from Gemini. First 20 chars: {summary[:20]}")
        return summary
    except Exception as e:
        logger.error(f"Error in get_summary for URL {url}: {e}")
        raise # Перевыбрасываем исключение, чтобы его поймал обработчик в choose_length

# ---------- Webhook для Telegram ----------
# ---------- Webhook для Telegram ----------
@app.route(f'/{TG_TOKEN}', methods=['POST'])
def telegram_webhook():
    logger.info("Received Telegram webhook POST request.")

    try:
        json_data = request.get_json(force=True)
        # logger.info(f"Received JSON data: {json_data}")
        update = telebot.types.Update.de_json(json_data)

        if update.message:
            logger.info(f"Message received: '{update.message.text}' from chat {update.message.chat.id}")
            if update.message.chat.id !=AUTHORIZED_USER_ID:
                return
            if update.message.text.startswith("http"):
                handle_url(update.message)
            else:
                bot.send_message(update.message.chat.id, "Отправьте ссылку, начиная с http.")

        elif update.callback_query:
            data = update.callback_query.data
            logger.info(f"Callback received: '{data}' from chat {update.callback_query.message.chat.id}")
            if data.startswith("style:"):
                choose_style(update.callback_query)
            elif data.startswith("length:"):
                choose_length(update.callback_query)
            else:
                bot.send_message(update.callback_query.message.chat.id, "Неизвестная команда.")
        else:
            logger.info(f"Unhandled update type: {update}")

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        # logger.error(f"Raw request data: {request.data.decode('utf-8', 'ignore')}")
        return 'error', 500

    return 'ok', 200
# ---------- Обработка URL ----------
@bot.message_handler(func=lambda msg: msg.text.startswith("http"))
def handle_url(message):
    logger.info("----------------hyyp------------------") # Изменено на logger.info
    logger.info(f"!!! INSIDE handle_url: Message text: '{message.text}' from chat_id: {message.chat.id}")
    chat_id = message.chat.id
    if chat_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
        bot.send_message(chat_id, "Извините, этот бот предназначен только для авторизованных пользователей.")
        return

    user_data[chat_id] = {"url": message.text}
    logger.info(f"URL stored for chat_id {chat_id}: {message.text}")

    markup = InlineKeyboardMarkup()
    for key, label in STYLES.items():
        markup.add(InlineKeyboardButton(label, callback_data=f"style:{key}"))

    bot.send_message(chat_id, "Выбери стиль оформления текста:", reply_markup=markup)
    logger.info(f"Sent style choice to chat_id: {chat_id}")
    logger.info(f"--- Exiting handle_url ---")
# ---------- Выбор стиля ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("style:"))
def choose_style(call):
    chat_id = call.message.chat.id
    style_key = call.data.split(":")[1]
    logger.info(f"Received style callback from chat_id: {chat_id}, style: {style_key}")

    if chat_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized callback attempt from chat_id: {chat_id}")
        return

    user_data[chat_id]["style"] = style_key
    logger.info(f"Style '{style_key}' stored for chat_id: {chat_id}")

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Короткий", callback_data="length:short"),
        InlineKeyboardButton("Средний", callback_data="length:medium"),
        InlineKeyboardButton("Длинный", callback_data="length:long"),
    )

    bot.send_message(chat_id, "Теперь выбери длину текста:", reply_markup=markup)
    logger.info(f"Sent length choice to chat_id: {chat_id}")

# ---------- Выбор длины и генерация текста ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("length:"))
def choose_length(call):
    chat_id = call.message.chat.id
    length_key = call.data.split(":")[1]
    logger.info(f"Received length callback from chat_id: {chat_id}, length: {length_key}")

    if chat_id != AUTHORIZED_USER_ID:
        logger.warning(f"Unauthorized callback attempt from chat_id: {chat_id}")
        return

    if chat_id not in user_data or "url" not in user_data[chat_id] or "style" not in user_data[chat_id]:
        logger.error(f"Missing user data for chat_id {chat_id} before generating summary.")
        bot.send_message(chat_id, "Произошла ошибка: не удалось найти данные для обработки. Пожалуйста, начните заново, отправив URL.")
        return

    user_data[chat_id]["length"] = length_key
    url = user_data[chat_id]["url"]
    style = user_data[chat_id]["style"]
    logger.info(f"Length '{length_key}' stored for chat_id: {chat_id}. URL: {url}, Style: {style}")


    bot.send_message(chat_id, "Готовлю текст, подожди немного…")
    logger.info(f"Sending 'processing' message to chat_id: {chat_id}")

    try:
        summary = get_summary(url, style, length_key)
        logger.info(f"Successfully generated summary for chat_id: {chat_id}")
    except Exception as e:
        summary = f"Произошла ошибка при обработке статьи: {e}"
        logger.error(f"Error generating summary for chat_id {chat_id}: {e}")

    bot.send_message(chat_id, summary)
    logger.info(f"Sent summary to chat_id: {chat_id}")


@app.route('/')
def index():
    logger.info("Received GET request on /")
    return 'OK', 200

if __name__ == '__main__':

     app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
