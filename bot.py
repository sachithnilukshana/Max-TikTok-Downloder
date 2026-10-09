import os, re, json, uuid, asyncio, tempfile, requests, threading, subprocess, logging, html, time, hashlib, sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction, ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")
ADMIN_ID=int(os.getenv("ADMIN_ID","0"))
MAX_SIZE_MB=int(os.getenv("MAX_TELEGRAM_SIZE_MB","50"))
AUTO_DELETE_MIN=int(os.getenv("AUTO_DELETE_MIN","10"))
BOT_USERNAME=os.getenv("BOT_USERNAME","@YourBot")
LOGO_PATH="TIKTOKLOGO.png"
PROXY_LIST=[p.strip() for p in os.getenv("PROXY_LIST","").split(",") if p.strip()]
CHANNEL_USERNAME=os.getenv("CHANNEL_USERNAME","") # For force sub, e.g. @mychannel
WEBAPP_URL=os.getenv("WEBAPP_URL",f"https://{os.getenv('KOYEB_APP_NAME','')}.koyeb.app/app")

# ===== DATABASE (Feature #4) =====
DB_FILE="max_downloader.db"
def init_db():
    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT, joined_at TEXT, total_downloads INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS cache (url_hash TEXT PRIMARY KEY, url TEXT, file_id TEXT, file_unique_id TEXT, size REAL, title TEXT, author TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, url TEXT, title TEXT, size REAL, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, url TEXT, title TEXT, created_at TEXT, UNIQUE(user_id, url))")
    c.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit(); conn.close()
init_db()
def db_query(q, params=(), fetch=False):
    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    c.execute(q, params)
    data=c.fetchall() if fetch else None
    conn.commit(); conn.close()
    return data

# ===== FEATURE #10 LANGUAGE =====
LANGS={
    "en": {"welcome":"🚀 <b>MAX DOWNLOADER</b> 🚀\nSend TikTok link ✨\n\n💎 1080p Full Quality\n📦 Large File 1GB Support\n⚡ Real-Time Progress\n🌐 Auto language: {lang}","downloading":"Downloading","queue":"⏳ Queue: You are #{pos} - {wait}s wait","cached":"⚡ From Cache - Instant! 🚀","fav_added":"❤️ Added to favorites","fav_list":"❤️ Your Favorites","history":"📜 Your History","error_private":"🔒 Video is private or deleted","error_region":"🌍 Region blocked - retrying with proxy...","error_limit":"⏰ Too many requests - wait {sec}s","broadcast_done":"📢 Broadcast sent to {n} users"},
    "ar": {"welcome":"🚀 <b>MAX DOWNLOADER</b> 🚀\nأرسل رابط تيك توك ✨","downloading":"جار التحميل","queue":"⏳ قائمة الانتظار: أنت رقم {pos}","cached":"⚡ من الذاكرة - فوري!","fav_added":"❤️ تمت الإضافة للمفضلة","fav_list":"❤️ مفضلتك","history":"📜 سجلك","error_private":"🔒 الفيديو خاص أو محذوف","error_region":"🌍 محظور في منطقتك","error_limit":"⏰ طلبات كثيرة - انتظر {sec}ث","broadcast_done":"📢 تم الإرسال لـ {n}"},
    "hi": {"welcome":"🚀 <b>MAX DOWNLOADER</b> 🚀\nTikTok लिंक भेजें ✨","downloading":"डाउनलोड हो रहा","queue":"⏳ कतार: आप #{pos} पर हैं","cached":"⚡ कैश से - तुरंत!","fav_added":"❤️ पसंदीदा में जोड़ा","fav_list":"❤️ आपके पसंदीदा","history":"📜 आपका इतिहास","error_private":"🔒 वीडियो प्राइवेट है","error_region":"🌍 क्षेत्र ब्लॉक","error_limit":"⏰ बहुत अनुरोध - {sec}s रुको","broadcast_done":"📢 {n} यूजर्स को भेजा"},
    "ru": {"welcome":"🚀 <b>MAX DOWNLOADER</b> 🚀\nОтправь ссылку TikTok ✨","downloading":"Загрузка","queue":"⏳ Очередь: Вы #{pos}","cached":"⚡ Из кэша - мгновенно!","fav_added":"❤️ Добавлено в избранное","fav_list":"❤️ Избранное","history":"📜 История","error_private":"🔒 Видео приватное","error_region":"🌍 Блок региона","error_limit":"⏰ Много запросов - жди {sec}с","broadcast_done":"📢 Отправлено {n}"},
}
def get_user_lang(user):
    try:
        code=(user.language_code or "en")[:2]
        if code in LANGS: return code
    except: pass
    return "en"
