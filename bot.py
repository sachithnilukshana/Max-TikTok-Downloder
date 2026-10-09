import os, re, json, uuid, asyncio, tempfile, requests, threading, subprocess, logging, html, random
from datetime import datetime
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction, ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Beautiful Bot Alive")
    def log_message(self,*a): pass
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.getenv("PORT",10000))), HealthHandler).serve_forever(), daemon=True).start()

load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")
ADMIN_ID=int(os.getenv("ADMIN_ID","0"))
MAX_SIZE_MB=int(os.getenv("MAX_TELEGRAM_SIZE_MB","50"))
AUTO_DELETE_MIN=int(os.getenv("AUTO_DELETE_MIN","10"))
BOT_USERNAME=os.getenv("BOT_USERNAME","@YourBot")
LOGO_PATH="TIKTOKLOGO.png"

STATS_FILE="stats.json"
URL_STORE={}
LIVE_DOWNLOADS=0

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

# ===== FANCY FONTS =====
def to_bold(text):
    # Bold sans for premium look
    normal="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold="𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    trans=str.maketrans(normal, bold)
    return text.translate(trans)

# ===== BEAUTIFUL PROGRESS BAR ANIMATION =====
def progress_bar(pct):
    filled=int(pct/10)
    bar="█"*filled + "░"*(10-filled)
    return f"{bar} {pct}%"

# ===== ULTRA BEAUTIFUL BOX =====
def beautiful_caption(info, size, elapsed, user_name):
    safe_title=html.escape(info['title'][:45])
    safe_author=html.escape(info['author'][:20])
    total=STATS['total']+1
    users=len(STATS['users'])

    # CYBERPUNK + LUXURY COMBINED
    return (
        f"🌌 <b>{to_bold('TIKTOK PREMIUM')}</b> 🌌\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Hey <b>{html.escape(user_name)}</b>! Your video ready ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┌─ 🎬 <b>Video Info</b> ─┐\n"
        f"│ 👤 <b>Creator:</b> @{safe_author}\n"
        f"│ 📝 <b>Title:</b> {safe_title}\n"
        f"│ ⏱ <b>Duration:</b> {info['duration']}s\n"
        f"│ 📦 <b>Size:</b> {size:.1f}MB | 💎 <b>1080p FULL</b>\n"
        f"│ ⚡ <b>Speed:</b> {elapsed:.1f}s\n"
        f"└───────────────┘\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Live Stats:</b> {total} downloads | {users} users | 🔴 {LIVE_DOWNLOADS} live\n"
        f"💎 <b>Full Quality • No Watermark • No Compression</b>\n"
        f"⏰ Auto-delete in {AUTO_DELETE_MIN}min | {BOT_USERNAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )

def upload_large_file(fp):
    size_mb=os.path.getsize(fp)/(1024*1024)
    if size_mb < 200:
        try:
            with open(fp,'rb') as f:
                r=requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload":f}, timeout=600)
            if r.status_code==200 and "http" in r.text: return r.text.strip(), "Catbox.moe"
        except: pass
    try:
        with open(fp,'rb') as f:
            r=requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={"reqtype":"fileupload","time":"72h"}, files={"fileToUpload":f}, timeout=600)
        if r.status_code==200 and "http" in r.text: return r.text.strip(), "Litterbox 1GB 72h"
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

def create_beautiful_thumbnail(thumb_path, logo_path):
    # Add logo overlay to thumbnail + blur premium look
    try:
        from PIL import Image, ImageFilter
        if not os.path.exists(thumb_path) or not os.path.exists(logo_path): return thumb_path
        base=Image.open(thumb_path).convert("RGBA")
        logo=Image.open(logo_path).convert("RGBA")
        # Resize logo 20%
        w=int(base.width*0.22)
        h=int(w*logo.height/logo.width)
        logo=logo.resize((w,h), Image.LANCZOS)
        # Position bottom-right
        base.paste(logo, (base.width-w-15, 15), logo)
        out=thumb_path.replace(".jpg","_beauty.jpg")
        base.convert("RGB").save(out, "JPEG", quality=90)
        return out
    except Exception as e:
        logger.error(f"Thumb beauty {e}")
        return thumb_path

def add_watermark(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1][0]scale2ref=w=iw*0.18:h=ow/mdar[wm][vid];[vid][wm]overlay=W-w-20:20:enable='gte(t,1)'","-codec:a","copy","-movflags","+faststart",output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40)
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

