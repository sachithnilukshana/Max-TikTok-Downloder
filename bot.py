import os, re, uuid, asyncio, tempfile, requests, threading, subprocess
from datetime import datetime
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-type','text/plain'); self.end_headers()
        self.wfile.write(b"Alive")
    def log_message(self,*a): pass
def run_web():
    try: HTTPServer(('0.0.0.0', int(os.getenv("PORT",10000))), HealthHandler).serve_forever()
    except: pass
threading.Thread(target=run_web, daemon=True).start()

load_dotenv()
BOT_TOKEN=os.getenv("BOT_TOKEN")
MAX_SIZE_MB=int(os.getenv("MAX_TELEGRAM_SIZE_MB","50"))
BOT_USERNAME=os.getenv("BOT_USERNAME","@YourBot")
LOGO_PATH="TIKTOKLOGO.png"
if not BOT_TOKEN: raise ValueError("BOT_TOKEN missing")

URL_STORE={}

def upload_to_catbox(fp):
    try:
        print(f"Uploading {fp} to Catbox...")
        with open(fp,'rb') as f:
            r=requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload":f}, timeout=120)
        if r.status_code==200 and "https://catbox.moe" in r.text:
            url=r.text.strip()
            print(f"Catbox OK {url}")
            return url
    except Exception as e:
        print(f"Catbox fail {e}")
    return None

def add_watermark(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1][0]scale2ref=w=iw*0.18:h=ow/mdar[wm][vid];[vid][wm]overlay=W-w-20:20","-codec:a","copy",output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        if os.path.exists(output_path) and os.path.getsize(output_path)>1000: return output_path
    except: pass
    return video_path

def download_video_sync(url, tmpdir, quality="hd", watermark=False):
    import yt_dlp
    fp=os.path.join(tmpdir, f"{uuid.uuid4().hex}.mp4")
    # METHOD 1: yt-dlp App API - FULL VIDEO FIX
    try:
        ydl_opts={
            'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl':fp,
            'merge_output_format':'mp4',
            'concurrent_fragment_downloads':16,
            'quiet':True,'no_warnings':True,'noplaylist':True,'nocheckcertificate':True,
            'extractor_args':{'tiktok':{'api_hostname':['api16-normal-c-useast1a.tiktokv.com']}},
            'external_downloader_args':{'ffmpeg':['-threads','8']},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=False)
            data={'title':info.get('title','')[:80],'author':info.get('uploader','tiktok'),'duration':info.get('duration',0)}
            ydl.download([url])
        if not os.path.exists(fp):
            for f in os.listdir(tmpdir):
                if f.endswith('.mp4'): fp=os.path.join(tmpdir,f); break
        if os.path.exists(fp) and os.path.getsize(fp)>10000:
            if watermark and os.path.exists(LOGO_PATH):
                wm_out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
                fp=add_watermark(fp, LOGO_PATH, wm_out)
            return {"path":fp,"data":data}
    except Exception as e:
        print(f"yt-dlp fail {e}")

    # METHOD 2: tikwm FULL VIDEO
    try:
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        j=r.json()
        if j.get('code')==0:
            d=j['data']
            vurl=d.get('hdplay') if quality=="hd" else d.get('play')
            vurl=vurl or d.get('play')
            fp2=os.path.join(tmpdir, f"tikwm_{uuid.uuid4().hex}.mp4")
            with requests.Session() as s:
                s.headers.update({'User-Agent':'Mozilla/5.0','Referer':'https://www.tikwm.com/'})
                with s.get(vurl, stream=True, timeout=90) as r2:
                    with open(fp2,'wb') as f:
                        for chunk in r2.iter_content(chunk_size=1024*1024*2):
                            if chunk: f.write(chunk)
            data={'title':d.get('title','')[:80],'author':d.get('author',{}).get('unique_id','tiktok'),'duration':d.get('duration',0)}
            if watermark and os.path.exists(LOGO_PATH):
                wm_out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
                fp2=add_watermark(fp2, LOGO_PATH, wm_out)
            return {"path":fp2,"data":data}
    except Exception as e:
        print(f"tikwm fail {e}")

    raise Exception("Download failed - try again")

