import os, re, json, uuid, asyncio, tempfile, requests, logging, subprocess, time, threading
from datetime import datetime
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction

# --- 1. RENDER AWAKE WEB SERVER (for cron-job.org ping) ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is Alive! 24/7")
    def log_message(self, *args): pass

def run_web():
    port = int(os.getenv("PORT", 10000))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"Web server running on port {port} for Render ping")
        server.serve_forever()
    except Exception as e:
        print(f"Web server error: {e}")

threading.Thread(target=run_web, daemon=True).start()
# --- END WEB SERVER ---

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()]
AUTO_DELETE_MIN = int(os.getenv("AUTO_DELETE_MINUTES","2")) # ඔයා කිව්ව විදියට 2
BOT_USERNAME = os.getenv("BOT_USERNAME","@YourBot")
CATBOX_ENABLED = os.getenv("CATBOX_ENABLED","True").lower()=="true"
MAX_SIZE_MB = int(os.getenv("MAX_TELEGRAM_SIZE_MB","50")) # 50ට අඩු සෘජුව Telegram
LOGO_PATH = "TIKTOKLOGO.png"

if not BOT_TOKEN:
<<<<<<< HEAD
    raise ValueError("BOT_TOKEN missing")
=======
    raise ValueError("BOT_TOKEN missing in.env")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_FILE = "bot_data.json"
URL_STORE = {}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE,'r') as f: DATA=json.load(f)
        DATA.setdefault("cache", {}); DATA.setdefault("history", {}); DATA.setdefault("stats", {"total":0,"today":0,"last_reset":str(datetime.now().date())})
        DATA.setdefault("banned", []); DATA.setdefault("users", {})
<<<<<<< HEAD
    except: DATA={"cache":{},"history":{},"stats":{"total":0,"today":0,"last_reset":str(datetime.now().date())},"banned":[],"users":{}}
else: DATA={"cache":{},"history":{},"stats":{"total":0,"today":0,"last_reset":str(datetime.now().date())},"banned":[],"users":{}}

def save_data():
    try:
        with open(DATA_FILE,'w') as f: json.dump(DATA,f)
    except: pass
=======
    except:
        DATA={"cache":{},"history":{},"stats":{"total":0,"today":0,"last_reset":str(datetime.now().date())},"banned":[],"users":{}}
else:
    DATA={"cache":{},"history":{},"stats":{"total":0,"today":0,"last_reset":str(datetime.now().date())},"banned":[],"users":{}}

def save_data():
    try:
        with open(DATA_FILE,'w') as f: json.dump(DATA,f, indent=2)
    except Exception as e:
        logger.error(f"Save error: {e}")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c

def is_admin(uid): return uid in ADMIN_IDS
def get_rank(c):
    if c>=100: return "👑 Diamond"
    if c>=50: return "🥇 Gold"
    if c>=20: return "🥈 Silver"
    if c>=5: return "🥉 Bronze"
    return "🌱 Newbie"

def format_number(n):
    try:
        n=int(n)
        if n>=1000000: return f"{n/1000000:.1f}M"
        if n>=1000: return f"{n/1000:.1f}K"
        return str(n)
    except: return str(n)

def beautiful_caption(d, uid=None):
    author=d.get('author',{}); uniq=author.get('unique_id',''); nick=author.get('nickname','')
    title=d.get('title','') or "No caption"; views=format_number(d.get('play_count',0))
    likes=format_number(d.get('digg_count',0)); music=d.get('music_info',{}).get('title','Original')[:30]
    count=len(DATA.get("history",{}).get(str(uid),[])) if uid else 0
    rank=get_rank(count)
    return f"""╭─ 🎬 𝗧𝗜𝗞𝗧𝗢𝗞 𝗗𝗟 ───────────╮
│ 👤 @{uniq} • {rank}
│ 📝 {title[:120]}
├─ 📊 {views} views • ❤️ {likes} • 🎵 {music}
╰─ ✨ {BOT_USERNAME} ─╯"""

def upload_to_catbox(file_path):
    try:
        with open(file_path,'rb') as f:
<<<<<<< HEAD
            r = requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload": f}, timeout=90)
        if r.status_code==200 and "catbox" in r.text: return r.text.strip()
    except Exception as e: logger.error(f"Catbox failed: {e}")