def download_video_sync(url, tmpdir, quality="hd", watermark=False):
    import yt_dlp
    fp=os.path.join(tmpdir, f"{uuid.uuid4().hex}.mp4")
    try:
        ydl_opts={'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best','outtmpl':fp,'merge_output_format':'mp4','concurrent_fragment_downloads':16,'quiet':True,'no_warnings':True,'noplaylist':True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if not os.path.exists(fp):
            for f in os.listdir(tmpdir):
                if f.endswith('.mp4'): fp=os.path.join(tmpdir,f); break
        if watermark and os.path.exists(LOGO_PATH):
            out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp=add_watermark(fp, LOGO_PATH, out)
        return fp
    except:
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
        j=r.json(); d=j['data']
        vurl=d.get('hdplay') or d.get('play')
        fp2=os.path.join(tmpdir, f"tikwm_{uuid.uuid4().hex}.mp4")
        with requests.get(vurl, stream=True, timeout=600) as r2:
            with open(fp2,'wb') as f:
                for chunk in r2.iter_content(chunk_size=1024*1024*4):
                    if chunk: f.write(chunk)
        if watermark and os.path.exists(LOGO_PATH):
            out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp2=add_watermark(fp2, LOGO_PATH, out)
        return fp2

async def delete_after(context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=context.job.data['chat_id'], message_id=context.job.data['msg_id'])
    except: pass

async def process_tiktok(update:Update, context, url:str):
    global LIVE_DOWNLOADS, STATS
    LIVE_DOWNLOADS+=1
    t0=datetime.now()
    tmpdir=tempfile.mkdtemp()
    m=await update.message.reply_text("🎬✨")
    try:
        # ANIMATED DOWNLOAD EFFECT
        animations=[
            "🎬 Analyzing link...",
            "🔍 Fetching info... "+progress_bar(20),
            "⚡ Connecting... "+progress_bar(40),
            "📥 Downloading FULL... "+progress_bar(70),
            "💎 Processing 1080p... "+progress_bar(90),
            "✨ Finalizing... "+progress_bar(100),
        ]
        for anim in animations:
            try: await m.edit_text(anim); await asyncio.sleep(0.35)
            except: pass

        await update.effective_chat.send_action(ChatAction.TYPING)
        info=await asyncio.to_thread(get_tiktok_info, url, tmpdir)

        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        await m.edit_text(f"⚡ Downloading {info['duration']}s FULL VIDEO...\n{progress_bar(85)}\n🔴 Live: {LIVE_DOWNLOADS} downloading now")

        path=await asyncio.to_thread(download_video_sync, url, tmpdir, "hd", False)
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

        # BEAUTIFUL THUMBNAIL WITH LOGO
        beautiful_thumb=None
        if info['thumb'] and os.path.exists(info['thumb']):
            beautiful_thumb=await asyncio.to_thread(create_beautiful_thumbnail, info['thumb'], LOGO_PATH)

        if size_mb > MAX_SIZE_MB:
            await m.edit_text(f"📦 {size_mb:.1f}MB Large File - Uploading to Premium Cloud... 🚀\n{progress_bar(95)}")
            link, service = await asyncio.to_thread(upload_large_file, path)
            if link:
                # OPTION 2 BEAUTIFUL + MORE BEAUTIFUL BUTTONS
                kb=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"📦 Catbox Full Quality • {size_mb:.1f}MB 🚀", url=link)],
                    [InlineKeyboardButton(f"⬇️ Download Full HD • No Compression 💎", url=link)],
                    [InlineKeyboardButton("🎬 HD 1080p 💎", callback_data=f"hd_{short_id}"), InlineKeyboardButton("💧 Watermark", callback_data=f"wm_{short_id}")],
                    [InlineKeyboardButton(f"📊 Stats • {STATS['total']} downloads", callback_data=f"stats_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")]
                ])
                sent=await update.message.reply_text(caption+f"\n\n☁️ <b>{service}</b>\n🔗 <code>{html.escape(link)}</code>", reply_markup=kb, parse_mode=ParseMode.HTML)
                context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id})
            else:
                await update.message.reply_text("❌ Upload failed")
            try: await m.delete()
            except: pass
            return

        # SMALL FILE - MOST BEAUTIFUL UI
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 HD 1080p 💎 Premium", callback_data=f"hd_{short_id}")],
            [InlineKeyboardButton("📱 Original", callback_data=f"orig_{short_id}"), InlineKeyboardButton("💧 Watermark ✨", callback_data=f"wm_{short_id}")],
            [InlineKeyboardButton("🎵 MP3 Audio", callback_data=f"mp3_{short_id}"), InlineKeyboardButton("🖼 Thumbnail", callback_data=f"thumb_{short_id}")],
            [InlineKeyboardButton(f"📊 {STATS['total']} Downloads • 🔴 {LIVE_DOWNLOADS} Live", callback_data=f"stats_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")],
        ])

        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        thumb_file = open(beautiful_thumb,'rb') if beautiful_thumb and os.path.exists(beautiful_thumb) else (open(info['thumb'],'rb') if info['thumb'] and os.path.exists(info['thumb']) else None)

        with open(path,'rb') as vf:
            sent=await update.message.reply_video(
                video=vf, thumbnail=thumb_file, caption=caption,
                supports_streaming=True, reply_markup=kb,
                parse_mode=ParseMode.HTML, has_spoiler=False,
                read_timeout=180, write_timeout=180
            )
        if thumb_file: thumb_file.close()
        try: await m.delete()
        except: pass
        context.job_queue.run_once(delete_after, when=AUTO_DELETE_MIN*60, data={'chat_id':sent.chat_id,'msg_id':sent.message_id})
        # BEAUTIFUL AUTO-DELETE MESSAGE
        await update.message.reply_text(
            f"✅ <b>Video sent!</b> ✨\n⏰ Auto-delete in {AUTO_DELETE_MIN}min • Enjoy 💎",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Delete Now", callback_data=f"del_{short_id}")]]),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Error {e}", exc_info=True)
        try: await m.edit_text(f"❌ {e}")
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
    if data.startswith("stats_"):
        total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
        return await q.message.reply_text(f"📊 <b>LIVE DASHBOARD</b>\n━━━━━━━━━━━━\n📥 Total: {STATS['total']}\n👥 Users: {total_users}\n🔴 Live: {LIVE_DOWNLOADS}\n💾 Served: {STATS['total_size']/1024:.2f} GB\n━━━━━━━━━━━━", parse_mode=ParseMode.HTML)
    if data.startswith("thumb_"):
        sid=data.split("_",1)[1]
        info=URL_STORE.get(sid)
        if info and info['thumb'] and os.path.exists(info['thumb']):
            with open(info['thumb'],'rb') as f:
                await q.message.reply_photo(photo=f, caption="🖼 Beautiful Thumbnail with Logo")
        return
    try:
        action, sid = data.split("_",1)
        info=URL_STORE.get(sid)
        if not info: return await q.message.reply_text("Expired")
        tmpdir=tempfile.mkdtemp()
        m=await q.message.reply_text(f"⚡ {action.upper()}... {progress_bar(50)}")
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
                await m.edit_text(f"📦 Uploading {size_mb:.1f}MB 🚀... {progress_bar(80)}")
                link, service=await asyncio.to_thread(upload_large_file, path)
                if link:
                    kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Catbox Full Quality • {size_mb:.1f}MB 🚀", url=link)]])
                    await q.message.reply_text(f"📦 FULL {size_mb:.1f}MB • {service}\n{link}", reply_markup=kb)
                    await m.delete()
                    return
            with open(path,'rb') as vf:
                await q.message.reply_video(video=vf, caption=f"🎬 @{info['author']} • {size_mb:.1f}MB FULL 💎", supports_streaming=True)
            await m.delete()
        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Button {e}")
        await q.message.reply_text(f"Error: {e}")

