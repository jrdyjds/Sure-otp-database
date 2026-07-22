# database_bot.py
import os
import json
import sys
from datetime import datetime

# ==================== TRY-EXCEPT FOR TELEGRAM IMPORT ====================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("📦 Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

# ==================== CONFIG ====================
DB_BOT_TOKEN = os.environ.get("DB_BOT_TOKEN", "8748919559:AAEHUeR390Y8RuBMqFpx4BVkKy2pGQvPHCw")
ADMIN_IDS = [2102179662]

# ==================== DATA FILES ====================
DATA_FILES = [
    "users.json",
    "paid_sms.json",
    "user_stats.json",
    "referral_data.json",
    "banned_users.json",
    "withdraw_requests.json",
    "activity_logs.json",
    "datarange.json",
    "custom_services.json",
    "admins.json",
    "otp_groups.json",
    "user_last_data.json"
]

DATA_DIR = "storage_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== DATA FUNCTIONS ====================

def load_data(file_name):
    """ফাইল থেকে ডেটা লোড করে"""
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        return {} if file_name != "banned_users.json" else []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {} if file_name != "banned_users.json" else []

def save_data(file_name, data):
    """ফাইলে ডেটা সেভ করে"""
    file_path = os.path.join(DATA_DIR, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return True

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("🔒 This bot is private. Only admins can access.")
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 List Files", callback_data="list_files")],
        [InlineKeyboardButton("📦 Backup All", callback_data="backup_all")],
        [InlineKeyboardButton("📊 Storage Stats", callback_data="storage_stats")]
    ])
    
    await update.message.reply_text(
        "💾 <b>Database Storage Bot</b>\n\n"
        "This bot stores all JSON data for the main OTP bot.\n"
        "Use the buttons below to manage your data.\n\n"
        "<code>/list</code> - Show all files\n"
        "<code>/get users.json</code> - Get a file\n"
        "<code>/set users.json {...}</code> - Update a file",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব ফাইলের লিস্ট দেখায়"""
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    files_info = []
    total_size = 0
    for file_name in DATA_FILES:
        file_path = os.path.join(DATA_DIR, file_name)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            total_size += size
            files_info.append(f"• {file_name}: {size:,} bytes")
        else:
            files_info.append(f"• {file_name}: ❌ Not found")
    
    text = (
        f"📂 <b>Data Files</b>\n\n"
        f"Total: {len(DATA_FILES)} files\n"
        f"Total size: {total_size:,} bytes ({total_size/1024:.1f} KB)\n\n"
        + "\n".join(files_info)
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """একটি ফাইল দেখায়"""
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    parts = update.message.text.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text("❌ Format: /get users.json")
        return
    
    file_name = parts[1].strip()
    if file_name not in DATA_FILES:
        await update.message.reply_text(f"❌ Invalid file: {file_name}")
        return
    
    data = load_data(file_name)
    
    import sys
    size = sys.getsizeof(json.dumps(data))
    if size > 4000:
        file_path = os.path.join(DATA_DIR, file_name)
        with open(file_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=file_name,
                caption=f"📄 {file_name}\nSize: {size} bytes"
            )
    else:
        await update.message.reply_text(
            f"📄 {file_name}\n\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)[:3500]}\n```",
            parse_mode="Markdown"
        )

async def set_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """একটি ফাইল আপডেট করে"""
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    parts = update.message.text.split(" ", 2)
    if len(parts) < 3:
        await update.message.reply_text("❌ Format: /set users.json {\"key\": \"value\"}")
        return
    
    file_name = parts[1].strip()
    if file_name not in DATA_FILES:
        await update.message.reply_text(f"❌ Invalid file: {file_name}")
        return
    
    try:
        data = json.loads(parts[2])
        save_data(file_name, data)
        await update.message.reply_text(f"✅ Data saved to {file_name}")
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Invalid JSON format!")

async def backup_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব ডেটার ব্যাকআপ তৈরি করে"""
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    await update.message.reply_text("⏳ Creating backup...")
    
    all_data = {}
    for file_name in DATA_FILES:
        all_data[file_name] = load_data(file_name)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.json"
    file_path = os.path.join(DATA_DIR, backup_file)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    with open(file_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=backup_file,
            caption=f"📦 Backup - {timestamp}\nTotal: {len(DATA_FILES)} files"
        )

async def storage_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্টোরেজ স্ট্যাটস দেখায়"""
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    total_size = 0
    file_stats = []
    for file_name in DATA_FILES:
        file_path = os.path.join(DATA_DIR, file_name)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            total_size += size
            file_stats.append(f"• {file_name}: {size:,} bytes")
        else:
            file_stats.append(f"• {file_name}: ❌ Not found")
    
    text = (
        f"📊 <b>Storage Stats</b>\n\n"
        f"Total files: {len(DATA_FILES)}\n"
        f"Total size: {total_size:,} bytes ({total_size/1024:.1f} KB)\n\n"
        + "\n".join(file_stats)
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বাটন কলব্যাক"""
    query = update.callback_query
    uid = query.from_user.id
    
    if uid not in ADMIN_IDS:
        await query.answer("Unauthorized!", show_alert=True)
        return
    
    await query.answer()
    data = query.data
    
    if data == "list_files":
        await list_files(update, context)
    elif data == "backup_all":
        await backup_all(update, context)
    elif data == "storage_stats":
        await storage_stats(update, context)

# ==================== MAIN ====================

def main():
    try:
        app = ApplicationBuilder().token(DB_BOT_TOKEN).build()
        
        # Command Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("list", list_files))
        app.add_handler(CommandHandler("get", get_file))
        app.add_handler(CommandHandler("set", set_file))
        app.add_handler(CommandHandler("backup", backup_all))
        
        # Callback Handler
        app.add_handler(CallbackQueryHandler(button_callback))
        
        print("💾 Database Storage Bot is running...")
        print(f"📂 Data directory: {DATA_DIR}")
        print(f"📄 Total files: {len(DATA_FILES)}")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("📦 Please check: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
