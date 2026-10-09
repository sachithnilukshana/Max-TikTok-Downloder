import os, re, json, uuid, asyncio, tempfile, requests, threading, subprocess, logging
from datetime import datetime
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction, ParseMode

# ===== LOGGING PRODUCTION =====
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-type','text/plain'); self.end_headers()
        self.wfile.write(b"Ultimate Bot Alive")
    def log_message(self,*a): pass
def run_web():
    try: HTTPServer(('0.0.0.0', int(os.getenv("PORT",10000))), HealthHandler).serve_forever()
    except: pass
threading.Thread(target=run_web, daemon=True).start()

load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")
ADMIN_ID=int(os.getenv("ADMIN_ID","0"))
MAX_SIZE_MB=int(os.getenv("MAX_TELEGRAM_SIZE_MB","50"))
AUTO_DELETE_MIN=int(os.getenv("AUTO_DELETE_MIN","10"))
BOT_USERNAME=os.getenv("BOT_USERNAME","@YourBot")
LOGO_PATH="TIKTOKLOGO.png"

if not BOT_TOKEN: raise ValueError("BOT_TOKEN missing")

# ===== LIVE STATS COUNTER =====
STATS_FILE="stats.json"
URL_STORE={}
LIVE_DOWNLOADS=0
def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE,'r') as f: return json.load(f)
    except: pass
    return {"total":0,"total_size":0,"users":set(),"today":0,"last_reset":str(datetime.now().date())}
def save_stats(s):
    try:
        data=s.copy()
        data['users']=list(data['users']) if isinstance(data['users'], set) else data['users']
        with open(STATS_FILE,'w') as f: json.dump(data,f)
    except: pass

STATS=load_stats()
if isinstance(STATS.get('users'), list): STATS['users']=set(STATS['users'])

# ===== BEAUTIFUL BOX UI =====
def beautiful_box(author, duration, size, elapsed, title):
    return (
        f"╔═══════════════════════╗\n"
        f"║ ✨ 𝗧𝗜𝗞𝗧𝗢𝗞 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗘𝗥 ✨ ║\n"
        f"╠═══════════════════════╣\n"
        f"║ 👤 @{author[:18]:<18} ║\n"
        f"║ ⏱️ {duration}s | 📦 {size:.1f}MB{'':<6} ║\n"
        f"║ ⚡ {elapsed:.1f}s | 💎 FULL QUALITY ║\n"
        f"╠═══════════════════════╣\n"
        f"║ 📝 {title[:21]:<21} ║\n"
        f"╚═══════════════════════╝"
    )

# ===== LARGE FILE FIX - 456MB =====
def upload_large_file(fp):
    size_mb=os.path.getsize(fp)/(1024*1024)
    logger.info(f"Uploading large {size_mb:.1f}MB")
    # 1. CATBOX <200MB
    if size_mb < 200:
        try:
            with open(fp,'rb') as f:
                r=requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload":f}, timeout=600)
            if r.status_code==200 and "catbox" in r.text and "http" in r.text:
                return r.text.strip(), "Catbox.moe"
        except Exception as e: logger.error(f"Catbox {e}")

    # 2. LITTERBOX 1GB - FIX FOR YOUR 456.9MB
    try:
        logger.info("Trying Litterbox 1GB for 456MB")
        with open(fp,'rb') as f:
            r=requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype":"fileupload","time":"72h"}, files={"fileToUpload":f}, timeout=600)
        if r.status_code==200 and "litter" in r.text.lower() and "http" in r.text:
            return r.text.strip(), "Litterbox 1GB 72h"
    except Exception as e: logger.error(f"Litterbox {e}")

    # 3. GOFILE 10GB
    try:
        logger.info("Trying GoFile 10GB")
        r=requests.get("https://api.gofile.io/servers", timeout=20)
        server=r.json()['data']['servers'][0]['name']
        with open(fp,'rb') as f:
            r=requests.post(f"https://{server}.gofile.io/uploadFile", files={"file":f}, timeout=600)
        j=r.json()
        if j['status']=='ok':
            return j['data']['downloadPage'], "GoFile 10GB"
    except Exception as e: logger.error(f"GoFile {e}")

    return None, None

def add_watermark(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1][0]scale2ref=w=iw*0.18:h=ow/mdar[wm][vid];[vid][wm]overlay=W-w-20:20:enable='gte(t,1)'","-codec:a","copy","-movflags","+faststart",output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40)
        if os.path.exists(output_path) and os.path.getsize(output_path)>10000: return output_path
    except Exception as e: logger.error(f"Watermark {e}")
    return video_path