async def process_tiktok(update:Update, context, url:str):
    t0=datetime.now()
    tmpdir=tempfile.mkdtemp()
    m=await update.message.reply_text("⚡ Turbo Download FULL...")
    try:
        await update.effective_chat.send_action(ChatAction.UPLOAD_VIDEO)
        res=await asyncio.to_thread(download_video_sync, url, tmpdir, "hd", False)
        path=res["path"]
        size_mb=os.path.getsize(path)/(1024*1024)
        elapsed=(datetime.now()-t0).total_seconds()

        short_id=str(uuid.uuid4())[:8]
        URL_STORE[short_id]=res["data"]
        URL_STORE[short_id]['url']=url
        URL_STORE[short_id]['tmp_path']=path # keep for catbox if needed? but we will re-download on button
        URL_STORE[short_id]['original_path']=path

        # BUTTONS LIKE YOUR PHOTO
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 HD 1080p 💎", callback_data=f"hd_{short_id}")],
            [InlineKeyboardButton("📱 Original", callback_data=f"orig_{short_id}"), InlineKeyboardButton("💧 Watermark", callback_data=f"wm_{short_id}")],
            [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")],
            [InlineKeyboardButton("📦 Catbox Full Quality", callback_data=f"catbox_{short_id}")]
        ])

        # CASE 1: MORE THAN 50MB -> CATBOX
        if size_mb > MAX_SIZE_MB:
            await m.edit_text(f"📦 {size_mb:.1f}MB > {MAX_SIZE_MB}MB - Uploading to Catbox Full Quality...")
            cat_url=await asyncio.to_thread(upload_to_catbox, path)
            if cat_url:
                cat_kb=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download Full Quality", url=cat_url)],
                    [InlineKeyboardButton("🎬 HD 1080p 💎", callback_data=f"hd_{short_id}"), InlineKeyboardButton("📱 Original", callback_data=f"orig_{short_id}")],
                    [InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")]
                ])
                await update.message.reply_text(
                    f"📦 **FULL VIDEO {size_mb:.1f}MB - Telegram limit exceeded**\n"
                    f"🎬 @{res['data']['author']} • {res['data']['duration']}s FULL\n"
                    f"💎 Full Quality No Compression\n"
                    f"🔗 {cat_url}\n"
                    f"⚡ {elapsed:.1f}s",
                    reply_markup=cat_kb, parse_mode='Markdown'
                )
                await m.delete()
            else:
                await m.edit_text("❌ Catbox failed")
            return

        # CASE 2: LESS THAN 50MB -> SEND VIDEO WITH BUTTONS
        else:
            await m.edit_text(f"⚡ {size_mb:.1f}MB in {elapsed:.1f}s - Sending video...")
            caption=f"🎬 @{res['data']['author']} • {res['data']['duration']}s FULL • {size_mb:.1f}MB • ⚡ {elapsed:.1f}s\n{BOT_USERNAME}"
            with open(path,'rb') as vf:
                await update.message.reply_video(
                    video=vf,
                    caption=caption,
                    supports_streaming=True,
                    reply_markup=kb,
                    read_timeout=120, write_timeout=120
                )
            await m.delete()

    except Exception as e:
        try: await m.edit_text(f"❌ {e}")
        except: pass
        print(e)
    finally:
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

async def button_handler(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    data=q.data
    if data.startswith("del_"):
        try: await q.message.delete()
        except: pass
        return

    try:
        action, sid = data.split("_",1)
        info=URL_STORE.get(sid)
        if not info:
            return await q.message.reply_text("❌ Expired - Send link again")

        tmpdir=tempfile.mkdtemp()
        m=await q.message.reply_text(f"⚡ Processing {action.upper()} FULL...")
        try:
            await q.message.chat.send_action(ChatAction.UPLOAD_VIDEO if action!="mp3" else ChatAction.UPLOAD_VOICE)

            if action=="mp3":
                import yt_dlp
                fp=os.path.join(tmpdir, "audio.%(ext)s")
                opts={'outtmpl':fp,'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],'quiet':True}
                await asyncio.to_thread(lambda: yt_dlp.YoutubeDL(opts).download([info['url']]))
                mp3=None
                for f in os.listdir(tmpdir):
                    if f.endswith('.mp3'): mp3=os.path.join(tmpdir,f); break
                if mp3:
                    with open(mp3,'rb') as af:
                        await q.message.reply_audio(audio=af, title=info.get('title','')[:60])
                    await m.delete()
                return

            watermark=(action=="wm")
            quality="hd" if action in ["hd","catbox"] else "orig"
            res=await asyncio.to_thread(download_video_sync, info['url'], tmpdir, quality, watermark)
            path=res["path"]
            size_mb=os.path.getsize(path)/(1024*1024)

            if action=="catbox" or size_mb>MAX_SIZE_MB:
                await m.edit_text(f"📦 Uploading {size_mb:.1f}MB Full Quality to Catbox...")
                cat_url=await asyncio.to_thread(upload_to_catbox, path)
                if cat_url:
                    kb=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Catbox Full Quality", url=cat_url)]])
                    await q.message.reply_text(f"📦 FULL {size_mb:.1f}MB 💎\n🔗 {cat_url}\nNo compression - Full Quality", reply_markup=kb)
                    await m.delete()
                    return

            cap=f"🎬 @{res['data']['author']} • {res['data']['duration']}s FULL • {size_mb:.1f}MB"
            with open(path,'rb') as vf:
                await q.message.reply_video(video=vf, caption=cap, supports_streaming=True, read_timeout=120, write_timeout=120)
            await m.delete()

        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    except Exception as e:
        print(f"Btn error {e}")
        try: await q.message.reply_text(f"❌ {e}")
        except: pass

async def start_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ Send TikTok link\nI will send VIDEO directly\nIf >50MB -> Catbox link\nIf <50MB -> Video + buttons")

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
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Bot Running - VIDEO FIRST + CATBOX >50MB")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