async def start_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
    await update.message.reply_text(
        f"🌌 <b>{to_bold('ULTIMATE TIKTOK BOT')}</b> 🌌\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>Features:</b>\n"
        f"• 💎 1080p Full Quality\n"
        f"• 📦 Catbox 1GB Support (456MB fixed)\n"
        f"• 🎨 Beautiful Thumbnail + {LOGO_PATH}\n"
        f"• 📊 Live Stats + Counter\n"
        f"• ⏰ Auto-delete {AUTO_DELETE_MIN}min\n"
        f"• ⚡ Progress Bar Animation\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 {STATS['total']} downloads | 👥 {total_users} users | 🔴 {LIVE_DOWNLOADS} live\n\n"
        f"Send TikTok link ✨",
        parse_mode=ParseMode.HTML
    )

async def admin_panel(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id!=ADMIN_ID: return await update.message.reply_text("Not admin")
    total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
    await update.message.reply_text(
        f"🔐 <b>ADMIN PANEL - BEAUTIFUL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Total: {STATS['total']} 📥\n"
        f"👥 Users: {total_users}\n"
        f"💾 Size: {STATS['total_size']:.1f}MB ({STATS['total_size']/1024:.2f}GB)\n"
        f"🔴 Live: {LIVE_DOWNLOADS} downloading\n"
        f"📦 Max: {MAX_SIZE_MB}MB\n"
        f"⏰ Auto-delete: {AUTO_DELETE_MIN}min\n"
        f"💧 Logo: {os.path.exists(LOGO_PATH)} {LOGO_PATH}\n"
        f"🚀 Catbox: 200MB | Litterbox: 1GB | GoFile: 10GB\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"/stats - Live stats\n"
        f"/start - Start",
        parse_mode=ParseMode.HTML
    )

async def stats_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    total_users=len(STATS['users']) if isinstance(STATS['users'], set) else 0
    await update.message.reply_text(
        f"📊 <b>LIVE DASHBOARD</b> 📊\n"
        f"╔═══════════════════╗\n"
        f"║ 📥 Total: {STATS['total']}\n"
        f"║ 👥 Users: {total_users}\n"
        f"║ 🔴 Live Now: {LIVE_DOWNLOADS}\n"
        f"║ 💾 Served: {STATS['total_size']/1024:.2f} GB\n"
        f"╚═══════════════════╝\n"
        f"✨ Beautiful Bot ✨",
        parse_mode=ParseMode.HTML
    )

async def inline_mode(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query=update.inline_query.query
    if not query: return
    results=[InlineQueryResultArticle(id=uuid.uuid4().hex, title="💎 Download TikTok FULL HD", description="Premium download", input_message_content=InputTextMessageContent(f"🎬 {query}\nSend to @{BOT_USERNAME} for premium download"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download in Bot 🚀", url=f"https://t.me/{BOT_USERNAME.replace('@','')}")]]))]
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
    logger.info("Beautiful Ultimate Bot Running")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
