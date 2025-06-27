import logging
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import json
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

# ✅ আপনার Bot Token এখানে দিন
TOKEN = "7267282376:AAHj3WDaEmjMw1p1BwNeUlUCmE5naTqm--I"

# ✅ Admin ID এখানে দিন (আপনার Telegram ID)
ADMIN_ID = 123456789

# ✅ লগ ফাইল
DATA_FILE = "data.json"

# ✅ টাইম জোন
TIMEZONE = pytz.timezone("Asia/Dhaka")

# ✅ Conversation state
SET_NOTE = 1

# ✅ লগ সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ✅ Scheduler
scheduler = BackgroundScheduler()
scheduler.start()


# ✅ ডাটাবেস লোড/সেভ
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ✅ Start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 হ্যালো {user.first_name}! \nএই বট দিয়ে আপনি ৫টি নোট টাইমসহ সেট করতে পারবেন।\n/set দিয়ে শুরু করুন!"
    )
    # Admin log
    data = load_data()
    if str(user.id) not in data:
        data[str(user.id)] = {"notes": []}
    save_data(data)


# ✅ Set কমান্ড
async def set_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕒 আপনার টাইম এবং নোট লিখুন (Format: HH:MM AM/PM | নোট)\nউদাহরণ: 07:30 AM | খুলনার জন্য ডেকে দিও"
    )
    return SET_NOTE


async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    try:
        parts = text.split("|")
        time_part = parts[0].strip()
        note_part = parts[1].strip()

        note_time = datetime.strptime(time_part, "%I:%M %p")
        hour = note_time.hour
        minute = note_time.minute

        data = load_data()
        user_data = data.get(str(user.id), {"notes": []})

        if len(user_data["notes"]) >= 5:
            await update.message.reply_text("❌ আপনি সর্বোচ্চ ৫টি নোট রাখতে পারবেন।")
            return ConversationHandler.END

        user_data["notes"].append({
            "hour": hour,
            "minute": minute,
            "note": note_part
        })

        data[str(user.id)] = user_data
        save_data(data)

        # Scheduler এ কাজ যোগ
        scheduler.add_job(
            send_note,
            "cron",
            hour=hour,
            minute=minute,
            args=[user.id, note_part],
            timezone=TIMEZONE
        )

        await update.message.reply_text(f"✅ নোট সেভ হয়েছে: {time_part} ➜ {note_part}")
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"❌ ফরম্যাট ভুল! সঠিকভাবে লিখুন: HH:MM AM/PM | নোট")
        return ConversationHandler.END


async def send_note(user_id, note):
    application = Application.builder().token(TOKEN).build()
    await application.bot.send_message(chat_id=user_id, text=f"🔔 Reminder: {note}")

    # Admin log
    admin_msg = f"👤 User: {user_id} ➜ Note: {note}"
    await application.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)


# ✅ Mynotes কমান্ড
async def my_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    user_data = data.get(str(user.id), {"notes": []})
    if not user_data["notes"]:
        await update.message.reply_text("❌ কোনো নোট নেই!")
        return
    text = "🗒️ আপনার নোটসমূহ:\n"
    for n in user_data["notes"]:
        time_str = f"{n['hour']:02}:{n['minute']:02}"
        text += f"🕒 {time_str} ➜ {n['note']}\n"
    await update.message.reply_text(text)


# ✅ Logs কমান্ড (Admin)
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ আপনি এডমিন নন!")
        return
    data = load_data()
    text = "📋 লগসমূহ:\n"
    for uid, udata in data.items():
        text += f"👤 User {uid}:\n"
        for n in udata["notes"]:
            time_str = f"{n['hour']:02}:{n['minute']:02}"
            text += f"   🕒 {time_str} ➜ {n['note']}\n"
    await update.message.reply_text(text)


# ✅ Stop কমান্ড
async def stop_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    if str(user.id) in data:
        data[str(user.id)]["notes"] = []
        save_data(data)
        await update.message.reply_text("✅ সব নোট বন্ধ করা হয়েছে!")
    else:
        await update.message.reply_text("❌ কোনো নোট সেট করা নেই!")


# ✅ Who কমান্ড (Admin)
async def who(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ আপনি এডমিন নন!")
        return
    data = load_data()
    text = "👥 বট ইউজারসমূহ:\n"
    for uid in data.keys():
        text += f"🔹 User: {uid}\n"
    await update.message.reply_text(text)


# ✅ Broadcast কমান্ড (Admin)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ আপনি এডমিন নন!")
        return
    msg = " ".join(context.args)
    data = load_data()
    for uid in data.keys():
        await context.bot.send_message(chat_id=uid, text=f"📢 Admin Message:\n{msg}")
    await update.message.reply_text("✅ ব্রডকাস্ট সম্পূর্ণ!")


# ✅ Main
def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set", set_note)],
        states={
            SET_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_note)],
        },
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("mynotes", my_notes))
    application.add_handler(CommandHandler("stop", stop_notes))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("who", who))
    application.add_handler(CommandHandler("broadcast", broadcast))

    application.run_polling()


if __name__ == "__main__":
    main()
