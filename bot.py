import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================== НАСТРОЙКИ ==================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

ADMIN_ID = 8497016432
CHANNEL_INVITE_LINK = "https://t.me/+ZGxlgkAB-WhjYTQy"

# Изображения (сохрани именно с этими именами в папку с ботом!)
WELCOME_IMAGE = "welcome.jpg"      # Главный постер Over Leader
STICKERS_IMAGE = "stickers.jpg"    # Коллаж из 6 стикеров
SUCCESS_IMAGE = "success.jpg"      # Волк с галочкой
QR_IMAGE = "qr_code.jpg"           # QR-код 490 ₽

PAYMENT_AMOUNT = 490
PAYMENT_URL = "https://finance.ozon.ru/apps/sbp/ozonbankpay/019d6503-5b8f-7142-b3a7-f598d52b8366"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ================== ЗАГРУЗКА/СОХРАНЕНИЕ ДАННЫХ ==================
def load_data():
    if os.path.exists("bot_data.json"):
        with open("bot_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            data["approved"] = set(data.get("approved", []))
            data["pending"] = {int(k): v for k, v in data.get("pending", {}).items()}
            return data
    return {"approved": set(), "pending": {}}


def save_data(data):
    with open("bot_data.json", "w", encoding="utf-8") as f:
        json.dump({
            "approved": list(data["approved"]),
            "pending": {str(k): v for k, v in data["pending"].items()},
        }, f, ensure_ascii=False, indent=2)


# ================== КОМАНДА /start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()

    # Нижняя клавиатура
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("🚀 Купить доступ")]],
        resize_keyboard=True,
        persistent=True
    )

    if user.id in data["approved"]:
        await update.message.reply_text(
            "🎉 Вы уже имеете доступ в <b>Over Leader</b>!\n\n"
            "Нажмите кнопку ниже, чтобы открыть канал 👇",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Открыть канал", url=CHANNEL_INVITE_LINK)]
            ])
        )
        return

    # 1. Главный постер
    with open(WELCOME_IMAGE, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption="👋 <b>Добро пожаловать в Over Leader</b>\n\n"
                    "Премиальные стикеры • эксклюзивная коллекция",
            parse_mode="HTML",
            reply_markup=reply_keyboard
        )

    # 2. Коллаж стикеров (реклама)
    with open(STICKERS_IMAGE, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption="🔥 <b>Эксклюзивная коллекция премиальных стикеров</b>\n\n"
                    "Стильные, атмосферные, с характером — только для своих 🔥",
            parse_mode="HTML"
        )

    # 3. Волк с галочкой
    with open(SUCCESS_IMAGE, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption="✅ <b>После оплаты — мгновенный доступ</b>\n"
                    "к закрытому каналу со всеми стикерами",
            parse_mode="HTML"
        )

    # 4. QR-код + кнопки оплаты
    text = (
        f"💰 Стоимость доступа: <b>{PAYMENT_AMOUNT} ₽</b>\n\n"
        "Оплатите по QR-коду или по ссылке ниже.\n"
        "После оплаты нажмите кнопку «✅ Я оплатил»"
    )

    inline_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оплатить 490 ₽ через Ozon Банк", url=PAYMENT_URL)],
        [InlineKeyboardButton("✅ Я оплатил", callback_data="i_paid")]
    ])
    with open(QR_IMAGE, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=inline_kb
        )


# ================== КНОПКА «Я ОПЛАТИЛ» ==================
async def handle_i_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = load_data()

    if user_id in data["approved"]:
        await query.edit_message_caption(
            caption="✅ Вы уже имеете доступ в канал.",
            parse_mode="HTML"
        )
        return

    data["pending"][user_id] = query.message.chat_id
    save_data(data)

    await query.edit_message_caption(
        caption="📨 Оплата отправлена на проверку!\n"
                "Администратор проверит в ближайшее время ⏳",
        parse_mode="HTML"
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 <b>Новый запрос на доступ</b>\n\n"
             f"👤 @{query.from_user.username or 'без username'}\n"
             f"🆔 ID: <code>{user_id}</code>\n\n"
             f"Ожидает проверки оплаты.",
        parse_mode="HTML"
    )


# ================== ОБРАБОТКА ФОТО ЧЕКА ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()

    if user_id in data["approved"]:
        await update.message.reply_text("✅ У вас уже есть доступ в канал.")
        return

    data["pending"][user_id] = update.message.chat_id
    save_data(data)

    await update.message.reply_text(
        "📸 <b>Чек получен!</b>\n\n"
        "Администратор проверит оплату в ближайшее время ⏳",
        parse_mode="HTML"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{user_id}")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}")]
    ])

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"📥 <b>Новый чек от пользователя</b>\n"
                f"👤 @{update.effective_user.username or 'без username'}\n"
                f"🆔 ID: <code>{user_id}</code>\n\n"
                "Примите решение:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ================== ОБРАБОТКА РЕШЕНИЯ АДМИНА ==================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id_str = query.data.split(":")
    user_id = int(user_id_str)
    data = load_data()
    user_chat_id = data["pending"].get(user_id)

    if not user_chat_id:
        await query.edit_message_caption(caption="⚠️ Запрос уже обработан ранее.")
        return

    if action == "approve":
        data["approved"].add(user_id)
        data["pending"].pop(user_id, None)
        save_data(data)

        await context.bot.send_message(
            chat_id=user_chat_id,
            text="🎉 <b>Оплата успешно подтверждена!</b>\n\n"
                 "Добро пожаловать в <b>Over Leader</b>!\n\n"
                 "Нажмите кнопку ниже, чтобы вступить в канал 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Открыть канал", url=CHANNEL_INVITE_LINK)]
            ]),
            parse_mode="HTML"
        )

        await query.edit_message_caption(
            caption=f"✅ ОДОБРЕНО\nПользователь {user_id} получил доступ.",
            parse_mode="HTML"
        )

    elif action == "reject":
        data["pending"].pop(user_id, None)
        save_data(data)

        await context.bot.send_message(
            chat_id=user_chat_id,
            text="❌ <b>Оплата не подтверждена.</b>\n\n"
                 "Пожалуйста, отправьте корректный чек повторно или напишите администратору.",
            parse_mode="HTML"
        )
        await query.edit_message_caption(
            caption=f"❌ ОТКЛОНЕНО\nПользователь {user_id} уведомлён.",
            parse_mode="HTML"
        )


# ================== ЗАПУСК БОТА ==================
def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не задан в переменных окружения!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_i_paid, pattern="i_paid"))
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    app.add_handler(MessageHandler(filters.Regex("Купить доступ"), start))

    logger.info("🚀 Over Leader Bot успешно запущен и готов к работе!")
    app.run_polling()


if __name__ == "__main__":
    main()
