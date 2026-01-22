import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# -----------------------------
# Environment Variables
# -----------------------------
API_TOKEN = os.getenv("API_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
XROCKET_API_KEY = os.getenv("XROCKET_API_KEY")
MASTER_CHANNEL_1 = os.getenv("MASTER_CHANNEL_1")
MASTER_CHANNEL_2 = os.getenv("MASTER_CHANNEL_2")
CURRENCY = "USDT"

# -----------------------------
# Bot Setup
# -----------------------------
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# -----------------------------
# Database Setup
# -----------------------------
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Users Table
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance REAL DEFAULT 0,
    referred_by INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0,
    version INTEGER DEFAULT 1
)""")
conn.commit()

# Withdraw Requests Table
cursor.execute("""CREATE TABLE IF NOT EXISTS withdraw_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    status TEXT DEFAULT 'pending'
)""")
conn.commit()

# -----------------------------
# Helper Functions
# -----------------------------
def is_joined(user_id: int):
    try:
        member1 = bot.get_chat_member(MASTER_CHANNEL_1, user_id)
        member2 = bot.get_chat_member(MASTER_CHANNEL_2, user_id)
        return member1.status != "left" and member2.status != "left"
    except:
        return False

def register_user(user_id, username, first_name, referred_by=0):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, first_name, referred_by) VALUES (?, ?, ?, ?)",
                       (user_id, username, first_name, referred_by))
        if referred_by:
            cursor.execute("UPDATE users SET referrals=referrals+1 WHERE user_id=?", (referred_by,))
        conn.commit()

# -----------------------------
# Main Menu
# -----------------------------
async def send_main_menu(uid):
    cursor.execute("SELECT version FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    version = row[0] if row else 1

    kb = InlineKeyboardMarkup(row_width=1)

    # Version-specific buttons
    if version == 1:
        kb.add(InlineKeyboardButton("👤 Profile", callback_data="profile"))
        kb.add(InlineKeyboardButton("💰 Balance", callback_data="balance"))
        kb.add(InlineKeyboardButton("🔗 Refer", callback_data="refer"))
        kb.add(InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"))
    elif version == 2:
        kb.add(InlineKeyboardButton("🔐 Captcha Verify", callback_data="captcha"))
        kb.add(InlineKeyboardButton("👤 Profile", callback_data="profile"))
        kb.add(InlineKeyboardButton("💰 Balance", callback_data="balance"))
        kb.add(InlineKeyboardButton("🔗 Refer", callback_data="refer"))
        kb.add(InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"))
    elif version == 3:
        kb.add(InlineKeyboardButton("🏆 Daily Bonus", callback_data="daily_bonus"))
        kb.add(InlineKeyboardButton("🎯 Tasks", callback_data="tasks"))
        kb.add(InlineKeyboardButton("👤 Profile", callback_data="profile"))
        kb.add(InlineKeyboardButton("💰 Balance", callback_data="balance"))
        kb.add(InlineKeyboardButton("🔗 Refer", callback_data="refer"))
        kb.add(InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"))
    elif version == 4:
        kb.add(InlineKeyboardButton("🛠 Create Bot", callback_data="create_bot"))
        kb.add(InlineKeyboardButton("⚙ Set Token & Channels", callback_data="set_bot"))
        kb.add(InlineKeyboardButton("👤 Profile", callback_data="profile"))
        kb.add(InlineKeyboardButton("💰 Balance", callback_data="balance"))
        kb.add(InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"))

    # Admin Panel for OWNER_ID
    if uid == OWNER_ID:
        kb.add(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))

    await bot.send_message(uid, "📌 Main Menu:", reply_markup=kb)

# -----------------------------
# /start Command
# -----------------------------
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    # Check master channel join
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
    
    await message.answer("Welcome! Please join our master channels first:", reply_markup=kb)
    
    # Register user in DB
    register_user(user_id, username, first_name)

# -----------------------------
# Button Callbacks
# -----------------------------
@dp.callback_query_handler(lambda c: c.data == "check_join")
async def check_join_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    try:
        member1 = await bot.get_chat_member(MASTER_CHANNEL_1, uid)
        member2 = await bot.get_chat_member(MASTER_CHANNEL_2, uid)
        if member1.status == "left" or member2.status == "left":
            await c.answer("You must join both channels first!", show_alert=True)
            return
    except:
        await c.answer("Error checking channels.", show_alert=True)
        return
    await c.message.delete()
    await send_main_menu(uid)

# -----------------------------
# Profile & Refer
# -----------------------------
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    cursor.execute("SELECT balance, referrals, version FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    if row:
        balance, referrals, version = row
        await c.message.answer(f"👤 Profile\nBalance: {balance} {CURRENCY}\nReferrals: {referrals}\nVersion: {version}")
    else:
        await c.message.answer("Profile not found.")

@dp.callback_query_handler(lambda c: c.data == "refer")
async def refer_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    refer_link = f"https://t.me/{(await bot.get_me()).username}?start={uid}"
    await c.message.answer(f"🔗 Your referral link:\n{refer_link}\nShare and earn!")

# -----------------------------
# Admin Panel
# -----------------------------
@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    if uid != OWNER_ID:
        await c.answer("You are not the admin!", show_alert=True)
        return
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📊 Stats", callback_data="admin_stats"))
    kb.add(InlineKeyboardButton("💰 Withdraw Requests", callback_data="admin_withdraw"))
    kb.add(InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"))
    kb.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu"))
    await c.message.edit_text("⚙️ Admin Panel:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats_cb(c: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    await c.message.answer(f"📊 Total Users: {total_users}\n💰 Total Balance: {total_balance} {CURRENCY}")

@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def main_menu_cb(c: types.CallbackQuery):
    await c.message.delete()
    await send_main_menu(c.from_user.id)

# -----------------------------
# Reseller Bot Structure (Version 4)
# -----------------------------
@dp.callback_query_handler(lambda c: c.data == "create_bot")
async def create_bot_cb(c: types.CallbackQuery):
    await c.message.answer("🛠 Please provide your BotFather token and channels for your new bot. Version will be applied automatically.")

@dp.callback_query_handler(lambda c: c.data == "set_bot")
async def set_bot_cb(c: types.CallbackQuery):
    await c.message.answer("⚙️ Setup your bot: Send API token + Master Channels + Language + Version.")

# -----------------------------
# Run Bot
# -----------------------------
if __name__ == "__main__":
    print("Bot Started")
    executor.start_polling(dp, skip_updates=True)
