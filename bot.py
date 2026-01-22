import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import sqlite3
from aiorocket2 import xRocketClient
import os

# ===========================
# CONFIGURATION
# ===========================
API_TOKEN = os.getenv("8508138633:AAE6NRVSAXXrkzFCA8DLRJb389xroV2HqCA")  # Bot Token from Render Env Variables
OWNER_ID = int(os.getenv("5988572342", "0"))
MASTER_CHANNELS = ["@NOBAB_MASTER_BOT_CHANNEL", "@cryptomininginformer"]
XROCKET_API_KEY = os.getenv("XROCKET_API_KEY")  # Optional for auto withdraw
CURRENCY = "USDT"

# ===========================
# DATABASE SETUP
# ===========================
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance REAL DEFAULT 0,
    referred_by INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdraw_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    status TEXT DEFAULT 'pending',
    invoice_id TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

# Default settings
def init_settings():
    defaults = {
        "min_withdraw": "50",
        "max_withdraw": "1000",
        "withdraw_tax": "5",
        "per_refer_bonus": "10"
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
init_settings()

# ===========================
# BOT + XRocket CLIENT INIT
# ===========================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

if XROCKET_API_KEY:
    xrocket_client = xRocketClient(api_key=XROCKET_API_KEY)
else:
    xrocket_client = None

# ===========================
# UTIL FUNCTIONS
# ===========================
async def check_master_channels(user_id):
    for ch in MASTER_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

async def send_main_menu(uid):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("👤 Profile", callback_data="profile"))
    kb.add(InlineKeyboardButton("💰 Balance", callback_data="balance"))
    kb.add(InlineKeyboardButton("🔗 Refer", callback_data="refer"))
    kb.add(InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"))
    if uid == OWNER_ID:
        kb.add(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    await bot.send_message(uid, "📌 Main Menu:", reply_markup=kb)

# ===========================
# START COMMAND
# ===========================
@dp.message_handler(commands=["start"])
async def start_cmd(msg: types.Message):
    user = msg.from_user
    args = msg.get_args()
    referred_by = 0
    if args.isdigit():
        referred_by = int(args)

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, referred_by) VALUES (?, ?, ?, ?)",
        (user.id, user.username or "", user.first_name or "", referred_by)
    )

    if referred_by and referred_by != user.id:
        cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (referred_by,))
        bonus = float(cursor.execute("SELECT value FROM settings WHERE key='per_refer_bonus'").fetchone()[0])
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (bonus, referred_by))
    conn.commit()

    joined = await check_master_channels(user.id)
    if not joined:
        kb = InlineKeyboardMarkup(row_width=1)
        for ch in MASTER_CHANNELS:
            kb.add(InlineKeyboardButton(text=f"Join {ch}", url=f"https://t.me/{ch.replace('@','')}"))
        kb.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
        await msg.answer("Please join required channels:", reply_markup=kb)
        return

    await send_main_menu(user.id)

# ===========================
# CALLBACK HANDLER
# ===========================
@dp.callback_query_handler(lambda c: True)
async def cb_handler(c: types.CallbackQuery):
    user_id = c.from_user.id
    data = c.data

    if data == "check_join":
        ok = await check_master_channels(user_id)
        if not ok:
            await c.answer("Still not joined.", show_alert=True)
            return
        await c.message.delete()
        await send_main_menu(user_id)

    # Admin Panel skeleton
    if data == "admin_panel" and user_id == OWNER_ID:
        await bot.send_message(user_id, "⚙️ Admin Panel is coming soon...")

# ===========================
# RUN BOT
# ===========================
if __name__ == "__main__":
    print("Bot Started")
    executor.start_polling(dp, skip_updates=True)