def t(user_id, key, **kwargs):
    try:
        conn=sqlite3.connect(DB_FILE); c=conn.cursor()
        c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)); r=c.fetchone(); conn.close()
        lang=r[0] if r and r[0] in LANGS else "en"
    except: lang="en"
    txt=LANGS.get(lang, LANGS["en"]).get(key, key)
    try: return txt.format(**kwargs)
    except: return txt

# ===== GLOBAL STATE =====
STATS_FILE="stats.json"
URL_STORE={}
LIVE_DOWNLOADS=0
progress_data_global={"pct":0,"speed":"","eta":"","downloaded":"","total":""}
DOWNLOAD_SEM=asyncio.Semaphore(3) # Feature #2 Queue limit 3 parallel
QUEUE_DEQUE=deque()
USER_REQUESTS=defaultdict(list) # anti-spam
CACHE_MEMORY={} # url_hash -> file_id

# ===== WEB APP (Feature #11) =====
WEBAPP_HTML="""
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Max Downloader</title><style>
body{font-family:sans-serif;background:#0a0a0f;color:#fff;padding:20px;text-align:center}
.card{background:#1a1a2e;border-radius:16px;padding:20px;margin:15px 0;border:1px solid #ff0055}
.btn{background:linear-gradient(90deg,#ff0055,#ff5500);color:#fff;padding:12px 24px;border-radius:10px;text-decoration:none;display:inline-block;margin:10px}
h1{color:#ff0055}
</style></head><body>
<h1>🚀 MAX DOWNLOADER WEB</h1>
<div class="card"><h3>📊 Live Stats</h3><p id="stats">Loading...</p></div>
<div class="card"><h3>🎬 How to use</h3><p>Send TikTok link to bot<br>@YourBot</p><a class="btn" href="https://t.me/YourBot">Open Bot</a></div>
<div class="card"><h3>❤️ Favorites & History</h3><p>Access in bot: /favorites /history</p></div>
<script>
fetch('/api/stats').then(r=>r.json()).then(d=>{
 document.getElementById('stats').innerHTML=`Total: ${d.total}<br>Users: ${d.users}<br>Live: ${d.live}`;
});
</script></body></html>
"""

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=="/app" or parsed.path=="/":
            self.send_response(200); self.send_header("Content-type","text/html"); self.end_headers()
            self.wfile.write(WEBAPP_HTML.encode())
        elif parsed.path=="/api/stats":
            try:
                conn=sqlite3.connect(DB_FILE); c=conn.cursor()
                c.execute("SELECT COUNT(*) FROM users"); users=c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM cache"); cache=c.fetchone()[0]
                conn.close()
                import json as js
                data=js.dumps({"total":cache,"users":users,"live":LIVE_DOWNLOADS})
                self.send_response(200); self.send_header("Content-type","application/json"); self.end_headers()
                self.wfile.write(data.encode())
            except Exception as e:
                self.send_response(200); self.end_headers(); self.wfile.write(b'{"error":1}')
        else:
            self.send_response(200); self.end_headers(); self.wfile.write(b"Max Downloader Alive")
    def log_message(self,*a): pass
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.getenv("PORT",10000))), HealthHandler).serve_forever(), daemon=True).start()

# ===== UTILS =====
def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE,'r') as f: return json.load(f)
    except: pass
    return {"total":0,"total_size":0,"users":[]}
def save_stats(s):
    try:
        with open(STATS_FILE,'w') as f: json.dump(s,f)
    except: pass
STATS=load_stats()
try: STATS['users']=set(STATS['users'])
except: STATS['users']=set()

