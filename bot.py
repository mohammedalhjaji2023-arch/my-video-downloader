import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# --- الإعدادات ---
TOKEN = "8794596123:AAGFD2hNbtmc-3jmMsRN_tD9JF8R1CFtVws"
CHANNEL_ID = "@lio8l1"
CHANNEL_LINK = "https://t.me/lio8l1"

# ذاكرة مؤقتة للروابط
user_links = {}

# --- دالة التحقق من الاشتراك ---
async def is_subscribed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# --- الأوامر الأساسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    text = (
        f"👋 أهلاً بك يا {user_name} في بوت التحميل العالمي!\n\n"
        "🎬 **ماذا يمكنني أن أفعل؟**\n"
        "أقوم بتحميل الفيديوهات من يوتيوب، تيك توك، إنستغرام، فيسبوك، وتويتر بأعلى جودة ممكنة.\n\n"
        f"📢 **شرط التشغيل:**\n"
        f"يجب أن تكون مشتركاً في قناتنا أولاً: {CHANNEL_ID}"
    )
    
    if await is_subscribed(update, context):
        await update.message.reply_text(text + "\n\n✅ أنت مشترك بالفعل، أرسل الرابط الآن!")
    else:
        keyboard = [[InlineKeyboardButton("إضغط هنا للاشتراك في القناة ✅", url=CHANNEL_LINK)],
                    [InlineKeyboardButton("تم الاشتراك، تفعيل البوت 🔄", callback_data="check_sub")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 **طريقة الاستخدام:**\n"
        "1️⃣ قم بنسخ رابط الفيديو (مثلاً من تيك توك أو يوتيوب).\n"
        "2️⃣ أرسل الرابط هنا في البوت.\n"
        "3️⃣ اختر الصيغة المطلوبة (فيديو أو صوت MP3).\n\n"
        "⚠️ إذا واجهت مشكلة، تأكد أن الفيديو ليس خاصاً (Private)."
    )
    await update.message.reply_text(help_text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "🌐 **المنصات المدعومة:**\n"
        "- يوتيوب (بما في ذلك Shorts)\n"
        "- تيك توك (بدون علامة مائية)\n"
        "- إنستغرام (Reels & Stories)\n"
        "- فيسبوك وتويتر (X)\n\n"
        f"👤 مبرمج البوت: {CHANNEL_ID}"
    )
    await update.message.reply_text(about_text)

# --- معالجة الروابط ---
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await start(update, context)
        return

    url = update.message.text
    if "http" not in url:
        return await update.message.reply_text("❌ عذراً، هذا ليس رابطاً صحيحاً.")

    user_id = update.effective_user.id
    user_links[user_id] = url # تخزين الرابط لتجنب خطأ التلجرام للبيانات الطويلة

    keyboard = [
        [InlineKeyboardButton("🎬 فيديو MP4 (جودة عالية)", callback_data="dl_high")],
        [InlineKeyboardButton("🎬 فيديو MP4 (جودة متوسطة)", callback_data="dl_low")],
        [InlineKeyboardButton("🎵 ملف صوتي MP3", callback_data="dl_mp3")]
    ]
    await update.message.reply_text("📥 تم استلام الرابط! اختر الصيغة التي تريدها:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- معالجة الأزرار والتحميل ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    if query.data == "check_sub":
        if await is_subscribed(update, context):
            await query.edit_message_text("✅ تم تفعيل البوت بنجاح! أرسل رابط الفيديو الآن.")
        else:
            await query.answer("⚠️ أنت غير مشترك في القناة بعد!", show_alert=True)
        return

    url = user_links.get(user_id)
    if not url:
        return await query.edit_message_text("❌ انتهت الجلسة، أرسل الرابط مرة أخرى.")

    await query.edit_message_text("⏳ جاري التحميل والمعالجة... انتظر قليلاً.")

    file_path = f"file_{user_id}"
    ydl_opts = {
        'outtmpl': f"{file_path}.%(ext)s",
        'quiet': True,
        'no_warnings': True,
    }

    if query.data == "dl_high":
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
    elif query.data == "dl_low":
        ydl_opts['format'] = 'worstvideo+worstaudio/best'
    elif query.data == "dl_mp3":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if query.data == "dl_mp3": filename = filename.rsplit('.', 1)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if query.data == "dl_mp3":
                await context.bot.send_audio(chat_id=user_id, audio=f, caption=f"✅ تم تحميل الصوت\n📢 {CHANNEL_ID}")
