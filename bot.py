import os, re, json, uuid, asyncio, tempfile, requests, logging, subprocess, threading
from datetime import datetime
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction

# --- RENDER AWAKE WEB SERVER ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is Alive! 24/7 - Full Video Fix")
    def log_message(self, *args): pass

def run_web():
    port = int(os.getenv("PORT", 10000))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"Web server on {port}")
        server.serve_forever()
    except: pass
threading.Thread(target=run_web, daemon=True).start()

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()]
AUTO_DELETE_MIN = int(os.getenv("AUTO_DELETE_MINUTES","2"))
BOT_USERNAME = os.getenv("BOT_USERNAME","@YourBot")
CATBOX_ENABLED = os.getenv("CATBOX_ENABLED","True").lower()=="true"
MAX_SIZE_MB = int(os.getenv("MAX_TELEGRAM_SIZE_MB","50"))
LOGO_PATH = "TIKTOKLOGO.png"
if not BOT_TOKEN: raise ValueError("BOT_TOKEN missing")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DATA_FILE = "bot_data.json"
URL_STORE = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE,'r') as f: DATA=json.load(f)
        DATA.setdefault("cache", {}); DATA.setdefault("history", {}); DATA.setdefault("stats", {"total":0,"today":0,"last_reset":str(datetime.now().date())})
        DATA.setdefault("banned", []); DATA.setdefault("users", {})
    except: DATA={"cache":{},"history":{},"stats":{"total":0,"today":0,"last_reset":str(datetime.now().date())},"banned":[],"users":{}}
else: DATA={"cache":{},"history":{},"stats":{"total":0,"today":0,"last_reset":str(datetime.now().date())},"banned":[],"users":{}}
def save_data():
    try:
        with open(DATA_FILE,'w') as f: json.dump(DATA,f)
    except: pass
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
    author=d.get('author',{}); uniq=author.get('unique_id',''); title=d.get('title','') or "No caption"; views=format_number(d.get('play_count',0)); likes=format_number(d.get('digg_count',0)); music=d.get('music_info',{}).get('title','Original')[:30]; count=len(DATA.get("history",{}).get(str(uid),[])) if uid else 0; rank=get_rank(count)
    return f"🎬 @{uniq} • {rank}\n📝 {title[:120]}\n📊 {views} views • ❤️ {likes} • 🎵 {music}\n✨ {BOT_USERNAME}"

def upload_to_catbox(file_path):
    try:
        with open(file_path,'rb') as f:
            r = requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload": f}, timeout=120)
        if r.status_code==200 and "catbox" in r.text: return r.text.strip()
    except: pass
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
    return dest_path

def add_watermark_if_possible(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1][0]scale2ref=w=iw*0.18:h=ow/mdar[wm][vid];[vid][wm]overlay=W-w-20:20","-codec:a","copy",output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if os.path.exists(output_path) and os.path.getsize(output_path)>1000: return output_path
    except: pass
    return video_path