def progress_bar(pct):
    pct=int(max(0,min(100,pct)))
    filled=pct//10
    return f"{'█'*filled}{'░'*(10-filled)} {pct}%"

def url_hash(url):
    return hashlib.md5(url.encode()).hexdigest()[:16]

def beautiful_caption(info, size, elapsed, user_name, cached=False):
    safe_title=html.escape(info['title'][:45])
    safe_author=html.escape(info['author'][:20])
    cache_tag="⚡ CACHED INSTANT 🚀\n" if cached else ""
    return (
        f"{cache_tag}🚀 <b>MAX DOWNLOADER</b> 🚀\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Hey <b>{html.escape(user_name)}</b>!\n"
        f"┌─ 🎬 Video Info ─┐\n"
        f"│ 👤 @{safe_author}\n"
        f"│ 📝 {safe_title}\n"
        f"│ ⏱ {info['duration']}s | 📦 {size:.1f}MB\n"
        f"│ ⚡ {elapsed:.1f}s | 💎 FULL HD\n"
        f"└───────────────┘\n"
        f"📊 Total: {STATS['total']+1} | 👥 {len(STATS['users'])} | 🔴 {LIVE_DOWNLOADS} live\n"
        f"💎 Max Downloader • No Compression\n"
        f"⏰ Auto-delete {AUTO_DELETE_MIN}min"
    )

def upload_large_file_real(fp):
    size_mb=os.path.getsize(fp)/(1024*1024)
    if size_mb > 100:
        try:
            with open(fp,'rb') as f:
                r=requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype":"fileupload","time":"72h"}, files={"fileToUpload":(os.path.basename(fp), f, "video/mp4")}, timeout=600)
            if r.status_code==200 and "http" in r.text: return r.text.strip(), "Litterbox 1GB 72h"
        except Exception as e: logger.error(f"Litterbox {e}")
    if size_mb < 200:
        try:
            with open(fp,'rb') as f:
                r=requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload":f}, timeout=600)
            if r.status_code==200 and "http" in r.text: return r.text.strip(), "Catbox.moe"
        except: pass
    try:
        r=requests.get("https://api.gofile.io/servers", timeout=20)
        server=r.json()['data']['servers'][0]['name']
        with open(fp,'rb') as f:
            r=requests.post(f"https://{server}.gofile.io/uploadFile", files={"file":f}, timeout=600)
        j=r.json()
        if j['status']=='ok': return j['data']['downloadPage'], "GoFile 10GB"
    except: pass
    return None, None

def add_watermark_fixed(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1:v]scale=iw*0.18:-1[wm];[0:v][wm]overlay=W-w-20:H-h-20:format=auto,format=yuv420p","-c:a","copy","-movflags","+faststart",output_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if os.path.exists(output_path) and os.path.getsize(output_path)>10000: return output_path
    except: pass
    return video_path

def get_tiktok_info(url, tmpdir):
    try:
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        j=r.json()
        if j.get('code')==0:
            d=j['data']
            thumb_path=None
            if d.get('cover'):
                thumb_path=os.path.join(tmpdir, "thumb.jpg")
                try:
                    with requests.get(d.get('cover'), timeout=15) as cr:
                        with open(thumb_path,'wb') as f: f.write(cr.content)
                except: thumb_path=None
            return {'title':d.get('title','')[:80],'author':d.get('author',{}).get('unique_id','tiktok'),'duration':d.get('duration',0),'thumb':thumb_path,'url':url}
    except: pass
    import yt_dlp
    with yt_dlp.YoutubeDL({'quiet':True,'skip_download':True}) as ydl:
        i=ydl.extract_info(url, download=False)
        return {'title':i.get('title','')[:80],'author':i.get('uploader','tiktok'),'duration':i.get('duration',0),'thumb':None,'url':url}

def make_hook():
    def hook(d):
        if d['status']=='downloading':
            try:
                pct=float(d.get('_percent_str','0%').replace('%','').strip())
                progress_data_global["pct"]=pct
                progress_data_global["speed"]=d.get('_speed_str','').strip()
                progress_data_global["eta"]=d.get('_eta_str','').strip()
                progress_data_global["downloaded"]=d.get('_downloaded_bytes_str','').strip()
                progress_data_global["total"]=d.get('_total_bytes_str','').strip()
            except: pass
    return hook

