import os, re, json, uuid, asyncio, tempfile, requests, threading, subprocess, logging, html, time
from datetime import datetime
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction, ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Max Downloader Alive")
    def log_message(self,*a): pass
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.getenv("PORT",10000))), HealthHandler).serve_forever(), daemon=True).start()

load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")
ADMIN_ID=int(os.getenv("ADMIN_ID","0"))
MAX_SIZE_MB=int(os.getenv("MAX_TELEGRAM_SIZE_MB","50"))
AUTO_DELETE_MIN=int(os.getenv("AUTO_DELETE_MIN","10"))
BOT_USERNAME=os.getenv("BOT_USERNAME","@YourBot")
LOGO_PATH="TIKTOKLOGO.png"

if not BOT_TOKEN: raise ValueError("BOT_TOKEN missing")

STATS_FILE="stats.json"
URL_STORE={}
LIVE_DOWNLOADS=0
progress_data_global={"pct":0,"speed":"","eta":"","downloaded":"","total":""}

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

def beautiful_caption(info, size, elapsed, user_name):
    safe_title=html.escape(info['title'][:45])
    safe_author=html.escape(info['author'][:20])
    return (
        f"🚀 <b>MAX DOWNLOADER</b> 🚀\n"
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
    logger.info(f"Large upload {size_mb:.1f}MB")
    if size_mb > 100:
        try:
            with open(fp,'rb') as f:
                r=requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype":"fileupload","time":"72h"}, files={"fileToUpload":(os.path.basename(fp), f, "video/mp4")}, timeout=600)
            logger.info(f"Litterbox {r.status_code} {r.text[:120]}")
            if r.status_code==200 and "http" in r.text: return r.text.strip(), "Litterbox 1GB 72h"
        except Exception as e: logger.error(f"Litterbox {e}")
    if size_mb < 200:
        try:
            with open(fp,'rb') as f:
                r=requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload":f}, timeout=600)
            if r.status_code==200 and "http" in r.text: return r.text.strip(), "Catbox.moe"
        except Exception as e: logger.error(f"Catbox {e}")
    try:
        r=requests.get("https://api.gofile.io/servers", timeout=20)
        server=r.json()['data']['servers'][0]['name']
        with open(fp,'rb') as f:
            r=requests.post(f"https://{server}.gofile.io/uploadFile", files={"file":f}, timeout=600)
        j=r.json()
        if j['status']=='ok': return j['data']['downloadPage'], "GoFile 10GB"
    except Exception as e: logger.error(f"GoFile {e}")
    return None, None

def add_watermark_fixed(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1:v]scale=iw*0.18:-1[wm];[0:v][wm]overlay=W-w-20:H-h-20:format=auto,format=yuv420p","-c:a","copy","-movflags","+faststart",output_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if os.path.exists(output_path) and os.path.getsize(output_path)>10000: return output_path
    except Exception as e: logger.error(f"WM {e}")
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
                pct_str=d.get('_percent_str','0%').replace('%','').strip()
                pct=float(pct_str)
                progress_data_global["pct"]=pct
                progress_data_global["speed"]=d.get('_speed_str','').strip()
                progress_data_global["eta"]=d.get('_eta_str','').strip()
                progress_data_global["downloaded"]=d.get('_downloaded_bytes_str','').strip()
                progress_data_global["total"]=d.get('_total_bytes_str','').strip()
            except: pass
    return hook

def download_video_sync_max_realtime(url, tmpdir, watermark=False):
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
    except:
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
        j=r.json(); d=j['data']
        vurl=d.get('hdplay') or d.get('play')
        fp2=os.path.join(tmpdir, f"tikwm_{uuid.uuid4().hex}.mp4")
        with requests.get(vurl, stream=True, timeout=600) as r2:
            total=int(r2.headers.get('content-length',0))
            downloaded=0
            with open(fp2,'wb') as f:
                for chunk in r2.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        downloaded+=len(chunk)
                        if total>0:
                            pct=downloaded/total*100
                            progress_data_global["pct"]=pct
                            progress_data_global["downloaded"]=f"{downloaded/1024/1024:.1f}MB"
                            progress_data_global["total"]=f"{total/1024/1024:.1f}MB"
        if watermark:
            out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp2=add_watermark_fixed(fp2, LOGO_PATH, out)
        return fp2

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

async def process_tiktok(update:Update, context, url:str):
    global LIVE_DOWNLOADS, STATS
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
                        await m.edit_text(
                            f"🚀 <b>MAX DOWNLOADER</b> 🚀\n"
                            f"━━━━━━━━━━━━━━━\n"
                            f"🎬 {info['duration']}s video\n"
                            f"{bar}\n"
                            f"📦 {down} / {total}\n"
                            f"⚡ {speed} | ⏰ {eta}\n"
                            f"🔴 Live: {LIVE_DOWNLOADS}",
                            parse_mode=ParseMode.HTML
                        )
                        last_pct=pct
                    except: pass
                await asyncio.sleep(0.8)
        updater_task=asyncio.create_task(realtime_updater())
        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        path=await asyncio.to_thread(download_video_sync_max_realtime, url, tmpdir, False)
        stop_updating=True
        try: await updater_task
        except: pass
        size_mb=os.path.getsize(path)/(1024*1024)
        elapsed=(datetime.now()-t0).total_seconds()
        STATS['total']+=1
        STATS['total_size']+=size_mb
        try: STATS['users'].add(update.effective_user.id)
        except: pass
        save_stats({"total":STATS['total'],"total_size":STATS['total_size'],"users":list(STATS['users']) if isinstance(STATS['users'], set) else STATS['users']})
        short_id=str(uuid.uuid4())[:8]
        URL_STORE[short_id]=info
        user_name=update.effective_user.first_name or "Friend"
        caption=beautiful_caption(info, size_mb, elapsed, user_name)
        await m.edit_text(f"🚀 <b>MAX DOWNLOADER</b>\n{progress_bar(100)}\n✅ Done! Uploading to Telegram...", parse_mode=ParseMode.HTML)
        if size_mb > MAX_SIZE_MB:
            await m.edit_text(f"📦 {size_mb:.1f}MB Large - Uploading to cloud... 🚀", parse_mode=ParseMode.HTML)
            link, service = await asyncio.to_thread(upload_large_file_real, path)
            if link:
                kb=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"📦 Catbox Full Quality • {size_mb:.1f}MB 🚀", url=link)],
                    [InlineKeyboardButton(f"⬇️ Download Full HD • Max Downloader 💎", url=link)],
                ])
                sent=await update.message.reply_text(caption+f"\n\n☁️ <b>{service}</b>\n🔗 <code>{html.escape(link)}</code>", reply_markup=kb, parse_mode=ParseMode.HTML)
                context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id})
            try: await m.delete()
            except: pass
            return
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 HD 1080p 💎", callback_data=f"hd_{short_id}")],
            [InlineKeyboardButton("📱 Original", callback_data=f"orig_{short_id}"), InlineKeyboardButton("💧 Watermark ✨", callback_data=f"wm_{short_id}")],
            [InlineKeyboardButton("🎵 MP3 Audio 🎧", callback_data=f"mp3_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")],
        ])
        thumb_file = open(info['thumb'],'rb') if info['thumb'] and os.path.exists(info['thumb']) else None
        with open(path,'rb') as vf:
            sent=await update.message.reply_video(video=vf, thumbnail=thumb_file, caption=caption, supports_streaming=True, reply_markup=kb, parse_mode=ParseMode.HTML, read_timeout=180, write_timeout=180)
        if thumb_file: thumb_file.close()
        try: await m.delete()
        except: pass
        context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id})
    except Exception as e:
        logger.error(f"Process {e}", exc_info=True)
        try: await m.edit_text(f"❌ {html.escape(str(e)[:200])}", parse_mode=ParseMode.HTML)
        except: pass
    finally:
        LIVE_DOWNLOADS-=1
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

