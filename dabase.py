# database_bot.py
import os
import json
import asyncio
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ==================== CONFIG ====================
DB_BOT_TOKEN = "8748919559:AAEHUeR390Y8RuBMqFpx4BVkKy2pGQvPHCw"
ADMIN_IDS = [2102179662]
API_PORT = 8000
API_HOST = "0.0.0.0"

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

def get_default_data(file_name):
    """প্রতিটি ফাইলের ডিফল্ট ডেটা"""
    if file_name in ["banned_users.json", "custom_services.json"]:
        return []
    elif file_name == "admins.json":
        return ADMIN_IDS
    elif file_name == "otp_groups.json":
        return [-1004374381669]
    else:
        return {}

def load_data(file_name):
    """ফাইল থেকে ডেটা লোড করে (না থাকলে তৈরি করে)"""
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        default_data = get_default_data(file_name)
        save_data(file_name, default_data)
        return default_data
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        default_data = get_default_data(file_name)
        save_data(file_name, default_data)
        return default_data

def save_data(file_name, data):
    """ফাইলে ডেটা সেভ করে"""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, file_name)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Save error {file_name}: {e}")
        return False

def get_file_size(file_name):
    file_path = os.path.join(DATA_DIR, file_name)
    return os.path.getsize(file_path) if os.path.exists(file_path) else 0

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"

# ==================== FASTAPI APP ====================

app = FastAPI(title="Database Bot API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """হেলথ চেক"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/files")
async def list_files():
    """সব ফাইলের লিস্ট"""
    files_info = []
    total_size = 0
    for file_name in DATA_FILES:
        size = get_file_size(file_name)
        total_size += size
        files_info.append({
            "name": file_name,
            "size": size,
            "size_formatted": format_size(size),
            "exists": os.path.exists(os.path.join(DATA_DIR, file_name))
        })
    return {
        "total_files": len(DATA_FILES),
        "total_size": total_size,
        "total_size_formatted": format_size(total_size),
        "files": files_info
    }

@app.get("/data/{file_name}")
async def get_data(file_name: str):
    """একটি ফাইলের ডেটা রিটার্ন করে"""
    if file_name not in DATA_FILES:
        raise HTTPException(status_code=404, detail="File not found")
    data = load_data(file_name)
    return {"file_name": file_name, "data": data, "size": get_file_size(file_name)}

@app.post("/data/{file_name}")
async def set_data(file_name: str, payload: dict):
    """একটি ফাইলে ডেটা সেভ করে"""
    if file_name not in DATA_FILES:
        raise HTTPException(status_code=404, detail="File not found")
    data = payload.get("data")
    if data is None:
        raise HTTPException(status_code=400, detail="Missing 'data' field")
    save_data(file_name, data)
    return {"status": "success", "file_name": file_name}

@app.post("/data/{file_name}/update")
async def update_data(file_name: str, payload: dict):
    """একটি ফাইলের ডেটা আপডেট করে (মার্জ)"""
    if file_name not in DATA_FILES:
        raise HTTPException(status_code=404, detail="File not found")
    new_data = payload.get("data")
    if new_data is None:
        raise HTTPException(status_code=400, detail="Missing 'data' field")
    current_data = load_data(file_name)
    if isinstance(current_data, dict) and isinstance(new_data, dict):
        current_data.update(new_data)
    else:
        current_data = new_data
    save_data(file_name, current_data)
    return {"status": "success", "file_name": file_name}

@app.delete("/data/{file_name}")
async def delete_file(file_name: str):
    """একটি ফাইল ডিলিট করে"""
    if file_name not in DATA_FILES:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = os.path.join(DATA_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "success", "message": f"Deleted {file_name}"}
    return {"status": "error", "message": "File not found"}