=======
            r = requests.post("https://catbox.moe/user/api.php",
                data={"reqtype":"fileupload"},
                files={"fileToUpload": f}, timeout=90)
        if r.status_code==200 and "catbox" in r.text:
            return r.text.strip()
    except Exception as e:
        logger.error(f"Catbox upload failed: {e}")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
    return None

def fast_download_file(url, dest_path):
    headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.tikwm.com/'}
    with requests.Session() as s:
        s.headers.update(headers)
        with s.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest_path,'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024*2):
                    if chunk: f.write(chunk)
<<<<<<< HEAD
=======
    elapsed=time.time()-start
    size_mb=os.path.getsize(dest_path)/(1024*1024)
    logger.info(f"Fast DL: {size_mb:.1f}MB in {elapsed:.1f}s")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
    return dest_path

def add_watermark_if_possible(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        subprocess.run(["ffmpeg","-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1][0]scale2ref=w=iw*0.18:h=ow/mdar[wm][vid];[vid][wm]overlay=W-w-20:20","-codec:a","copy",output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
<<<<<<< HEAD
        if os.path.exists(output_path) and os.path.getsize(output_path)>1000: return output_path
    except: pass
=======
        if os.path.exists(output_path) and os.path.getsize(output_path)>1000:
            return output_path
    except Exception as e:
        logger.warning(f"Watermark failed: {e}")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
    return video_path

def download_tiktok(url, tmpdir, quality="hd"):
    r = requests.get(f"https://www.tikwm.com/api/?url={url}", headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
    j = r.json()
    if j.get('code')!= 0: raise Exception("API failed, try again")
    d = j['data']
    if d.get('images'): return {"type":"slideshow","data":d}
    vurl = d.get('hdplay') or d.get('play')
    if quality=="watermark": vurl=d.get('wmplay') or vurl
    if quality=="original": vurl=d.get('play') or vurl
    fp = os.path.join(tmpdir, f'tiktok_{quality}.mp4')
    cover_path = os.path.join(tmpdir, 'cover.jpg')
    try:
        cover_url = d.get('origin_cover') or d.get('cover')
        if cover_url:
            with requests.get(cover_url, stream=True, timeout=10) as cr:
                with open(cover_path,'wb') as cf:
                    for c in cr.iter_content(8192): cf.write(c)
    except: pass
    fast_download_file(vurl, fp)
    final_path = fp
    if os.path.exists(LOGO_PATH):
        wm_out = os.path.join(tmpdir, f'wm_{quality}.mp4')
        final_path = add_watermark_if_possible(fp, LOGO_PATH, wm_out)
    return {"type":"video","path":final_path,"cover":cover_path if os.path.exists(cover_path) else None,"data":d,"url":vurl}

async def animate_downloading(msg, quality="HD"):
<<<<<<< HEAD
    frames=[f"╭─ ⬇️ {quality} ─╮\n│ ◐ 10% Turbo ⚡\n╰─╯",f"╭─ ⬇️ {quality} ─╮\n│ ◓ 45% Fast...\n╰─╯",f"╭─ ⬇️ {quality} ─╮\n│ ◑ 80% Fast...\n╰─╯"]
=======
    frames=[f"╭─ ⬇️ {quality} ─╮\n│ ◐ 10% Turbo ⚡\n╰─╯",f"╭─ ⬇️ {quality} ─╮\n│ ◓ 45% Fast...\n╰─╯",f"╭─ ⬇️ {quality} ─╮\n│ ◑ 80% Fast...\n╰─╯",f"╭─ ⚡ {quality} ─╮\n│ ◒ 95% Final...\n╰─╯"]
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
    i=0
    try:
        while True:
            await msg.edit_text(frames[i%len(frames)]); i+=1; await asyncio.sleep(0.4)
    except: pass

async def auto_delete_message(context, chat_id, message_id):
    await asyncio.sleep(AUTO_DELETE_MIN*60)
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass

async def process_tiktok(update: Update, context, url: str, quality="hd"):
    uid=str(update.effective_user.id)
    if uid in DATA["banned"]: return await update.message.reply_text("🚫 Banned")
    if uid not in DATA["history"]: DATA["history"][uid]=[]
    DATA["users"][uid] = {"name": update.effective_user.full_name, "username": update.effective_user.username, "last": datetime.now().isoformat()}
    if DATA["stats"].get("last_reset")!= str(datetime.now().date()):
        DATA["stats"]["today"]=0; DATA["stats"]["last_reset"]=str(datetime.now().date())
    save_data()
<<<<<<< HEAD
    m = await update.message.reply_text(f"╭─ ⬇️ 𝗙𝗔𝗦𝗧 𝗗𝗟 {quality.upper()} ─╮\n│ ◐ 0% • Turbo ON ⚡\n╰─╯")
=======

    m = await update.message.reply_text(f"╭─ ⬇️ 𝗙𝗔𝗦𝗧 𝗗𝗟 {quality.upper()} ─╮\n│ ◐ 0% • Turbo ON ⚡\n╰─────────────────╯")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
    anim_task = asyncio.create_task(animate_downloading(m, quality.upper()))
    tmpdir = tempfile.mkdtemp()
    try:
        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        res = await asyncio.to_thread(download_tiktok, url, tmpdir, quality)
        anim_task.cancel()
        await m.edit_text(f"╭─ ✅ 𝗨𝗣𝗟𝗢𝗔𝗗𝗜𝗡𝗚 ─╮\n│ ▓▓▓▓▓ 100%\n╰─╯")
        if res["type"]=="slideshow":
            d=res["data"]; files=[]; media=[]
            for img_url in d['images'][:10]:
                img_path=os.path.join(tmpdir, f"{uuid.uuid4()}.jpg")
                with requests.get(img_url, stream=True, timeout=15) as r:
                    with open(img_path,'wb') as f:
                        for c in r.iter_content(8192): f.write(c)
                f=open(img_path,'rb'); files.append(f); media.append(InputMediaPhoto(f))
            await update.message.reply_media_group(media)
            for f in files: f.close()
            await m.delete(); return
        path=res["path"]; cover=res["cover"]; d=res["data"]
        size_mb=os.path.getsize(path)/(1024*1024)
        title=d.get('title') or ""; author=d.get('author',{}).get('unique_id','')
        DATA["history"][uid].insert(0, {"url":url,"title":title[:60],"date":datetime.now().strftime("%d/%m %H:%M"),"author":author})
        DATA["history"][uid]=DATA["history"][uid][:30]; DATA["stats"]["total"]+=1; DATA["stats"]["today"]+=1; save_data()
        short_id=str(uuid.uuid4())[:8]
        URL_STORE[short_id]={"url":url,"data":d,"title":title,"author":author}
        caption=beautiful_caption(d, update.effective_user.id)+f"\n📦 {size_mb:.1f} MB"
<<<<<<< HEAD
        if size_mb > MAX_SIZE_MB and CATBOX_ENABLED:
            await m.edit_text(f"╭─ 📦 Large {size_mb:.1f}MB ─╮\n│ ⬆️ Catbox.moe...\n╰─╯")
            catbox_url = await asyncio.to_thread(upload_to_catbox, path)
            if catbox_url:
                kb=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download from Catbox 📦", url=catbox_url)],[InlineKeyboardButton(f"🎵 Get MP3", callback_data=f"mp3_{short_id}")]])
                txt=f"""╭─ 📦 𝗟𝗔𝗥𝗚𝗘 𝗙𝗜𝗟𝗘 ─╮
│ ⚠️ {size_mb:.1f} MB > {MAX_SIZE_MB}MB
│ 🎬 {title[:80]}
│ 🔗 {catbox_url}
╰─ 💡 Valid 30+ days ─╯"""
                await update.message.reply_text(txt, reply_markup=kb)
                await m.delete(); return
        kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"🎬 HD 1080p 💎", callback_data=f"q_hd_{short_id}")],[InlineKeyboardButton(f"📱 Original", callback_data=f"q_original_{short_id}"), InlineKeyboardButton(f"💧 Watermark", callback_data=f"q_watermark_{short_id}")],[InlineKeyboardButton(f"🎵 MP3", callback_data=f"mp3_{short_id}"), InlineKeyboardButton(f"🗑️ Delete", callback_data=f"del_{short_id}")]])
