import os, re, json, uuid, asyncio, tempfile, requests, threading
from datetime import datetime
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-type','text/plain'); self.end_headers()
        self.wfile.write(b"Bot Alive <10s")
    def log_message(self,*a): pass

def run_web():
    try:
        HTTPServer(('0.0.0.0', int(os.getenv("PORT",10000))), HealthHandler).serve_forever()
    except: pass
threading.Thread(target=run_web, daemon=True).start()

load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")
MAX_SIZE_MB=int(os.getenv("MAX_TELEGRAM_SIZE_MB","50"))
BOT_USERNAME=os.getenv("BOT_USERNAME","@YourBot")
if not BOT_TOKEN: raise ValueError("BOT_TOKEN missing")

def upload_to_catbox(fp):
    try:
        with open(fp,'rb') as f:
            r=requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload":f}, timeout=60)
        if r.status_code==200 and "catbox" in r.text: return r.text.strip()
    except: pass
    return None

def download_tiktok_fast(url, tmpdir):
    import yt_dlp
    fp=os.path.join(tmpdir, f"{uuid.uuid4().hex}.mp4")
    ydl_info={'quiet':True,'skip_download':True,'no_warnings':True}
    with yt_dlp.YoutubeDL(ydl_info) as ydl:
        info=ydl.extract_info(url, download=False)
        data={'title':info.get('title','')[:80],'author':info.get('uploader','tiktok'),'duration':info.get('duration',0)}

    ydl_opts={
        'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl':fp,
        'merge_output_format':'mp4',
        'concurrent_fragment_downloads':16,
        'quiet':True,
        'no_warnings':True,
        'noplaylist':True,
        'nocheckcertificate':True,
        'external_downloader_args':{'ffmpeg':['-threads','8']},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    if not os.path.exists(fp):
        for f in os.listdir(tmpdir):
            if f.endswith('.mp4'):
                fp=os.path.join(tmpdir,f)
                break
    return {"path":fp,"data":data}

async def process_tiktok(update:Update, context, url:str):
    t0=datetime.now()
    m=await update.message.reply_text("⚡ Turbo 0.5s...")
    tmpdir=tempfile.mkdtemp()
    try:
        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        res=await asyncio.to_thread(download_tiktok_fast, url, tmpdir)
        path=res["path"]
        size_mb=os.path.getsize(path)/(1024*1024)
        elapsed=(datetime.now()-t0).total_seconds()
        await m.edit_text(f"⚡ {size_mb:.1f}MB in {elapsed:.1f}s - Uploading...")
        if size_mb>MAX_SIZE_MB:
            cat=await asyncio.to_thread(upload_to_catbox, path)
            if cat:
                kb=InlineKeyboardMarkup([[InlineKeyboardButton("📥 DOWNLOAD FULL", url=cat)]])
                await update.message.reply_text(f"📦 FULL {size_mb:.1f}MB {res['data']['duration']}s\n🔗 {cat}", reply_markup=kb)
                await m.delete()
                return
        caption=f"🎬 @{res['data']['author']} • {res['data']['duration']}s FULL\n⚡ {(datetime.now()-t0).total_seconds():.1f}s • {BOT_USERNAME}"
        with open(path,'rb') as vf:
            await update.message.reply_video(video=vf, caption=caption, supports_streaming=True, read_timeout=120, write_timeout=120)
        await m.delete()
        print(f"DONE in {(datetime.now()-t0).total_seconds():.1f}s")
    except Exception as e:
        try: await m.edit_text(f"❌ {e}")
        except: pass
        print(e)
    finally:
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

async def start_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ ULTRA FAST <10s\nSend TikTok link\nFull video fix ON\n1min = 1min FULL")

async def handle(update:Update, context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text or ""
    urls=re.findall(r'https?://\S+', text)
    if not urls:
        urls=re.findall(r'tiktok\.com/\S+|vm\.tiktok\.com/\S+|vt\.tiktok\.com/\S+', text)
        urls=['https://'+u if not u.startswith('http') else u for u in urls]
    if not urls: return
    for u in urls[:3]:
        await process_tiktok(update, context, u)

async def cb(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    try: await q.message.delete()
    except: pass

def main():
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
    except: pass
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Bot Running <10s FULL FIX")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