def download_tiktok(url, tmpdir, quality="hd"):
    # FIX 9 SECOND BUG - USE YT-DLP FOR FULL VIDEO
    try:
        import yt_dlp
        fp = os.path.join(tmpdir, f'full_{quality}.mp4')
        cover_path = os.path.join(tmpdir, 'cover.jpg')

        # Get info for caption
        ydl_opts_info = {'quiet': True, 'skip_download': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            data = {
                'title': info.get('title',''),
                'author': {'unique_id': info.get('uploader','tiktok'), 'nickname': info.get('uploader','')},
                'play_count': info.get('view_count',0),
                'digg_count': info.get('like_count',0),
                'music_info': {'title': info.get('track','Original')},
                'origin_cover': info.get('thumbnail',''),
                'cover': info.get('thumbnail',''),
                'duration': info.get('duration',0)
            }
            print(f"Video duration: {data['duration']} sec - FULL")

        ydl_opts = {
            'outtmpl': fp,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'no_watermark': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(fp):
            for f in os.listdir(tmpdir):
                if f.endswith('.mp4'):
                    fp = os.path.join(tmpdir, f)
                    break

        if not os.path.exists(fp):
            raise Exception("yt-dlp file not found")

        try:
            thumb_url = data.get('origin_cover')
            if thumb_url:
                with requests.get(thumb_url, stream=True, timeout=10) as cr:
                    with open(cover_path,'wb') as cf:
                        for c in cr.iter_content(8192): cf.write(c)
        except: pass

        final_path = fp
        if os.path.exists(LOGO_PATH):
            wm_out = os.path.join(tmpdir, f'wm_{quality}.mp4')
            final_path = add_watermark_if_possible(fp, LOGO_PATH, wm_out)

        size = os.path.getsize(final_path)
        print(f"FULL VIDEO OK: {size} bytes, {data['duration']}s")
        return {"type":"video","path":final_path,"cover":cover_path if os.path.exists(cover_path) else None,"data":data,"url":url}

    except Exception as e:
        print(f"yt-dlp failed {e}, fallback to tikwm API")
        try:
            r = requests.get(f"https://www.tikwm.com/api/?url={url}", headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
            j = r.json()
            if j.get('code')!= 0: raise Exception("API failed")
            d = j['data']
            if d.get('images'): return {"type":"slideshow","data":d}
            vurl = d.get('hdplay') or d.get('play') or d.get('wmplay')
            fp = os.path.join(tmpdir, f'tiktok_{quality}.mp4')
            fast_download_file(vurl, fp)
            final_path = fp
            if os.path.exists(LOGO_PATH):
                wm_out = os.path.join(tmpdir, f'wm_{quality}.mp4')
                final_path = add_watermark_if_possible(fp, LOGO_PATH, wm_out)
            cover_path = os.path.join(tmpdir, 'cover.jpg')
            return {"type":"video","path":final_path,"cover":None,"data":d,"url":vurl}
        except Exception as e2:
            raise Exception(f"Both methods failed: {e} / {e2}")

async def process_tiktok(update: Update, context, url: str, quality="hd"):
    uid=str(update.effective_user.id)
    if uid in DATA["banned"]: return await update.message.reply_text("🚫 Banned")
    if uid not in DATA["history"]: DATA["history"][uid]=[]
    DATA["users"][uid] = {"name": update.effective_user.full_name, "username": update.effective_user.username, "last": datetime.now().isoformat()}
    if DATA["stats"].get("last_reset")!= str(datetime.now().date()):
        DATA["stats"]["today"]=0; DATA["stats"]["last_reset"]=str(datetime.now().date())
    save_data()
    m = await update.message.reply_text(f"⬇️ FULL DL {quality.upper()} • Turbo ⚡")
    tmpdir = tempfile.mkdtemp()
    try:
        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        res = await asyncio.to_thread(download_tiktok, url, tmpdir, quality)
        await m.edit_text(f"✅ UPLOADING FULL VIDEO")
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
        duration=d.get('duration',0)
        DATA["history"][uid].insert(0, {"url":url,"title":title[:60],"date":datetime.now().strftime("%d/%m %H:%M"),"author":author})
        DATA["history"][uid]=DATA["history"][uid][:30]; DATA["stats"]["total"]+=1; DATA["stats"]["today"]+=1; save_data()
        short_id=str(uuid.uuid4())[:8]
        URL_STORE[short_id]={"url":url,"data":d,"title":title,"author":author}
        caption=beautiful_caption(d, update.effective_user.id)+f"\n📦 {size_mb:.1f} MB • ⏱️ {duration}s FULL"
        if size_mb > MAX_SIZE_MB and CATBOX_ENABLED:
            await m.edit_text(f"📦 Large {size_mb:.1f}MB -> Catbox...")
            catbox_url = await asyncio.to_thread(upload_to_catbox, path)
            if catbox_url:
                kb=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download FULL from Catbox", url=catbox_url)]])
                await update.message.reply_text(f"📦 FULL {size_mb:.1f}MB • {duration}s\n🔗 {catbox_url}\n🎬 {title[:80]}", reply_markup=kb)
                await m.delete(); return
        kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"🎬 HD FULL", callback_data=f"q_hd_{short_id}")],[InlineKeyboardButton(f"🎵 MP3", callback_data=f"mp3_{short_id}")]])
        thumb_file = open(cover,'rb') if cover and os.path.exists(cover) else None
        with open(path,'rb') as vf:
            sent=await update.message.reply_video(video=vf, thumbnail=thumb_file, caption=caption, reply_markup=kb, supports_streaming=True, read_timeout=180, write_timeout=180)
        if thumb_file: thumb_file.close()
        await m.delete()
        if AUTO_DELETE_MIN>0:
            async def del_msg():
                await asyncio.sleep(AUTO_DELETE_MIN*60)
                try: await context.bot.delete_message(chat_id=sent.chat_id, message_id=sent.message_id)
                except: pass
            asyncio.create_task(del_msg())
    except Exception as e:
        try: await m.edit_text(f"❌ {e}")
        except: pass
        logger.error(f"Failed: {e}")
    finally:
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    DATA["users"][str(uid)] = {"name": update.effective_user.full_name, "username": update.effective_user.username, "last": datetime.now().isoformat()}
    save_data()
    count=len(DATA["history"].get(str(uid),[]))
    welcome = f"👋 WELCOME {get_rank(count)} • {count} DL\n🎬 FULL VIDEO FIX ⚡ 1 min = 1 min\n📦 Catbox >50MB • AutoDel {AUTO_DELETE_MIN}min"
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("📜 History", callback_data="user_history")]])
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
    try:
        parts=data.split('_'); action=parts[0]
        if action=="q":
            qual=parts[1]; sid='_'.join(parts[2:]); info=URL_STORE.get(sid)
            if not info: return await q.message.reply_text("Expired - Send link again")
            tmpdir=tempfile.mkdtemp()
            try:
                m=await q.message.reply_text(f"⬇️ FULL {qual}")
                res=await asyncio.to_thread(download_tiktok, info['url'], tmpdir, qual)
                size_mb=os.path.getsize(res['path'])/(1024*1024)
                if size_mb > MAX_SIZE_MB and CATBOX_ENABLED:
                    cat_url=await asyncio.to_thread(upload_to_catbox, res['path'])
                    if cat_url: return await q.message.reply_text(f"📦 FULL {size_mb:.1f}MB\n{cat_url}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=cat_url)]]))
                thumb=open(res['cover'],'rb') if res['cover'] and os.path.exists(res['cover']) else None
                with open(res['path'],'rb') as vf:
                    await q.message.reply_video(video=vf, thumbnail=thumb, caption=beautiful_caption(info['data'], q.from_user.id)+f" FULL {res['data'].get('duration',0)}s")
                if thumb: thumb.close()
                await m.delete()
            finally:
                import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
        elif action=="mp3":
            sid='_'.join(parts[1:]); info=URL_STORE.get(sid)
            if not info: return
            tmpdir=tempfile.mkdtemp()
            try:
                m=await q.message.reply_text("🎵 MP3 FULL...")
                import yt_dlp
                opts={'outtmpl':os.path.join(tmpdir,"audio.%(ext)s"),'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],'quiet':True}
                def dl():
                    with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([info['url']])
                await asyncio.to_thread(dl)
                mp3_path=None
                for f in os.listdir(tmpdir):
                    if f.endswith('.mp3'): mp3_path=os.path.join(tmpdir,f); break
                if mp3_path:
                    with open(mp3_path,'rb') as af:
                        await q.message.reply_audio(audio=af, title=info['title'][:60], performer=info['author'])
                    await m.delete()
                else: await m.edit_text("❌ MP3 failed")
            finally:
                import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e: print(e)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(f"Users: {len(DATA['users'])} Total: {DATA['stats']['total']} Full Video Fix ON")

def main():
    if not BOT_TOKEN: return
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
    except: pass
    print(f"Starting Bot FULL VIDEO FIX... Logo:{os.path.exists(LOGO_PATH)} Limit:{MAX_SIZE_MB}MB AutoDel:{AUTO_DELETE_MIN}min")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Bot Running - FULL 1 min = 1 min")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    main()