def download_video_sync_max_realtime(url, tmpdir, watermark=False, proxy=None):
    import yt_dlp
    progress_data_global["pct"]=0
    fp=os.path.join(tmpdir, f"{uuid.uuid4().hex}.mp4")
    ydl_opts={
        'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl':fp,
        'merge_output_format':'mp4',
        'concurrent_fragment_downloads':8,
        'quiet':True,
        'no_warnings':True,
        'noplaylist':True,
        'nocheckcertificate':True,
        'progress_hooks':[make_hook()],
    }
    if proxy: ydl_opts['proxy']=proxy
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if not os.path.exists(fp):
            for f in os.listdir(tmpdir):
                if f.endswith('.mp4'): fp=os.path.join(tmpdir,f); break
        if watermark:
            out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp=add_watermark_fixed(fp, LOGO_PATH, out)
        return fp
    except Exception as e:
        logger.error(f"yt-dlp primary fail {e}")
        raise e

def download_with_retry(url, tmpdir, watermark=False):
    # Feature #6 Retry + Proxy
    last_err=None
    proxies=[None]+PROXY_LIST
    for attempt in range(3):
        for proxy in proxies:
            try:
                if proxy: logger.info(f"Retry {attempt+1} with proxy {proxy[:20]}")
                return download_video_sync_max_realtime(url, tmpdir, watermark, proxy)
            except Exception as e:
                last_err=e
                err_str=str(e).lower()
                if "private" in err_str or "deleted" in err_str or "not available" in err_str:
                    raise Exception("private_video")
                if "403" in err_str or "blocked" in err_str:
                    continue
                time.sleep(1)
    raise last_err or Exception("download_failed")