@app.post("/backup")
async def create_backup():
    """সব ডেটার ব্যাকআপ তৈরি করে"""
    all_data = {}
    for file_name in DATA_FILES:
        all_data[file_name] = load_data(file_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.json"
    file_path = os.path.join(DATA_DIR, backup_file)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    return {"status": "success", "backup_file": backup_file, "file_count": len(DATA_FILES)}

# ==================== TELEGRAM BOT KEYBOARDS ====================

def main_keyboard():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 List Files", callback_data="list_files")],
        [InlineKeyboardButton("📊 Storage Stats", callback_data="storage_stats")],
        [InlineKeyboardButton("📦 Backup All", callback_data="backup_all")],
        [InlineKeyboardButton("🔄 Restore Backup", callback_data="restore_backup")],
        [InlineKeyboardButton("📝 Edit File", callback_data="edit_file")],
        [InlineKeyboardButton("🌐 API Status", callback_data="api_status")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    return keyboard

def file_list_keyboard(page=0):
    buttons = []
    per_page = 6
    start = page * per_page
    end = start + per_page
    files = DATA_FILES[start:end]
    
    for file_name in files:
        size = get_file_size(file_name)
        status = "✅" if size > 0 else "📄"
        buttons.append([InlineKeyboardButton(
            f"{status} {file_name} ({format_size(size)})",
            callback_data=f"view_file_{file_name}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"list_page_{page-1}"))
    if end < len(DATA_FILES):
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"list_page_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)

def edit_file_keyboard(file_name):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 View Content", callback_data=f"view_content_{file_name}")],
        [InlineKeyboardButton("📥 Download", callback_data=f"download_file_{file_name}")],
        [InlineKeyboardButton("📤 Upload New", callback_data=f"upload_file_{file_name}")],
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_file_{file_name}")],
        [InlineKeyboardButton("🔙 Back", callback_data="edit_file")]
    ])
    return keyboard

# ==================== TELEGRAM BOT HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("🔒 Private bot! Only admins can access.")
        return
    
    await update.message.reply_text(
        f"💾 <b>📦 DATABASE STORAGE BOT</b> 📦\n\n"
        f"✅ <b>Status:</b> 🟢 Online\n"
        f"📂 <b>Total Files:</b> {len(DATA_FILES)}\n"
        f"💾 <b>Storage Used:</b> {format_size(sum(get_file_size(f) for f in DATA_FILES))}\n"
        f"🌐 <b>API:</b> http://{API_HOST}:{API_PORT}\n\n"
        "🔹 <i>Use the buttons below to manage your data</i>\n"
        "🔹 <i>Main bot can access data via HTTP API</i>",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    page = context.user_data.get("list_page", 0)
    
    if query:
        await query.answer()
        await query.message.edit_text(
            f"📂 <b>DATA FILES</b>\n\nPage {page + 1} of {((len(DATA_FILES)-1)//6)+1}\nSelect a file:",
            parse_mode="HTML",
            reply_markup=file_list_keyboard(page)
        )
    else:
        await update.message.reply_text(
            "📂 <b>DATA FILES</b>\n\nSelect a file:",
            parse_mode="HTML",
            reply_markup=file_list_keyboard(0)
        )

async def view_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_name = query.data.replace("view_file_", "")
    data = load_data(file_name)
    
    text = f"📄 <b>{file_name}</b>\n📏 Size: {format_size(get_file_size(file_name))}\n📊 Items: {len(data) if isinstance(data, (dict, list)) else 0}\n\n"
    
    if isinstance(data, dict):
        items = list(data.items())[:10]
        for key, value in items:
            text += f"🔑 <code>{key}</code>: {str(value)[:50]}\n"
        if len(data) > 10:
            text += f"\n... and {len(data)-10} more items"
    elif isinstance(data, list):
        items = data[:10]
        for item in items:
            text += f"• {str(item)[:50]}\n"
        if len(data) > 10:
            text += f"\n... and {len(data)-10} more items"
    else:
        text += str(data)[:200]
    
    if len(text) > 3500:
        text = text[:3500] + "...\n\n⚠️ File too large, download to view full content"
    
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=edit_file_keyboard(file_name))

async def view_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_name = query.data.replace("view_content_", "")
    file_path = os.path.join(DATA_DIR, file_name)
    
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            await query.message.reply_document(
                document=f, filename=file_name,
                caption=f"📄 {file_name}\n📏 Size: {format_size(get_file_size(file_name))}"
            )
    else:
        await query.message.edit_text(f"❌ File not found: {file_name}", reply_markup=edit_file_keyboard(file_name))

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_name = query.data.replace("download_file_", "")
    file_path = os.path.join(DATA_DIR, file_name)
    
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            await query.message.reply_document(document=f, filename=file_name, caption=f"📥 Downloaded: {file_name}")
    else:
        await query.message.edit_text(f"❌ File not found: {file_name}", reply_markup=edit_file_keyboard(file_name))

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_name = query.data.replace("upload_file_", "")
    context.user_data["upload_target"] = file_name
    
    await query.message.edit_text(
        f"📤 <b>Upload {file_name}</b>\n\nPlease send the JSON file as a document.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="edit_file")]])
    )

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_name = query.data.replace("delete_file_", "")
    file_path = os.path.join(DATA_DIR, file_name)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        await query.message.edit_text(f"🗑️ <b>{file_name}</b> deleted!", parse_mode="HTML", reply_markup=file_list_keyboard(0))
    else:
        await query.message.edit_text(f"❌ File not found: {file_name}", reply_markup=edit_file_keyboard(file_name))

async def backup_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    if query:
        await query.answer()
        msg = await query.message.edit_text("⏳ Creating backup...")
    else:
        msg = await update.message.reply_text("⏳ Creating backup...")
    
    all_data = {}
    for file_name in DATA_FILES:
        all_data[file_name] = load_data(file_name)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.json"
    file_path = os.path.join(DATA_DIR, backup_file)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    with open(file_path, "rb") as f:
        await msg.edit_text("📦 Backup created! Sending...")
        await update.effective_user.send_document(
            document=f, filename=backup_file,
            caption=f"📦 <b>Full Backup</b>\n📅 {timestamp}\n📂 {len(DATA_FILES)} files",
            parse_mode="HTML"
        )
        await msg.delete()

async def restore_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    if query:
        await query.answer()
        await query.message.edit_text(
            "📥 <b>RESTORE BACKUP</b>\n\nPlease send the backup JSON file.\n⚠️ <i>This will overwrite ALL current data!</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="back_to_main")]])
        )
        context.user_data["restore_mode"] = True
    else:
        await update.message.reply_text(
            "📥 Please send the backup JSON file.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="back_to_main")]])
        )
        context.user_data["restore_mode"] = True

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    document = update.message.document
    if not document or not document.file_name.endswith(".json"):
        await update.message.reply_text("❌ Please send a valid JSON file!")
        return
    
    if context.user_data.get("restore_mode"):
        await update.message.reply_text("⏳ Restoring backup...")
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        try:
            all_data = json.loads(file_bytes.decode())
            restored = 0
            for file_name, data in all_data.items():
                if file_name in DATA_FILES:
                    save_data(file_name, data)
                    restored += 1
            await update.message.reply_text(
                f"✅ <b>Restore Complete!</b>\n📂 Restored: {restored} files\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="HTML", reply_markup=main_keyboard()
            )
            context.user_data["restore_mode"] = False
        except Exception as e:
            await update.message.reply_text(f"❌ Restore failed: {str(e)}")
            context.user_data["restore_mode"] = False
        return
    
    if context.user_data.get("upload_target"):
        file_name = context.user_data["upload_target"]
        await update.message.reply_text(f"⏳ Uploading {file_name}...")
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        try:
            data = json.loads(file_bytes.decode())
            save_data(file_name, data)
            await update.message.reply_text(
                f"✅ <b>{file_name}</b> uploaded successfully!",
                parse_mode="HTML", reply_markup=edit_file_keyboard(file_name)
            )
            context.user_data["upload_target"] = None
        except Exception as e:
            await update.message.reply_text(f"❌ Upload failed: {str(e)}")
        return

async def storage_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    if query:
        await query.answer()
    
    total_size = 0
    file_stats = []
    for file_name in DATA_FILES:
        size = get_file_size(file_name)
        total_size += size
        status = "✅" if size > 0 else "📄"
        file_stats.append(f"{status} {file_name}: {format_size(size)}")
    
    text = f"📊 <b>STORAGE STATISTICS</b>\n\n📂 Total Files: {len(DATA_FILES)}\n💾 Total Size: {format_size(total_size)}\n\n" + "\n".join(file_stats)
    
    if query:
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]))