=======

        if size_mb > MAX_SIZE_MB and CATBOX_ENABLED:
            await m.edit_text(f"╭─ 📦 Large {size_mb:.1f}MB ─╮\n│ ⬆️ Uploading to Catbox.moe...\n╰─────────────────╯")
            catbox_url = await asyncio.to_thread(upload_to_catbox, path)
            if catbox_url:
                kb=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download from Catbox 📦", url=catbox_url)],
                    [InlineKeyboardButton(f"🎵 Get MP3 ({size_mb:.0f}MB→5MB)", callback_data=f"mp3_{short_id}")],
                ])
                txt=f"""╭─ 📦 𝗟𝗔𝗥𝗚𝗘 𝗙𝗜𝗟𝗘 ───────────╮
│ ⚠️ {size_mb:.1f} MB > {MAX_SIZE_MB}MB Limit
│ 🎬 {title[:80]}
│ 👤 @{author}
├─ 📥 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 ───────┤
│ 🔗 {catbox_url}
╰─ 💡 Valid 30+ days ─╯"""
                await update.message.reply_text(txt, reply_markup=kb)
                await m.delete()
                return

        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎬 HD 1080p 💎", callback_data=f"q_hd_{short_id}")],
            [InlineKeyboardButton(f"📱 Original", callback_data=f"q_original_{short_id}"), InlineKeyboardButton(f"💧 Watermark", callback_data=f"q_watermark_{short_id}")],
            [InlineKeyboardButton(f"🎵 MP3", callback_data=f"mp3_{short_id}"), InlineKeyboardButton(f"🗑️ Delete", callback_data=f"del_{short_id}")]
        ])
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
        thumb_file = open(cover,'rb') if cover and os.path.exists(cover) else None
        with open(path,'rb') as vf:
            sent=await update.message.reply_video(video=vf, thumbnail=thumb_file, caption=caption, reply_markup=kb, supports_streaming=True, read_timeout=180, write_timeout=180)
        if thumb_file: thumb_file.close()
        await m.delete()
        if AUTO_DELETE_MIN>0: asyncio.create_task(auto_delete_message(context, sent.chat_id, sent.message_id))
    except Exception as e:
        try: anim_task.cancel()
        except: pass
        try: await m.edit_text(f"❌ {e}")
        except: pass
        logger.error(f"Failed: {e}")
    finally:
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
        # RAM නිදහස් කිරීම
        try:
            for f in os.listdir(tmpdir): pass
        except: pass

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    DATA["users"][str(uid)] = {"name": update.effective_user.full_name, "username": update.effective_user.username, "last": datetime.now().isoformat()}
    save_data()
    count=len(DATA["history"].get(str(uid),[]))
    welcome = f"""╭─ 👋 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 ─╮
│ {get_rank(count)} • {count} DL
│ 🎬 Ultra Fast ⚡ • 📦 Catbox >50MB
│ 💎 HD + Logo Watermark
│ ⏱️ Auto Delete {AUTO_DELETE_MIN} min (RAM Free)
╰─ ✨ Send TikTok link! ─╯"""
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("🎬 Send Link", callback_data="help")],[InlineKeyboardButton("📜 History", callback_data="user_history"),InlineKeyboardButton("📊 Rank", callback_data="my_rank")]])
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH,'rb') as lf: await update.message.reply_photo(photo=lf, caption=welcome, reply_markup=kb)
    else: await update.message.reply_text(welcome, reply_markup=kb)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text=update.message.text or ""
    urls=re.findall(r'https?://\S+', text)
    if not urls:
        urls=re.findall(r'tiktok\.com/\S+|vm\.tiktok\.com/\S+', text)
        urls=['https://'+u if not u.startswith('http') else u for u in urls]
    if not urls: return
    for u in urls[:5]: await process_tiktok(update, context, u, "hd")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); data=q.data
    if data=="user_history":
        uid=str(q.from_user.id); hist=DATA.get("history",{}).get(uid,[])
        if not hist: return await q.message.reply_text("No history")
        txt="📜 History:\n"+"\n".join([f"{i}. @{h['author']} - {h['date']}\n{h['url']}\n" for i,h in enumerate(hist[:10],1)])
        await q.message.reply_text(txt); return
    if data=="my_rank":
        cnt=len(DATA.get("history",{}).get(str(q.from_user.id),[]))
        await q.message.reply_text(f"👑 {get_rank(cnt)} • {cnt} DL"); return
    try:
        parts=data.split('_'); action=parts[0]
        if action=="del":
            try: await q.message.delete()
            except: pass
            return
        if action=="q":
            qual=parts[1]; sid='_'.join(parts[2:]); info=URL_STORE.get(sid)
            if not info: return await q.message.reply_text("Expired")
            tmpdir=tempfile.mkdtemp()
            try:
                m=await q.message.reply_text(f"⬇️ Fast DL {qual}")
                res=await asyncio.to_thread(download_tiktok, info['url'], tmpdir, qual)
                size_mb=os.path.getsize(res['path'])/(1024*1024)
                if size_mb > MAX_SIZE_MB and CATBOX_ENABLED:
                    cat_url=await asyncio.to_thread(upload_to_catbox, res['path'])
                    if cat_url: return await q.message.reply_text(f"📦 {size_mb:.1f}MB\n🔗 {cat_url}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=cat_url)]]))
                thumb=open(res['cover'],'rb') if res['cover'] and os.path.exists(res['cover']) else None
                with open(res['path'],'rb') as vf:
                    await q.message.reply_video(video=vf, thumbnail=thumb, caption=beautiful_caption(info['data'], q.from_user.id))
                if thumb: thumb.close()
                await m.delete()
            finally:
                import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
        elif action=="mp3":
            sid='_'.join(parts[1:]); info=URL_STORE.get(sid)
            if not info: return
            tmpdir=tempfile.mkdtemp()
            try:
                m=await q.message.reply_text("🎵 Extracting MP3...")
                import yt_dlp
                opts={'outtmpl':os.path.join(tmpdir,"audio.%(ext)s"),'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],'quiet':True}
                def dl():
<<<<<<< HEAD
                    with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([info['url']])
=======
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([info['url']])
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
                await asyncio.to_thread(dl)
                mp3_path=None
                for f in os.listdir(tmpdir):
                    if f.endswith('.mp3'): mp3_path=os.path.join(tmpdir,f); break
                if mp3_path:
                    with open(mp3_path,'rb') as af:
                        await q.message.reply_audio(audio=af, title=info['title'][:60], performer=info['author'])
                    await m.delete()
<<<<<<< HEAD
                else: await m.edit_text("❌ MP3 failed")
            finally:
                import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e: logger.error(f"Button error: {e}")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return await update.message.reply_text("⛔ Not admin")
    await update.message.reply_text(f"🔐 Admin • Users: {len(DATA['users'])} • Total: {DATA['stats']['total']} • Catbox: {CATBOX_ENABLED} • RAM Free: {AUTO_DELETE_MIN}min")

def main():
    if not BOT_TOKEN:
        print("Missing BOT_TOKEN"); return
    # Fix 409 Conflict
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
        print("Webhook cleared - No 409")
    except: pass
    print(f"Starting Bot... Logo:{os.path.exists(LOGO_PATH)} Catbox:{CATBOX_ENABLED} Limit:{MAX_SIZE_MB}MB AutoDel:{AUTO_DELETE_MIN}min")
=======
                else:
                    await m.edit_text("❌ MP3 failed")
            finally:
                import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Button error: {e}")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return await update.message.reply_text("⛔ Not admin")
    await update.message.reply_text(f"🔐 Admin • Users: {len(DATA['users'])} • Total: {DATA['stats']['total']} • Catbox: {CATBOX_ENABLED} • Logo: {os.path.exists(LOGO_PATH)}")

def main():
    if not BOT_TOKEN:
        print("Missing BOT_TOKEN in.env")
        return
    print(f"Starting Bot... Logo:{os.path.exists(LOGO_PATH)} Catbox:{CATBOX_ENABLED} Limit:{MAX_SIZE_MB}MB")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("admin", admin_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
<<<<<<< HEAD
    print("Bot Running - Ready + Web Server for Ping")
=======
    print("Bot Running - Polling started")
>>>>>>> f68d2c387811c255424b7c2591045a509407932c
    application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    main()