def download_mp3_fixed(url, tmpdir):
    import yt_dlp
    progress_data_global["pct"]=0
    outtmpl=os.path.join(tmpdir, f"audio_{uuid.uuid4().hex}.%(ext)s")
    ydl_opts={
        'format':'bestaudio/best',
        'outtmpl':outtmpl,
        'quiet':True,
        'no_warnings':True,
        'progress_hooks':[make_hook()],
        'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    for f in os.listdir(tmpdir):
        if f.endswith('.mp3'): return os.path.join(tmpdir,f)
    raise FileNotFoundError("MP3 failed")

async def delete_after(context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=context.job.data['chat_id'], message_id=context.job.data['msg_id'])
    except: pass

def check_antispam(user_id):
    # Feature #2 Anti-spam - 5 req/min
    now=time.time()
    USER_REQUESTS[user_id]=[t for t in USER_REQUESTS[user_id] if now-t<60]
    if len(USER_REQUESTS[user_id])>=5:
        return False, 60-int(now-USER_REQUESTS[user_id][0])
    USER_REQUESTS[user_id].append(now)
    return True, 0

async def process_tiktok(update:Update, context, url:str):
    global LIVE_DOWNLOADS, STATS
    user_id=update.effective_user.id
    # DB user
    try:
        lang=get_user_lang(update.effective_user)
        db_query("INSERT OR IGNORE INTO users (user_id, lang, joined_at) VALUES (?,?,?)", (user_id, lang, datetime.now().isoformat()))
    except: pass

    # Anti-spam check
    ok, wait_sec=check_antispam(user_id)
    if not ok:
        return await update.message.reply_text(t(user_id, "error_limit", sec=wait_sec))

    # Feature #1 Cache check
    h=url_hash(url)
    try:
        conn=sqlite3.connect(DB_FILE); c=conn.cursor()
        c.execute("SELECT file_id, title, author FROM cache WHERE url_hash=?", (h,)); row=c.fetchone(); conn.close()
        if row and row[0]:
            file_id, title, author=row
            info={'title':title,'author':author,'duration':0,'thumb':None,'url':url}
            caption=beautiful_caption(info, 0, 0.1, update.effective_user.first_name or "Friend", cached=True)
            short_id=str(uuid.uuid4())[:8]; URL_STORE[short_id]=info
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")]])
            try:
                sent=await update.message.reply_video(video=file_id, caption=caption, reply_markup=kb, parse_mode=ParseMode.HTML)
                db_query("INSERT INTO history (user_id, url, title, size, created_at) VALUES (?,?,?,?,?)", (user_id, url, title, 0, datetime.now().isoformat()))
                context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id})
                return
            except: pass
    except Exception as e: logger.error(f"Cache check {e}")

    # Queue system
    if DOWNLOAD_SEM.locked():
        pos=len(QUEUE_DEQUE)+1
        QUEUE_DEQUE.append(user_id)
        q_msg=await update.message.reply_text(t(user_id, "queue", pos=pos, wait=pos*15))
    else:
        q_msg=None

    async with DOWNLOAD_SEM:
        try:
            if q_msg:
                try: QUEUE_DEQUE.remove(user_id)
                except: pass
                try: await q_msg.delete()
                except: pass
        except: pass
        LIVE_DOWNLOADS+=1
        t0=datetime.now()
        tmpdir=tempfile.mkdtemp()
        m=await update.message.reply_text("🚀 <b>MAX DOWNLOADER</b>\n"+progress_bar(0), parse_mode=ParseMode.HTML)
        progress_data_global["pct"]=0
        stop_updating=False
        try:
            info=await asyncio.to_thread(get_tiktok_info, url, tmpdir)
            async def realtime_updater():
                last_pct=-1
                while not stop_updating:
                    pct=progress_data_global.get("pct",0)
                    speed=progress_data_global.get("speed","")
                    eta=progress_data_global.get("eta","")
                    down=progress_data_global.get("downloaded","")
                    total=progress_data_global.get("total","")
                    if abs(pct-last_pct)>=1 or pct==0:
                        bar=progress_bar(pct)
                        try:
                            await m.edit_text(f"🚀 <b>MAX DOWNLOADER</b> 🚀\n━━━━━━━━━━━━━━━\n🎬 {info['duration']}s video\n{bar}\n📦 {down} / {total}\n⚡ {speed} | ⏰ {eta}\n🔴 Live: {LIVE_DOWNLOADS}", parse_mode=ParseMode.HTML)
                            last_pct=pct
                        except: pass
                    await asyncio.sleep(0.8)
            updater_task=asyncio.create_task(realtime_updater())
            await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
            path=await asyncio.to_thread(download_with_retry, url, tmpdir, False)
            stop_updating=True
            try: await updater_task
            except: pass
            size_mb=os.path.getsize(path)/(1024*1024)
            elapsed=(datetime.now()-t0).total_seconds()
            STATS['total']+=1; STATS['total_size']+=size_mb
            try: STATS['users'].add(user_id)
            except: pass
            save_stats({"total":STATS['total'],"total_size":STATS['total_size'],"users":list(STATS['users']) if isinstance(STATS['users'], set) else STATS['users']})
            short_id=str(uuid.uuid4())[:8]; URL_STORE[short_id]=info
            user_name=update.effective_user.first_name or "Friend"
            caption=beautiful_caption(info, size_mb, elapsed, user_name)
            await m.edit_text(f"🚀 <b>MAX DOWNLOADER</b>\n{progress_bar(100)}\n✅ Done! Uploading...", parse_mode=ParseMode.HTML)
            if size_mb > MAX_SIZE_MB:
                await m.edit_text(f"📦 {size_mb:.1f}MB Large - Uploading to cloud... 🚀", parse_mode=ParseMode.HTML)
                link, service = await asyncio.to_thread(upload_large_file_real, path)
                if link:
                    kb=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"📦 Catbox Full Quality • {size_mb:.1f}MB 🚀", url=link)],
                        [InlineKeyboardButton(f"❤️ Favorite", callback_data=f"fav_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")],
                    ])
                    sent=await update.message.reply_text(caption+f"\n\n☁️ <b>{service}</b>\n🔗 <code>{html.escape(link)}</code>", reply_markup=kb, parse_mode=ParseMode.HTML)
                    context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id})
                try: await m.delete()
                except: pass
                return
            kb=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 HD 1080p 💎", callback_data=f"hd_{short_id}")],
                [InlineKeyboardButton("📱 Original", callback_data=f"orig_{short_id}"), InlineKeyboardButton("💧 Watermark ✨", callback_data=f"wm_{short_id}")],
                [InlineKeyboardButton("🎵 MP3 Audio 🎧", callback_data=f"mp3_{short_id}"), InlineKeyboardButton("❤️ Favorite", callback_data=f"fav_{short_id}")],
                [InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")],
            ])
            thumb_file = open(info['thumb'],'rb') if info['thumb'] and os.path.exists(info['thumb']) else None
            with open(path,'rb') as vf:
                sent=await update.message.reply_video(video=vf, thumbnail=thumb_file, caption=caption, supports_streaming=True, reply_markup=kb, parse_mode=ParseMode.HTML, read_timeout=180, write_timeout=180)
            if thumb_file: thumb_file.close()
            # Save to cache & history (Feature 1,5)
            try:
                file_id=sent.video.file_id
                db_query("INSERT OR REPLACE INTO cache (url_hash, url, file_id, size, title, author, created_at) VALUES (?,?,?,?,?,?,?)", (h, url, file_id, size_mb, info['title'], info['author'], datetime.now().isoformat()))
                db_query("INSERT INTO history (user_id, url, title, size, created_at) VALUES (?,?,?,?,?)", (user_id, url, info['title'], size_mb, datetime.now().isoformat()))
                db_query("UPDATE users SET total_downloads=total_downloads+1 WHERE user_id=?", (user_id,))
            except Exception as e: logger.error(f"DB save {e}")
            try: await m.delete()
            except: pass
            context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id})
        except Exception as e:
            stop_updating=True
            err=str(e).lower()
            logger.error(f"Process {e}", exc_info=True)
            # Feature #7 Better Errors
            if "private_video" in err or "private" in err or "deleted" in err:
                msg=t(user_id, "error_private")
            elif "403" in err or "blocked" in err or "region" in err:
                msg=t(user_id, "error_region")
            else:
                msg=f"❌ Error: {html.escape(str(e)[:200])}\n\nTry again or different link"
            try: await m.edit_text(msg, parse_mode=ParseMode.HTML)
            except: pass
        finally:
            LIVE_DOWNLOADS-=1
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