async def edit_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    if query:
        await query.answer()
        await query.message.edit_text("📝 <b>EDIT FILE</b>\n\nSelect a file:", parse_mode="HTML", reply_markup=file_list_keyboard(0))
    else:
        await update.message.reply_text("📝 <b>EDIT FILE</b>\n\nSelect a file:", parse_mode="HTML", reply_markup=file_list_keyboard(0))

async def api_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        f"🌐 <b>API STATUS</b>\n\n"
        f"📍 Host: {API_HOST}\n"
        f"🔢 Port: {API_PORT}\n"
        f"🟢 Status: Running\n\n"
        f"<b>Endpoints:</b>\n"
        f"<code>GET  /data/{{file}}</code>\n"
        f"<code>POST /data/{{file}}</code>\n"
        f"<code>POST /data/{{file}}/update</code>\n"
        f"<code>DELETE /data/{{file}}</code>\n"
        f"<code>POST /backup</code>\n"
        f"<code>GET  /files</code>\n"
        f"<code>GET  /health</code>"
    )
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]))

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data.clear()
        await query.message.edit_text("❌ Cancelled!", reply_markup=main_keyboard())
    else:
        await update.message.reply_text("❌ Cancelled!", reply_markup=main_keyboard())

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.edit_text(
            f"💾 <b>📦 DATABASE STORAGE BOT</b> 📦\n\n"
            f"✅ <b>Status:</b> 🟢 Online\n"
            f"📂 <b>Total Files:</b> {len(DATA_FILES)}\n"
            f"💾 <b>Storage Used:</b> {format_size(sum(get_file_size(f) for f in DATA_FILES))}\n"
            f"🌐 <b>API:</b> http://{API_HOST}:{API_PORT}\n\n"
            "🔹 <i>Use the buttons below</i>",
            parse_mode="HTML", reply_markup=main_keyboard()
        )
    else:
        await start(update, context)