def get_tiktok_info(url, tmpdir):
    import yt_dlp
    # Fast info via tikwm
    try:
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        j=r.json()
        if j.get('code')==0:
            d=j['data']
            cover_url=d.get('cover') or d.get('ai_dynamic_cover')
            thumb_path=None
            if cover_url:
                thumb_path=os.path.join(tmpdir, "thumb.jpg")
                try:
                    with requests.get(cover_url, timeout=15) as cr:
                        with open(thumb_path,'wb') as f: f.write(cr.content)
                except: thumb_path=None
            return {
                'title':d.get('title','')[:80],'author':d.get('author',{}).get('unique_id','tiktok'),
                'nickname':d.get('author',{}).get('nickname',''),'duration':d.get('duration',0),
                'thumb':thumb_path,'data':d,'url':url
            }
    except: pass

    ydl_opts={'quiet':True,'skip_download':True,'no_warnings':True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        i=ydl.extract_info(url, download=False)
        return {'title':i.get('title','')[:80],'author':i.get('uploader','tiktok'),'nickname':i.get('uploader',''),'duration':i.get('duration',0),'thumb':None,'data':i,'url':url}

def download_video_sync(url, tmpdir, quality="hd", watermark=False):
    import yt_dlp
    fp=os.path.join(tmpdir, f"{uuid.uuid4().hex}.mp4")
    try:
        ydl_opts={
            'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl':fp,'merge_output_format':'mp4','concurrent_fragment_downloads':16,
            'quiet':True,'no_warnings':True,'noplaylist':True,'nocheckcertificate':True,
            'extractor_args':{'tiktok':{'api_hostname':['api16-normal-c-useast1a.tiktokv.com']}},
            'external_downloader_args':{'ffmpeg':['-threads','8']},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if not os.path.exists(fp):
            for f in os.listdir(tmpdir):
                if f.endswith('.mp4'): fp=os.path.join(tmpdir,f); break
        if watermark and os.path.exists(LOGO_PATH):
            out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp=add_watermark(fp, LOGO_PATH, out)
        return fp
    except Exception as e:
        logger.error(f"yt-dlp fail {e}")
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
        j=r.json(); d=j['data']
        vurl=d.get('hdplay') if quality=="hd" else d.get('play')
        vurl=vurl or d.get('play')
        fp2=os.path.join(tmpdir, f"tikwm_{uuid.uuid4().hex}.mp4")
        with requests.Session() as s:
            s.headers.update({'User-Agent':'Mozilla/5.0','Referer':'https://www.tikwm.com/'})
            with s.get(vurl, stream=True, timeout=600) as r2:
                with open(fp2,'wb') as f:
                    for chunk in r2.iter_content(chunk_size=1024*1024*4):
                        if chunk: f.write(chunk)
        if watermark and os.path.exists(LOGO_PATH):
            out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp2=add_watermark(fp2, LOGO_PATH, out)
        return fp2

# ===== AUTO-DELETE JOB =====
async def delete_after(context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id=context.job.data['chat_id']
        msg_id=context.job.data['msg_id']
        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        logger.info(f"Auto-deleted {msg_id} after {AUTO_DELETE_MIN}min")
    except: pass

# ===== PROCESS WITH EFFECTS =====
async def process_tiktok(update:Update, context, url:str):
    global LIVE_DOWNLOADS, STATS
    LIVE_DOWNLOADS+=1
    t0=datetime.now()
    tmpdir=tempfile.mkdtemp()
    # STICKER ANIMATION EFFECT
    try:
        sticker_msg=await update.message.reply_text("🎬")
        await asyncio.sleep(0.3)
        try: await sticker_msg.delete()
        except: pass
    except: pass

    # DOWNLOAD EFFECT ANIMATION
    m=await update.message.reply_text("⏳ Analyzing...")
    try:
        for i, txt in enumerate(["⏳ Analyzing...","🔍 Fetching info...","⚡ Downloading FULL..."]):
            try: await m.edit_text(txt); await asyncio.sleep(0.4)
            except: pass

        await update.effective_chat.send_action(ChatAction.TYPING)
        info=await asyncio.to_thread(get_tiktok_info, url, tmpdir)

        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        await m.edit_text(f"⚡ Downloading {info['duration']}s FULL...\n🔴 Live: {LIVE_DOWNLOADS} downloading")

        path=await asyncio.to_thread(download_video_sync, url, tmpdir, "hd", False)
        size_mb=os.path.getsize(path)/(1024*1024)
        elapsed=(datetime.now()-t0).total_seconds()

        # STATS
        STATS['total']+=1
        STATS['total_size']+=size_mb
        STATS['users'].add(update.effective_user.id)
        save_stats(STATS)

        short_id=str(uuid.uuid4())[:8]
        URL_STORE[short_id]=info

        # BEAUTIFUL BOX CAPTION
        caption=beautiful_box(info['author'], info['duration'], size_mb, elapsed, info['title'])

        # LARGE FILE >50MB - OPTION 2 BEAUTIFUL BUTTON
        if size_mb > MAX_SIZE_MB:
            await m.edit_text(f"📦 {size_mb:.1f}MB > {MAX_SIZE_MB}MB - Uploading to Cloud...\n🔴 Large file takes 30-60s")
            link, service = await asyncio.to_thread(upload_large_file, path)

            if link:
                # OPTION 2 BEAUTIFUL BUTTON
                kb=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"📦 Catbox Full Quality • {size_mb:.1f}MB 🚀", url=link)],
                    [InlineKeyboardButton(f"⬇️ Download Full HD", url=link)],
                    [InlineKeyboardButton("🎬 Get HD 1080p", callback_data=f"hd_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")]
                ])
                sent=await update.message.reply_text(
                    f"{caption}\n\n"
                    f"☁️ **Service:** {service}\n"
                    f"🔗 `{link}`\n\n"
                    f"⏰ Auto-delete in {AUTO_DELETE_MIN}min\n"
                    f"📊 Total Downloads: {STATS['total']}",
                    reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                )
                # AUTO-DELETE TIMER
                context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id}, name=f"del_{sent.message_id}")
            else:
                await update.message.reply_text(f"❌ Failed to upload {size_mb:.1f}MB - Litterbox/GoFile down. Try again.")
            await m.delete()
            return

        # SMALL FILE - SEND VIDEO WITH CUSTOM THUMBNAIL
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 HD 1080p 💎", callback_data=f"hd_{short_id}")],
            [InlineKeyboardButton("📱 Original", callback_data=f"orig_{short_id}"), InlineKeyboardButton(f"💧 Watermark {LOGO_PATH[:4]}", callback_data=f"wm_{short_id}")],
            [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")],
        ])

        # CHAT ACTIONS + THUMBNAIL
        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        thumb_file = open(info['thumb'],'rb') if info['thumb'] and os.path.exists(info['thumb']) else None

        with open(path,'rb') as vf:
            sent=await update.message.reply_video(
                video=vf, thumbnail=thumb_file, caption=caption,
                supports_streaming=True, reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN, read_timeout=180, write_timeout=180
            )
        if thumb_file: thumb_file.close()
        await m.delete()

        # AUTO-DELETE AFTER 10 MIN
        context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id}, name=f"del_{sent.message_id}")
        await update.message.reply_text(f"⏰ This video will auto-delete in {AUTO_DELETE_MIN} minutes", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Delete Now", callback_data=f"del_{short_id}")]]))

    except Exception as e:
        logger.error(f"Process error {e}", exc_info=True)
        try: await m.edit_text(f"❌ Error: {e}\nTry again")
        except: pass
    finally:
        LIVE_DOWNLOADS-=1
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

async def button_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if q.data.startswith("del_"):
        try: await q.message.delete()
        except: pass
        return
    try:
        action, sid = q.data.split("_",1)
        info=URL_STORE.get(sid)
        if not info: return await q.message.reply_text("❌ Expired - Send link again")
        tmpdir=tempfile.mkdtemp()
        m=await q.message.reply_text(f"⚡ Processing {action.upper()}...")
        try:
            await q.message.chat.send_action(ChatAction.UPLOAD_VIDEO if action!="mp3" else ChatAction.UPLOAD_VOICE)
            if action=="mp3":
                import yt_dlp
                fp=os.path.join(tmpdir, "audio.%(ext)s")
                opts={'outtmpl':fp,'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],'quiet':True}
                await asyncio.to_thread(lambda: yt_dlp.YoutubeDL(opts).download([info['url']]))
                for f in os.listdir(tmpdir):
                    if f.endswith('.mp3'):
                        with open(os.path.join(tmpdir,f),'rb') as af:
                            await q.message.reply_audio(audio=af, title=info['title'][:60])
                        break
                await m.delete()
                return
            path=await asyncio.to_thread(download_video_sync, info['url'], tmpdir, "hd" if action in ["hd","catbox"] else "orig", action=="wm")
            size_mb=os.path.getsize(path)/(1024*1024)
            if action=="catbox" or size_mb>MAX_SIZE_MB:
                await m.edit_text(f"📦 Uploading {size_mb:.1f}MB 🚀...")
                link, service=await asyncio.to_thread(upload_large_file, path)
                if link:
                    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Catbox Full Quality • {size_mb:.1f}MB 🚀", url=link)]])
                    await q.message.reply_text(f"📦 FULL {size_mb:.1f}MB • {service}\n🔗 {link}", reply_markup=kb)
                    await m.delete()
                    return
            with open(path,'rb') as vf:
                await q.message.reply_video(video=vf, caption=f"🎬 @{info['author']} • {size_mb:.1f}MB FULL", supports_streaming=True)
            await m.delete()
        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Button error {e}", exc_info=True)
        await q.message.reply_text(f"❌ {e}")

async def start_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"✨ **ULTIMATE TIKTOK BOT** ✨\n"
        f"╔═══════════════╗\n"
        f"║ ⚡ <10s FULL VIDEO ║\n"
        f"║ 📦 Catbox 1GB Support ║\n"
        f"║ 💧 Logo: {LOGO_PATH} ║\n"
        f"╚═══════════════╝\n\n"
        f"Send TikTok link\n"
        f"📊 Downloads: {STATS['total']} | 👥 Users: {len(STATS['users'])} | 🔴 Live: {LIVE_DOWNLOADS}",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_panel(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id!=ADMIN_ID:
        return await update.message.reply_text("❌ Not admin")
    await update.message.reply_text(
        f"🔐 **ADMIN PANEL**\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 Total Downloads: {STATS['total']}\n"
        f"👥 Total Users: {len(STATS['users'])}\n"
        f"💾 Total Size: {STATS['total_size']:.1f}MB\n"
        f"🔴 Live Downloads: {LIVE_DOWNLOADS}\n"
        f"📦 Max Size: {MAX_SIZE_MB}MB\n"
        f"⏰ Auto-delete: {AUTO_DELETE_MIN}min\n"
        f"💧 Logo exists: {os.path.exists(LOGO_PATH)}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Commands: /stats /clearstats",
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 **LIVE STATS**\n"
        f"Total: {STATS['total']} videos\n"
        f"Users: {len(STATS['users'])}\n"
        f"Live: {LIVE_DOWNLOADS} downloading now\n"
        f"Size served: {STATS['total_size']/1024:.2f} GB"
    )

async def inline_mode(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query=update.inline_query.query
    if not query: return
    if "tiktok.com" not in query:
        results=[InlineQueryResultArticle(id="1", title="Send TikTok link", input_message_content=InputTextMessageContent(f"Download TikTok: {query}"))]
    else:
        results=[InlineQueryResultArticle(id=uuid.uuid4().hex, title="Download TikTok FULL", description="Click to download", input_message_content=InputTextMessageContent(f"🎬 Downloading {query}\nSend this link to @{BOT_USERNAME} for full video"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download in Bot", url=f"https://t.me/{BOT_USERNAME.replace('@','')}?start={query}")]]))]
    await update.inline_query.answer(results, cache_time=1)

async def handle(update:Update, context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text or ""
    urls=re.findall(r'https?://\S+', text)
    if not urls:
        urls=re.findall(r'tiktok\.com/\S+|vm\.tiktok\.com/\S+|vt\.tiktok\.com/\S+', text)
        urls=['https://'+u if not u.startswith('http') else u for u in urls]
    if not urls: return
    for u in urls[:3]: await process_tiktok(update, context, u)

async def error_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error {context.error}", exc_info=True)
    try:
        if update and update.message:
            await update.message.reply_text(f"❌ Error logged. Admin notified.\n{context.error}")
    except: pass

def main():
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
    except: pass
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(InlineQueryHandler(inline_mode))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_error_handler(error_handler)
    logger.info(f"Ultimate Bot Running - Logo:{LOGO_PATH} Delete:{AUTO_DELETE_MIN}min")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
