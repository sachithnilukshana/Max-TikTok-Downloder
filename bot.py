import os, re, json, uuid, asyncio, tempfile, requests, threading, subprocess
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
if not BOT_TOKEN: raise ValueError("BOT_TOKEN")

URL_STORE={}
DATA={"history":{},"stats":{"total":0}}

def upload_to_catbox(fp):
    try:
        with open(fp,'rb') as f:
            r=requests.post("https://catbox.moe/user/api.php", data={"reqtype":"fileupload"}, files={"fileToUpload":f}, timeout=120)
        if r.status_code==200 and "catbox" in r.text: return r.text.strip()
    except Exception as e: print(e)
    return None

def add_watermark(video_path, logo_path, output_path):
    if not os.path.exists(logo_path): return video_path
    try:
        cmd=["ffmpeg","-y","-i",video_path,"-i",logo_path,"-filter_complex","[1][0]scale2ref=w=iw*0.18:h=ow/mdar[wm][vid];[vid][wm]overlay=W-w-20:20","-codec:a","copy",output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        if os.path.exists(output_path) and os.path.getsize(output_path)>1000: return output_path
    except: pass
    return video_path

def get_info_fast(url, tmpdir):
    # FAST INFO via tikwm (fastest for cover)
    try:
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        j=r.json()
        if j.get('code')==0:
            d=j['data']
            cover_url=d.get('cover') or d.get('origin_cover') or d.get('ai_dynamic_cover')
            cover_path=None
            if cover_url:
                cover_path=os.path.join(tmpdir, "cover.jpg")
                try:
                    with requests.get(cover_url, stream=True, timeout=10) as cr:
                        with open(cover_path,'wb') as cf:
                            for c in cr.iter_content(8192): cf.write(c)
                except: cover_path=None
            info={
                'title':d.get('title','')[:200],
                'author':d.get('author',{}).get('unique_id','tiktok'),
                'nickname':d.get('author',{}).get('nickname',''),
                'duration':d.get('duration',0),
                'play_count':d.get('play_count',0),
                'digg_count':d.get('digg_count',0),
                'music':d.get('music_info',{}).get('title','Original')[:30],
                'cover':cover_path,
                'url':url,
                'data':d
            }
            return info
    except Exception as e:
        print(f"info fail {e}")

    # fallback yt-dlp info
    import yt_dlp
    ydl_info={'quiet':True,'skip_download':True,'no_warnings':True}
    with yt_dlp.YoutubeDL(ydl_info) as ydl:
        i=ydl.extract_info(url, download=False)
        return {
            'title':i.get('title','')[:200],
            'author':i.get('uploader','tiktok'),
            'nickname':i.get('uploader',''),
            'duration':i.get('duration',0),
            'play_count':i.get('view_count',0),
            'digg_count':i.get('like_count',0),
            'music':'Original',
            'cover':None,
            'url':url,
            'data':i
        }

def download_video(url, tmpdir, quality="hd", watermark=False):
    import yt_dlp
    fp=os.path.join(tmpdir, f"{uuid.uuid4().hex}.mp4")
    ydl_opts={
        'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl':fp,
        'merge_output_format':'mp4',
        'concurrent_fragment_downloads':16,
        'quiet':True,
        'no_warnings':True,
        'noplaylist':True,
        'nocheckcertificate':True,
        'extractor_args':{'tiktok':{'api_hostname':['api16-normal-c-useast1a.tiktokv.com']}},
        'external_downloader_args':{'ffmpeg':['-threads','8']},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if not os.path.exists(fp):
            for f in os.listdir(tmpdir):
                if f.endswith('.mp4'): fp=os.path.join(tmpdir,f); break
        if watermark and os.path.exists(LOGO_PATH):
            wm_out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp=add_watermark(fp, LOGO_PATH, wm_out)
        return fp
    except:
        # fallback tikwm direct
        r=requests.get(f"https://www.tikwm.com/api/?url={url}&hd=1", headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        j=r.json()
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
        if watermark and os.path.exists(LOGO_PATH):
            wm_out=os.path.join(tmpdir, f"wm_{uuid.uuid4().hex}.mp4")
            fp2=add_watermark(fp2, LOGO_PATH, wm_out)
        return fp2

def format_num(n):
    try:
        n=int(n)
        if n>=1000000: return f"{n/1000000:.1f}M"
        if n>=1000: return f"{n/1000:.1f}K"
        return str(n)
    except: return "0"

async def process_tiktok(update:Update, context, url:str):
    tmpdir=tempfile.mkdtemp()
    try:
        m=await update.message.reply_text("🔍 Getting info...")
        info=await asyncio.to_thread(get_info_fast, url, tmpdir)
        short_id=str(uuid.uuid4())[:8]
        URL_STORE[short_id]=info

        caption=(
            f"🎬 **@{info['author']}** ({info['nickname']})\n"
            f"📝 {info['title'][:100]}\n\n"
            f"⏱️ {info['duration']}s FULL • 👁️ {format_num(info['play_count'])} • ❤️ {format_num(info['digg_count'])}\n"
            f"🎵 {info['music']}\n\n"
            f"👇 Select quality - Full Quality Catbox available"
        )

        # BUTTONS LIKE YOUR PHOTO + CATBOX
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 HD 1080p 💎", callback_data=f"hd_{short_id}")],
            [InlineKeyboardButton("📱 Original", callback_data=f"orig_{short_id}"), InlineKeyboardButton("💧 Watermark", callback_data=f"wm_{short_id}")],
            [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3_{short_id}"), InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{short_id}")],
            [InlineKeyboardButton("📦 Catbox Full Quality", callback_data=f"catbox_{short_id}")]
        ])

        if info['cover'] and os.path.exists(info['cover']):
            with open(info['cover'],'rb') as ph:
                await update.message.reply_photo(photo=ph, caption=caption, reply_markup=kb, parse_mode='Markdown')
        else:
            await update.message.reply_text(caption, reply_markup=kb, parse_mode='Markdown')

        await m.delete()
    except Exception as e:
        print(e)
        await update.message.reply_text(f"❌ {e}")
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
        m=await q.message.reply_text(f"⚡ Downloading {action.upper()} FULL...")
        try:
            await q.message.chat.send_action(ChatAction.UPLOAD_VIDEO if action!="mp3" else ChatAction.UPLOAD_VOICE)

            if action=="mp3":
                import yt_dlp
                fp=os.path.join(tmpdir, "audio.%(ext)s")
                opts={'outtmpl':fp,'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],'quiet':True}
                def dlmp3():
                    with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([info['url']])
                await asyncio.to_thread(dlmp3)
                mp3=None
                for f in os.listdir(tmpdir):
                    if f.endswith('.mp3'): mp3=os.path.join(tmpdir,f); break
                if mp3:
                    with open(mp3,'rb') as af:
                        await q.message.reply_audio(audio=af, title=info['title'][:60], performer=info['author'])
                    await m.delete()
                else:
                    await m.edit_text("❌ MP3 failed")

            else:
                watermark = (action=="wm")
                quality = "hd" if action in ["hd","catbox"] else "orig"
                path=await asyncio.to_thread(download_video, info['url'], tmpdir, quality, watermark)

                size_mb=os.path.getsize(path)/(1024*1024)

                # CATBOX BUTTON ACTION
                if action=="catbox":
                    await m.edit_text(f"📦 Uploading {size_mb:.1f}MB to Catbox Full Quality...")
                    cat_url=await asyncio.to_thread(upload_to_catbox, path)
                    if cat_url:
                        kb=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Full Quality Catbox", url=cat_url)]])
                        await q.message.reply_text(f"📦 **FULL QUALITY {size_mb:.1f}MB**\n🎬 {info['title'][:80]}\n🔗 {cat_url}\n💎 No compression", reply_markup=kb, parse_mode='Markdown')
                        await m.delete()
                    else:
                        await m.edit_text("❌ Catbox upload failed, sending direct...")
                        with open(path,'rb') as vf:
                            await q.message.reply_video(video=vf, caption=f"🎬 FULL {size_mb:.1f}MB @{info['author']}")
                        await m.delete()
                else:
                    # Check size
                    if size_mb>MAX_SIZE_MB:
                        await m.edit_text(f"📦 {size_mb:.1f}MB > {MAX_SIZE_MB}MB -> Catbox...")
                        cat_url=await asyncio.to_thread(upload_to_catbox, path)
                        if cat_url:
                            kb=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Catbox Full", url=cat_url)]])
                            await q.message.reply_text(f"📦 Large Full {size_mb:.1f}MB\n🔗 {cat_url}", reply_markup=kb)
                            await m.delete()
                            return

                    cap=f"🎬 @{info['author']} • {info['duration']}s FULL • {size_mb:.1f}MB\n{BOT_USERNAME}"
                    if action=="hd": cap=f"🎬 HD 1080p 💎 FULL • {size_mb:.1f}MB\n{cap}"
                    elif action=="wm": cap=f"💧 Watermark • {cap}"

                    with open(path,'rb') as vf:
                        await q.message.reply_video(video=vf, caption=cap, supports_streaming=True, read_timeout=120, write_timeout=120)
                    await m.delete()

        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    except Exception as e:
        print(f"Button error {e}")
        try: await q.message.reply_text(f"❌ {e}")
        except: pass

async def start_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ Send TikTok link\nYou will get photo with info + buttons\nHD 1080p / Original / Watermark / MP3 / Delete / Catbox Full")

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
    print("Bot Running with INFO PHOTO + BUTTONS + CATBOX")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