async def button_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data=q.data
    user_id=update.effective_user.id
    if data.startswith("del_"):
        try: await q.message.delete()
        except: pass
        return
    if data.startswith("fav_"):
        sid=data.split("_",1)[1]
        info=URL_STORE.get(sid)
        if info:
            try:
                db_query("INSERT OR IGNORE INTO favorites (user_id, url, title, created_at) VALUES (?,?,?,?)", (user_id, info['url'], info['title'], datetime.now().isoformat()))
                await q.message.reply_text(t(user_id, "fav_added"))
            except: await q.message.reply_text("❤️ Already in favorites")
        return
    try:
        action, sid = data.split("_",1)
        info=URL_STORE.get(sid)
        if not info: return await q.message.reply_text("Expired")
        tmpdir=tempfile.mkdtemp()
        m=await q.message.reply_text(f"🚀 <b>MAX DOWNLOADER</b> {action.upper()}\n"+progress_bar(0), parse_mode=ParseMode.HTML)
        progress_data_global["pct"]=0
        stop_updating=False
        async def realtime_updater_btn():
            last_pct=-1
            while not stop_updating:
                pct=progress_data_global.get("pct",0)
                if abs(pct-last_pct)>=1:
                    try: await m.edit_text(f"🚀 <b>MAX DOWNLOADER</b> {action.upper()}\n{progress_bar(pct)}\n⚡ {progress_data_global.get('speed','')}", parse_mode=ParseMode.HTML)
                    except: pass
                    last_pct=pct
                await asyncio.sleep(0.8)
        updater_task=asyncio.create_task(realtime_updater_btn())
        try:
            if action=="mp3":
                await q.message.chat.send_action(ChatAction.UPLOAD_VOICE)
                mp3_path=await asyncio.to_thread(download_mp3_fixed, info['url'], tmpdir)
                stop_updating=True
                try: await updater_task
                except: pass
                await m.edit_text("🎵 Uploading MP3...\n"+progress_bar(95), parse_mode=ParseMode.HTML)
                with open(mp3_path,'rb') as af:
                    await q.message.reply_audio(audio=af, title=info['title'][:60], performer="Max Downloader")
                await m.delete()
                return
            await q.message.chat.send_action(ChatAction.UPLOAD_VIDEO)
            is_wm=(action=="wm")
            path=await asyncio.to_thread(download_with_retry, info['url'], tmpdir, is_wm)
            stop_updating=True
            try: await updater_task
            except: pass
            size_mb=os.path.getsize(path)/(1024*1024)
            if size_mb>MAX_SIZE_MB:
                await m.edit_text(f"📦 {size_mb:.1f}MB Uploading...\n"+progress_bar(80), parse_mode=ParseMode.HTML)
                link, service=await asyncio.to_thread(upload_large_file_real, path)
                if link:
                    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Catbox Full Quality • {size_mb:.1f}MB 🚀", url=link)]])
                    await q.message.reply_text(f"📦 FULL {size_mb:.1f}MB • {service}\n{link}", reply_markup=kb)
                    await m.delete()
                    return
            await m.edit_text("⬆️ Uploading...\n"+progress_bar(95), parse_mode=ParseMode.HTML)
            tag="💧 Watermark" if is_wm else "💎 FULL HD"
            with open(path,'rb') as vf:
                await q.message.reply_video(video=vf, caption=f"🚀 <b>MAX DOWNLOADER</b> • {tag} • {size_mb:.1f}MB", supports_streaming=True, parse_mode=ParseMode.HTML)
            await m.delete()
        finally:
            stop_updating=True
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Button {e}", exc_info=True)
        try: await q.message.reply_text(f"❌ {html.escape(str(e)[:300])}", parse_mode=ParseMode.HTML)
        except: pass

