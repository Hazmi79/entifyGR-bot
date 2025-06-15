
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import datetime
import pytz

# Set timezone
tz = pytz.timezone('Asia/Kuala_Lumpur')

# Bot token
BOT_TOKEN = "7605691181:AAF1KAiBGEVEUtNkY3c80y8Ys4JvDCbModU"

# Conversation states
PASSWORD, ACTIVE, MCQ = range(3)

# Welcome video
WELCOME_VIDEO_URL = "https://drive.google.com/uc?export=download&id=1NobniS5bIXeLzIWTPgsHQN1ASMTj4VTX"

# ENT cases (easily extendable list)
CASES = [
    {
        "title": "CASE 1: Swollen Ear",
        "video": "https://drive.google.com/uc?export=download&id=12q3m-dTtursM8N56sY13fJFrxThICv_g",
        "questions": [
            {
                "question": "What is the most likely diagnosis?",
                "options": [
                    "A) Otitis externa",
                    "B) Perichondritis",
                    "C) Cellulitis of the ear lobule",
                    "D) Mastoiditis"
                ],
                "answer": 1,
                "feedback": [
                    "❌ Otitis externa usually involves the ear canal and does not spare the lobule.",
                    "✅ Correct! Perichondritis presents with erythema and swelling of the pinna sparing the lobule.",
                    "❌ Cellulitis of the lobule involves the fatty lobule, which is spared in perichondritis.",
                    "❌ Mastoiditis affects the mastoid area behind the ear, not the pinna itself."
                ]
            }
        ]
    },
    # ➕ To add a new case, copy this structure and paste as another dictionary in the list above
]

# Store user state
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to ENTify Bot! Please enter the password to continue:")
    return PASSWORD

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "ENT2025":
        user_data[update.effective_chat.id] = {"case_index": 0, "question_index": 0}
        await update.message.reply_video(WELCOME_VIDEO_URL, caption="✅ Access granted! Starting the first case...")
        return await send_case(update, context)
    else:
        await update.message.reply_text("❌ Incorrect password. Please try again:")
        return PASSWORD

def get_current_case(chat_id):
    idx = user_data[chat_id]["case_index"]
    return CASES[idx]

def get_current_question(chat_id):
    case = get_current_case(chat_id)
    q_idx = user_data[chat_id]["question_index"]
    return case["questions"][q_idx]

async def send_case(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    case = get_current_case(chat_id)
    await context.bot.send_video(chat_id=chat_id, video=case["video"], caption=case["title"])
    return await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    question_data = get_current_question(chat_id)
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(question_data["options"])
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=question_data["question"], reply_markup=reply_markup)
    return MCQ

async def handle_mcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    selected = int(query.data)
    question = get_current_question(chat_id)

    feedback = question["feedback"][selected]
    await query.edit_message_text(
        f"Your answer:
{question['options'][selected]}

{feedback}"
    )

    # Advance question
    if user_data[chat_id]["question_index"] + 1 < len(get_current_case(chat_id)["questions"]):
        user_data[chat_id]["question_index"] += 1
        return await send_question(query, context)
    else:
        # Done with all questions
        keyboard = [[InlineKeyboardButton("➡️ Next Case", callback_data="next_case")]]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text="✅ Case completed.", reply_markup=markup)
        return MCQ

async def next_case(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_data[chat_id]["case_index"] += 1
    user_data[chat_id]["question_index"] = 0
    if user_data[chat_id]["case_index"] < len(CASES):
        return await send_case(update, context)
    else:
        await context.bot.send_message(chat_id=chat_id, text="🎉 All ENT cases completed! Thank you.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Goodbye!")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            MCQ: [
                CallbackQueryHandler(handle_mcq, pattern="^\d$"),
                CallbackQueryHandler(next_case, pattern="^next_case$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()
