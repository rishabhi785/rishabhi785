from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import logging
import requests

# Bot config
BOT_TOKEN = "8056660251:AAEdC57lu0_Jd52nCBbLAhVWVF7XketqrGY"
CHANNEL_USERNAME = "@rishabhearningtip"
YOUTUBE_LINK = "https://youtube.com/@rishabhearningtipss?si=4asSZyYDXpjTRTsh"
GROUP_CHAT_ID = -1002216818642
MIN_WITHDRAW = 15
MIN_REDEEM = 10
REFERRAL_BONUS = 3

# In-memory storage
users_data = {}
claimed_users = set()
awaiting_upi = set()
awaiting_withdraw = set()
awaiting_redeem = set()

# Logging
logging.basicConfig(level=logging.INFO)

# Reply Keyboard
reply_keyboard = ReplyKeyboardMarkup(
    [
        ["Balance", "Refer Link"],
        ["Add UPI", "Withdraw"],
        ["Redeem Code"]
    ],
    resize_keyboard=True
)

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    user = update.effective_user
    user_id = str(user.id)
    args = context.args
    if user_id not in users_data:
        users_data[user_id] = {"balance": 1, "referrals": 0, "upi": None}
        if args:
            ref_id = args[0]
            if ref_id != user_id and ref_id in users_data:
                ref_user = users_data[ref_id]
                ref_user["balance"] += REFERRAL_BONUS
                ref_user["referrals"] += 1
        keyboard = [
            [
                InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"),
                InlineKeyboardButton("Join YouTube", url=YOUTUBE_LINK)
            ],
            [InlineKeyboardButton("Claim Bonus", callback_data="claim_bonus")]
        ]
        await update.message.reply_text(
            "Join all channels below and then click *Claim Bonus* to receive your reward 🎉🎁:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("You already received your bonus.", reply_markup=reply_keyboard)

# Bonus Claim
async def claim_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    if user_id not in claimed_users:
        claimed_users.add(user_id)
        await query.message.reply_text("Note: Please join all channels to get your bonus.")
    else:
        await query.message.reply_text("Bonus Claimed! Start using menu below.", reply_markup=reply_keyboard)

# Reply keyboard actions
async def handle_reply_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text.strip()

    if user_id in awaiting_upi:
        if "@" in text and len(text) >= 5:
            users_data[user_id]["upi"] = text
            awaiting_upi.remove(user_id)
            await update.message.reply_text(f"Your UPI ID `{text}` has been saved!", parse_mode="Markdown", reply_markup=reply_keyboard)
        else:
            await update.message.reply_text("Invalid UPI ID format. Please send again.", reply_markup=reply_keyboard)
        return

    if user_id in awaiting_withdraw:
        try:
            amount = int(text)
            data = users_data[user_id]
            if amount > data["balance"]:
                await update.message.reply_text(f"You cannot withdraw more than your balance (₹{data['balance']})", reply_markup=reply_keyboard)
            elif amount < MIN_WITHDRAW:
                await update.message.reply_text(f"Minimum withdraw amount is ₹{MIN_WITHDRAW}", reply_markup=reply_keyboard)
            else:
                data["balance"] -= amount
                upi = data["upi"]

                # Call VSV Payment API
                try:
                    response = requests.get(f"https://vsv-gateway-solutions.co.in/Api/upi.php?token=JWLFKCJT&upi_id={upi}&amount={amount}&comment=CashLootWithdraw")
                    api_response = response.text
                except Exception as e:
                    api_response = f"API Error: {e}"

                await update.message.reply_text(
                    f"₹{amount} withdrawal processed to your UPI ID: `{upi}`\n\nAPI Response: {api_response}\nCurrent Balance: ₹{data['balance']}",
                    parse_mode="Markdown",
                    reply_markup=reply_keyboard
                )
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=f"₹{amount} withdrawal to `{upi}` from [{user.first_name}](tg://user?id={user.id})\nAPI response: {api_response}",
                    parse_mode="Markdown"
                )
        except:
            await update.message.reply_text("Please enter a valid amount.", reply_markup=reply_keyboard)
        awaiting_withdraw.remove(user_id)
        return

    if user_id in awaiting_redeem:
        try:
            amount = int(text)
            data = users_data[user_id]
            if amount > data["balance"]:
                await update.message.reply_text(f"You cannot redeem more than your balance (₹{data['balance']})", reply_markup=reply_keyboard)
            elif amount < MIN_REDEEM:
                await update.message.reply_text(f"Minimum redeem amount is ₹{MIN_REDEEM}.", reply_markup=reply_keyboard)
            else:
                data["balance"] -= amount
                await update.message.reply_text(
                    f"Your redeem code for ₹{amount} has been successfully sent to your chat!",
                    parse_mode="Markdown",
                    reply_markup=reply_keyboard
                )
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=f"₹{amount} redeemed by [{user.first_name}](tg://user?id={user.id}) as redeem code.",
                    parse_mode="Markdown"
                )
        except:
            await update.message.reply_text("Please enter a valid amount.", reply_markup=reply_keyboard)
        awaiting_redeem.remove(user_id)
        return

    # Menu options
    if text == "Balance":
        data = users_data.get(user_id, {"balance": 0, "referrals": 0})
        await update.message.reply_text(f"Balance: ₹{data['balance']}\nReferrals: {data['referrals']}")
    elif text == "Refer Link":
        await update.message.reply_text(
            f"🤑 Per Refer ₹{REFERRAL_BONUS}\n"
            f"✅ Minimum Withdraw ₹{MIN_WITHDRAW}\n"
            f"🔗 Referral Link:\n"
            f"https://t.me/cashLoootupii_bot?start={user_id}",
            reply_markup=reply_keyboard
        )
    elif text == "Add UPI":
        awaiting_upi.add(user_id)
        await update.message.reply_text("Send your UPI ID now (e.g. name@bank).")
    elif text == "Withdraw":
        data = users_data.get(user_id)
        if not data or data["upi"] is None:
            await update.message.reply_text("Please add your UPI ID first using 'Add UPI' option.", reply_markup=reply_keyboard)
            return
        if data["balance"] < MIN_WITHDRAW:
            await update.message.reply_text(f"Minimum withdraw amount is ₹{MIN_WITHDRAW}. Earn more by referring.", reply_markup=reply_keyboard)
            return
        awaiting_withdraw.add(user_id)
        await update.message.reply_text("Enter the amount you want to withdraw (in ₹):")
    elif text == "Redeem Code":
        data = users_data.get(user_id)
        if not data or data["balance"] < MIN_REDEEM:
            await update.message.reply_text("You need at least ₹10 balance to redeem.", reply_markup=reply_keyboard)
            return
        awaiting_redeem.add(user_id)
        await update.message.reply_text("Please enter the amount you want to redeem (in ₹):")
    else:
        await update.message.reply_text("Please choose a valid option from the keyboard.", reply_markup=reply_keyboard)

# Run Bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(claim_bonus, pattern="claim_bonus"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons))

print("Bot running...")
app.run_polling()