async def button_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    data=q.data
    if data.startswith("del_"):
        try: await q.message.delete()
        except: pass
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
            path=await asyncio.to_thread(download_video_sync_max_realtime, info['url'], tmpdir, is_wm)
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
    total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
    await update.message.reply_text(f"🚀 <b>MAX DOWNLOADER</b> 🚀\n━━━━━━━━━━━━━━━\n💎 1080p Full Quality\n📦 Large File 1GB Fixed ✅\n💧 Watermark {LOGO_PATH}\n🎵 MP3 Fixed\n⚡ Real-Time Progress 0-100%\n━━━━━━━━━━━━━━━\n📊 {STATS['total']} | 👥 {total_users} | 🔴 {LIVE_DOWNLOADS} live\nSend TikTok link ✨", parse_mode=ParseMode.HTML)

async def admin_panel(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id!=ADMIN_ID: return await update.message.reply_text("Not admin")
    total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
    await update.message.reply_text(f"🔐 <b>MAX DOWNLOADER ADMIN</b>\nTotal: {STATS['total']}\nUsers: {total_users}\nLive: {LIVE_DOWNLOADS}\nSize: {STATS['total_size']/1024:.2f}GB\nLogo: {os.path.exists(LOGO_PATH)}\nAuto-delete: {AUTO_DELETE_MIN}min", parse_mode=ParseMode.HTML)

async def stats_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
    await update.message.reply_text(f"📊 <b>MAX DOWNLOADER STATS</b>\nTotal: {STATS['total']}\nUsers: {total_users}\nLive: {LIVE_DOWNLOADS}\nServed: {STATS['total_size']/1024:.2f} GB", parse_mode=ParseMode.HTML)

async def inline_mode(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query=update.inline_query.query
    if not query: return
    results=[InlineQueryResultArticle(id=uuid.uuid4().hex, title="🚀 Max Downloader - FULL HD", description="Premium", input_message_content=InputTextMessageContent(f"🎬 {query}\nDownload via @{BOT_USERNAME}"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Max Downloader 🚀", url=f"https://t.me/{BOT_USERNAME.replace('@','')}")]]))]
    await update.inline_query.answer(results, cache_time=1)

async def handle(update:Update, context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text or ""
    urls=re.findall(r'https?://\S+', text)
    if not urls:
        urls=re.findall(r'tiktok\.com/\S+|vm\.tiktok\.com/\S+|vt\.tiktok\.com/\S+', text)
        urls=['https://'+u if not u.startswith('http') else u for u in urls]
    if not urls: return
    for u in urls[:3]: await process_tiktok(update, context, u)

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
    logger.info(f"MAX DOWNLOADER Running - Logo:{os.path.exists(LOGO_PATH)}")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
