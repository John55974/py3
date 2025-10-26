# ===============================
# 🎰 Telegram Roulette Bot (Crypto Royale - Final FIXED Version)
# 👑 بواسطة JOHN OSAMA
# ===============================

from flask import Flask
from threading import Thread

import asyncio
import logging
import random
import json
import os
from typing import Dict
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, Bot, MenuButtonCommands
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# =========== إعداداتك الشخصية ===========
TOKEN = "8474184257:AAGR5025u_KzEf4Gywo5YH5qLb26Qf0vs_I"
OWNER_USERNAME = "J_O_H_N8"        # بدون @
BOT_DISPLAY_NAME = "Crypto Royale"
BOT_PUBLIC_LINK = "https://t.me/cryptoJohn0bot"  # رابط البوت
OWNER_CHANNEL_LINK = "https://t.me/CRYPTO2KING1"  # رابط القناة الرسمي

DATA_FILE = "data.json"
LOG_FILE = "bot.log"

# =========== إعداد اللوج ===========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()]
)

# =========== قواعد بيانات ===========
user_linked_channel: Dict[int, str] = {}
roulettes: Dict[str, dict] = {}
awaiting_channel_link = set()
awaiting_roulette_message = {}

# =========== تحميل / حفظ ===========
def load_data():
    global user_linked_channel
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_linked_channel = {int(k): v for k, v in data.get("user_linked_channel", {}).items()}

def save_data():
    data = {"user_linked_channel": {str(k): v for k, v in user_linked_channel.items()}}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========== لوحة الأزرار ===========
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 إنشاء روليت", callback_data="create_regular")],
        [InlineKeyboardButton("🔗 ربط قناتك", callback_data="link_channel"),
         InlineKeyboardButton("❌ فصل القناة", callback_data="unlink_channel")],
        [InlineKeyboardButton("📢 قناتي", url=OWNER_CHANNEL_LINK)]
    ])

# =========== زر /start ===========
async def set_commands_and_menu():
    bot = Bot(token=TOKEN)
    await bot.set_my_commands([BotCommand("start", "ابدأ البوت")])
    await bot.set_chat_menu_button(chat_id=None, menu_button=MenuButtonCommands())

# =========== /start ===========
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"🎉 مرحبًا في *{BOT_DISPLAY_NAME}*!\nاضغط على الأزرار بالأسفل 👇"
    if update.message:
        await update.message.reply_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

# =========== ربط القناة ===========
async def link_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    awaiting_channel_link.add(q.from_user.id)
    await q.edit_message_text("📌 أرسل الآن معرف أو رابط قناتك (مثال: @MyChannel أو https://t.me/MyChannel)")

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()
    if uid not in awaiting_channel_link:
        return

    if not (text.startswith("@") or "t.me/" in text):
        await update.message.reply_text("❌ أرسل @اسم القناة أو رابط t.me/... بشكل صحيح.")
        return

    try:
        chat = await context.bot.get_chat(text)
        me = await context.bot.get_me()
        member = await context.bot.get_chat_member(chat.id, me.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ تأكد أن البوت أدمن في القناة.")
            return
    except Exception:
        await update.message.reply_text("❌ لا يمكن الوصول للقناة. تأكد أن البوت أدمن.")
        return

    user_linked_channel[uid] = f"@{chat.username}" if chat.username else str(chat.id)
    save_data()
    awaiting_channel_link.remove(uid)
    await update.message.reply_text(f"✅ تم ربط القناة بنجاح: {user_linked_channel[uid]}")

# =========== إنشاء روليت ===========
async def create_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in user_linked_channel:
        await q.edit_message_text("❌ لم تربط قناتك بعد. استخدم زر 'ربط قناتك'.")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 أريد كتابة رسالة", callback_data="create_write_msg")],
        [InlineKeyboardButton("🚀 نشر بدون كتابة", callback_data="create_post_default")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
    ])
    await q.edit_message_text("اختر نوع الروليت الذي تريد نشره:", reply_markup=kb)

# =========== استقبال رسالة المستخدم ===========
async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid in awaiting_roulette_message:
        channel = awaiting_roulette_message.pop(uid)
        msg = update.message.text
        await post_roulette(uid, channel, msg, context)
        await update.message.reply_text("✅ تم نشر الروليت بنجاح ✅")
    else:
        await receive_channel(update, context)