# ==================== API MESSAGE HANDLER ====================

async def handle_api_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """মেইন বট থেকে আসা API মেসেজ হ্যান্ডেল করে (Telegram API বাদ)"""
    # এই ফাংশনটি আর ব্যবহার করব না, কারণ HTTP API ব্যবহার করব
    pass

# ==================== RUN BOTH SERVICES ====================

def run_telegram_bot():
    """টেলিগ্রাম বট চালায়"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tg_app = ApplicationBuilder().token(DB_BOT_TOKEN).build()
    
    # কমান্ড হ্যান্ডলার
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("list", list_files))
    tg_app.add_handler(CommandHandler("stats", storage_stats))
    tg_app.add_handler(CommandHandler("backup", backup_all))
    tg_app.add_handler(CommandHandler("restore", restore_backup))
    tg_app.add_handler(CommandHandler("edit", edit_file))
    tg_app.add_handler(CommandHandler("cancel", cancel))
    
    # কলব্যাক হ্যান্ডলার
    tg_app.add_handler(CallbackQueryHandler(list_files, pattern="^list_files$"))
    tg_app.add_handler(CallbackQueryHandler(view_file, pattern="^view_file_"))
    tg_app.add_handler(CallbackQueryHandler(view_content, pattern="^view_content_"))
    tg_app.add_handler(CallbackQueryHandler(download_file, pattern="^download_file_"))
    tg_app.add_handler(CallbackQueryHandler(upload_file, pattern="^upload_file_"))
    tg_app.add_handler(CallbackQueryHandler(delete_file, pattern="^delete_file_"))
    tg_app.add_handler(CallbackQueryHandler(backup_all, pattern="^backup_all$"))
    tg_app.add_handler(CallbackQueryHandler(restore_backup, pattern="^restore_backup$"))
    tg_app.add_handler(CallbackQueryHandler(edit_file, pattern="^edit_file$"))
    tg_app.add_handler(CallbackQueryHandler(storage_stats, pattern="^storage_stats$"))
    tg_app.add_handler(CallbackQueryHandler(api_status, pattern="^api_status$"))
    tg_app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    tg_app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    
    # ডকুমেন্ট হ্যান্ডলার
    tg_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("🤖 Telegram Bot is running...")
    tg_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def run_api():
    """FastAPI সার্ভার চালায়"""
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="warning")

def main():
    print("🚀 STARTING DATABASE BOT...")
    print(f"📂 Data directory: {DATA_DIR}")
    print(f"🌐 API Server: http://{API_HOST}:{API_PORT}")
    print("🤖 Telegram Bot: @Sure_database_bot")
    
    # API সার্ভার আলাদা থ্রেডে চালান
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # টেলিগ্রাম বট মেইন থ্রেডে চালান
    run_telegram_bot()

if __name__ == "__main__":
    main()