async def start_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_id=update.effective_user.id
    lang=get_user_lang(update.effective_user)
    try: db_query("INSERT OR IGNORE INTO users (user_id, lang, joined_at) VALUES (?,?,?)", (user_id, lang, datetime.now().isoformat()))
    except: pass
    total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
    webapp_btn=InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Web App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📜 History", callback_data="show_history"), InlineKeyboardButton("❤️ Favorites", callback_data="show_fav")],
        [InlineKeyboardButton("📊 Stats", callback_data="show_stats_btn")]
    ])
    await update.message.reply_text(t(user_id, "welcome", lang=lang)+f"\n━━━━━━━━━━━━━━━\n📊 {STATS['total']} | 👥 {total_users} | 🔴 {LIVE_DOWNLOADS} live\n💾 Cache: instant repeat\n📦 1GB Large File ✅\n⚡ Real-Time 0-100%", reply_markup=webapp_btn, parse_mode=ParseMode.HTML)

async def history_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_id=update.effective_user.id
    rows=db_query("SELECT title, created_at FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,), fetch=True)
    if not rows: return await update.message.reply_text("📜 No history yet")
    txt=f"📜 <b>{t(user_id,'history')}</b> (last 10):\n━━━━━━━━━━━━━━━\n"
    for r in rows: txt+=f"• {html.escape(r[0][:30])} - {r[1][:10]}\n"
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def fav_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user_id=update.effective_user.id
    rows=db_query("SELECT title, url FROM favorites WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,), fetch=True)
    if not rows: return await update.message.reply_text("❤️ No favorites yet - tap ❤️ Favorite button")
    txt=f"❤️ <b>{t(user_id,'fav_list')}</b>:\n━━━━━━━━━━━━━━━\n"
    for title, url in rows: txt+=f"• {html.escape(title[:30])}\n<code>{html.escape(url[:40])}</code>\n\n"
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_panel(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id!=ADMIN_ID: return await update.message.reply_text("Not admin")
    rows=db_query("SELECT COUNT(*), SUM(size) FROM cache", fetch=True)
    cache_count=rows[0][0] if rows else 0
    await update.message.reply_text(f"🔐 <b>MAX DOWNLOADER ADMIN PRO</b>\nTotal: {STATS['total']}\nCache: {cache_count} videos (instant)\nQueue: {len(QUEUE_DEQUE)} waiting\nLive: {LIVE_DOWNLOADS}/3\nLogo: {os.path.exists(LOGO_PATH)}\nDB: SQLite + Cache\nLanguages: EN, AR, HI, RU\n\n/broadcast <msg>\n/stats\n/history\n/favorites\n/cache_clear", parse_mode=ParseMode.HTML)

async def stats_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    rows=db_query("SELECT COUNT(*) FROM users", fetch=True)
    users=rows[0][0] if rows else len(STATS['users'])
    rows2=db_query("SELECT COUNT(*) FROM cache", fetch=True)
    cache=rows2[0][0] if rows2 else 0
    await update.message.reply_text(f"📊 <b>MAX DOWNLOADER STATS PRO</b>\nTotal: {STATS['total']}\nUsers: {users}\nCache: {cache} (instant)\nLive: {LIVE_DOWNLOADS}/3\nQueue: {len(QUEUE_DEQUE)}\nServed: {STATS['total_size']/1024:.2f} GB\nLanguages: 4\nDB: SQLite", parse_mode=ParseMode.HTML)

async def broadcast_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id!=ADMIN_ID: return
    if not context.args: return await update.message.reply_text("Usage: /broadcast Hello users!")
    msg=" ".join(context.args)
    rows=db_query("SELECT user_id FROM users", fetch=True)
    sent=0
    for (uid,) in rows:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 <b>Announcement</b>\n\n{msg}", parse_mode=ParseMode.HTML)
            sent+=1
            await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(t(update.effective_user.id, "broadcast_done", n=sent))

async def cache_clear_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id!=ADMIN_ID: return
    db_query("DELETE FROM cache")
    await update.message.reply_text("✅ Cache cleared")

async def inline_mode(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query=update.inline_query.query
    if not query: return
    results=[InlineQueryResultArticle(id=uuid.uuid4().hex, title="🚀 Max Downloader - FULL HD", description="Premium", input_message_content=InputTextMessageContent(f"🎬 {query}\nDownload via @{BOT_USERNAME}"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Max Downloader 🚀", url=f"https://t.me/{BOT_USERNAME.replace('@','')}")]]))]
    await update.inline_query.answer(results, cache_time=1)

async def handle(update:Update, context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text or ""
    if text.startswith("/"): return
    urls=re.findall(r'https?://\S+', text)
    if not urls:
        urls=re.findall(r'tiktok\.com/\S+|vm\.tiktok\.com/\S+|vt\.tiktok\.com/\S+', text)
        urls=['https://'+u if not u.startswith('http') else u for u in urls]
    if not urls: return
    for u in urls[:3]: await process_tiktok(update, context, u)

async def extra_callback(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    if q.data=="show_history":
        await q.answer()
        user_id=q.from_user.id
        rows=db_query("SELECT title FROM history WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,), fetch=True)
        txt="📜 History:\n"+"\n".join([f"• {r[0][:30]}" for r in rows]) if rows else "No history"
        await q.message.reply_text(txt)
    elif q.data=="show_fav":
        await q.answer()
        user_id=q.from_user.id
        rows=db_query("SELECT title FROM favorites WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,), fetch=True)
        txt="❤️ Favorites:\n"+"\n".join([f"• {r[0][:30]}" for r in rows]) if rows else "No fav"
        await q.message.reply_text(txt)
    elif q.data=="show_stats_btn":
        await q.answer()
        await stats_cmd(update, context)
    else:
        await button_handler(update, context)

def main():
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
    except: pass
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("favorites", fav_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("cache_clear", cache_clear_cmd))
    app.add_handler(CallbackQueryHandler(extra_callback))
    app.add_handler(InlineQueryHandler(inline_mode))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    logger.info(f"MAX DOWNLOADER PRO Running - Cache+Queue+DB+History+Fav+Proxy+Lang+WebApp")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