# =========== نشر الروليت ===========
async def post_roulette(uid, channel, msg, context):
    try:
        sent = await context.bot.send_message(
            chat_id=channel,
            text=f"🎰 روليت جديد بواسطة [{BOT_DISPLAY_NAME}]({BOT_PUBLIC_LINK})\n\n{msg}\n\n🎯 اضغط للمشاركة:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 المشاركة (0)", callback_data="join")],
                [InlineKeyboardButton("⏹️ إيقاف المشاركة", callback_data="stop"),
                 InlineKeyboardButton("🏁 بدء السحب", callback_data="start_draw")]
            ])
        )
        roulettes[f"{sent.chat.id}:{sent.message_id}"] = {
            "owner_id": uid,
            "participants": [],
            "active": True,
        }
    except Exception as e:
        await context.bot.send_message(uid, f"❌ خطأ أثناء النشر: {e}")

# =========== روليت بدون كتابة ===========
async def create_post_default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    channel = user_linked_channel.get(uid)
    await post_roulette(uid, channel, "🎰 روليت جديد! اضغط للمشاركة 🎯", context)
    await q.edit_message_text("✅ تم نشر الروليت الافتراضي بنجاح!")

# =========== كتابة رسالة ===========
async def create_write_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    channel = user_linked_channel.get(uid)
    awaiting_roulette_message[uid] = channel
    await q.edit_message_text("✍️ اكتب الآن الرسالة التي تريد نشرها في الروليت:")

# =========== أزرار الروليت ===========
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    key = f"{q.message.chat.id}:{q.message.message_id}"

    if key not in roulettes:
        await q.answer("⚠️ حدث خطأ، الروليت غير معروف.", show_alert=True)
        return

    r = roulettes[key]
    if data == "join":
        if not r["active"]:
            await q.answer("❌ المشاركة مغلقة.", show_alert=True)
            return
        if uid in r["participants"]:
            await q.answer("✅ أنت مشارك بالفعل!", show_alert=True)
            return
        r["participants"].append(uid)
        count = len(r["participants"])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"👥 المشاركة ({count})", callback_data="join")],
            [InlineKeyboardButton("⏹️ إيقاف المشاركة", callback_data="stop"),
             InlineKeyboardButton("🏁 بدء السحب", callback_data="start_draw")]
        ])
        await context.bot.edit_message_reply_markup(q.message.chat.id, q.message.message_id, reply_markup=kb)
        await q.answer("✅ تم تسجيلك في السحب!")
    elif data == "stop" and uid == r["owner_id"]:
        r["active"] = False
        await q.answer("⏹️ تم إيقاف المشاركة.")
    elif data == "start_draw" and uid == r["owner_id"]:
        if not r["participants"]:
            await q.answer("⚠️ لا يوجد مشاركين.", show_alert=True)
            return
        winner = random.choice(r["participants"])
        await context.bot.send_message(q.message.chat.id, f"🏆 الفائز هو: [الشخص](tg://user?id={winner})", parse_mode="Markdown")
        del roulettes[key]
        await q.answer("تم اختيار الفائز 🎉")
    elif data == "back_main":
        await start_handler(update, context)

# =========== فصل القناة ===========
async def unlink_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    if uid in user_linked_channel:
        del user_linked_channel[uid]
        save_data()
    await q.edit_message_text("✅ تم فصل القناة بنجاح.", reply_markup=main_keyboard())

# =========== التشغيل ===========
def main():
    load_data()
    asyncio.run(set_commands_and_menu())

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(create_roulette, pattern="create_regular"))
    app.add_handler(CallbackQueryHandler(create_write_msg, pattern="create_write_msg"))
    app.add_handler(CallbackQueryHandler(create_post_default, pattern="create_post_default"))
    app.add_handler(CallbackQueryHandler(link_channel_prompt, pattern="link_channel"))
    app.add_handler(CallbackQueryHandler(unlink_channel, pattern="unlink_channel"))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message))

    logging.info("✅ البوت يعمل الآن...")
    app.run_polling(allowed_updates=["message", "callback_query"])


    from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


if __name__ == "__main__":
    keep_alive()  # <-- يخلي البوت صاحي 24 ساعة
    main()


if __name__ == "__main__":
    main()
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


if __name__ == "__main__":
    keep_alive()   # <-- السطر الجديد اللي بيخلي البوت صاحي
    main()


