# 🎬 MAX — TikTok Ultra Downloader Bot 💎

<p align="center">
  <img src="TIKTOKLOGO.png" width="180" alt="MAX TikTok Downloader Logo">
</p>

<h1 align="center">MAX TikTok Ultra Downloader</h1>

<p align="center">
  <b>Fast • Beautiful • Powerful • Production Ready</b>
</p>

<p align="center">
  Download TikTok videos, audio, slideshows and profiles directly through Telegram.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram">
  <img src="https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render">
  <img src="https://img.shields.io/badge/FFmpeg-Enabled-green?style=for-the-badge">
  <img src="https://img.shields.io/badge/Speed-Turbo-red?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge">
</p>

---

# 📖 About MAX

**MAX TikTok Ultra Downloader** is a Telegram bot designed to provide a fast and simple way to process TikTok URLs.

MAX can support:

- 🎬 TikTok video downloads
- 🎵 MP3/audio extraction
- 🖼️ TikTok slideshows
- 👤 Profile lookups
- 📦 Large-file handling
- ⚡ Fast downloading
- 🗂️ File caching
- 🖼️ Custom branding
- 📊 User ranking
- 🔐 Admin controls
- ♾️ Telegram Inline Mode
- 🗑️ Automatic cleanup

The project is designed to run locally or on cloud platforms such as **Render** using Docker.

---

# ✨ Features

## 🎬 HD Video Download

MAX can process TikTok videos in different quality modes depending on the source provider.

Supported workflows can include:

- 1080p
- Original quality
- Watermarked videos
- Standard quality
- Automatic file processing

Example:

```text
🔗 TikTok URL
       ↓
   MAX Bot
       ↓
  Download
       ↓
   Process
       ↓
📥 Telegram
```

---

# 🎵 MP3 Audio Extraction

MAX can extract audio from supported TikTok videos.

Features:

- MP3 conversion
- FFmpeg processing
- Audio metadata
- Cover image support
- Automatic temporary-file cleanup

Example:

```text
TikTok Video
      ↓
   FFmpeg
      ↓
   MP3 Audio
      ↓
   Telegram
```

---

# 🖼️ Slideshow Support

MAX can process TikTok photo/slideshow posts.

Supported workflow:

```text
TikTok Slideshow
       ↓
  Download Images
       ↓
 Process Images
       ↓
 Telegram Media Group
```

Users can receive multiple images directly inside Telegram.

---

# 👤 Profile Support

MAX can process TikTok profile usernames.

Example:

```text
@username
```

Depending on the configured source/API, the bot can retrieve available profile information or supported content.

---

# 📦 Large File Support

Telegram file-size limits can prevent large media files from being sent directly.

MAX can automatically detect large files.

Example:

```text
Downloaded File
      ↓
Is file larger than limit?
      │
   ┌──┴──┐
   │     │
  NO    YES
   │     │
   ▼     ▼
Telegram Catbox
```

For files larger than the configured Telegram limit, MAX can upload the file to **Catbox** and return a download link.

Example:

```text
╭─ 📦 LARGE FILE ─╮
│
│ ⚠️ 72.3 MB > 50 MB Limit
│
│ 🔗 https://files.catbox.moe/xxxx.mp4
│
╰─────────────────╯

📥 Download from Catbox
```

---

# ⚡ Turbo Download System

MAX is designed for fast downloading.

Possible optimizations include:

- Chunked downloads
- HTTP keep-alive
- Connection reuse
- Streaming
- Local caching
- Telegram `file_id` caching
- Automatic temporary-file cleanup

The exact download speed depends on:

- Source server
- Render region
- Internet connection
- TikTok response speed
- File size
- Telegram upload speed
- Catbox upload speed
- FFmpeg processing time

---

# 💎 Beautiful Telegram UI

MAX can provide a clean Telegram interface with:

- 🎬 Welcome screen
- 🔗 URL detection
- ⏳ Processing status
- 📊 Progress messages
- 📥 Download buttons
- ⚠️ Error messages
- 📦 Large-file notifications
- 🎵 Audio results
- 🖼️ Image results
- 👤 Profile information
- 🔐 Admin controls

---

# 🖼️ MAX Branding

The project uses:

```text
TIKTOKLOGO.png
```

This image should be placed in the root directory:

```text
tiktok-bot/
├── bot.py
├── TIKTOKLOGO.png
├── requirements.txt
└── README.md
```

The logo can be used for:

- `/start`
- Bot branding
- Generated media
- Watermark workflows
- Telegram messages

---

# 📊 Rank System

MAX can include a user ranking system.

Example:

```text
🆕 Newbie
🥉 Bronze
🥈 Silver
🥇 Gold
💎 Diamond
```

A rank system can be based on:

- Downloads
- User activity
- Daily usage
- Total requests
- Referrals
- Other custom metrics

Example:

```text
╭───────────────╮
│ 💎 MAX PROFILE │
├───────────────┤
│ 👤 User: Sachith
│ 🏆 Rank: Gold
│ 📥 Downloads: 250
│ ⭐ Points: 1,250
╰───────────────╯
```

---

# 🔐 Admin Panel

Administrators can access:

```text
/admin
```

Possible admin features:

```text
📊 Statistics
👥 Users
📢 Broadcast
🗑️ Clear Cache
📈 Analytics
⚙️ Settings
```

Example:

```text
╭────────────────────╮
│ 🔐 MAX ADMIN PANEL │
├────────────────────┤
│ 📊 Statistics       │
│ 👥 Users            │
│ 📢 Broadcast        │
│ 🗑️ Clear Cache      │
│ 📈 Analytics        │
│ ⚙️ Settings         │
╰────────────────────╯
```

Only Telegram IDs listed in `ADMIN_IDS` should be allowed to access administrator functions.

---

# ♾️ Inline Mode

If Telegram Inline Mode is enabled for the bot, users can process URLs directly inside chats.

Example:

```text
@YourBot https://www.tiktok.com/...
```

Telegram will then request results from MAX.

---

# 🗑️ Automatic Cleanup

Temporary files can consume a large amount of disk space.

MAX can automatically delete temporary files after processing.

Configuration:

```env
AUTO_DELETE_MINUTES=10
```

Temporary files can include:

```text
.mp4
.mp3
.jpg
.jpeg
```

---

# 🧠 How MAX Works

The basic workflow looks like this:

```text
                    👤 USER
                      │
                      ▼
              ┌───────────────┐
              │ Telegram Bot  │
              └───────┬───────┘
                      │
                      ▼
              🔗 TikTok URL
                      │
                      ▼
              ┌───────────────┐
              │   MAX Bot     │
              └───────┬───────┘
                      │
                      ▼
             TikTok/API Source
                      │
                      ▼
               ⚡ Downloader
                      │
                      ▼
                 FFmpeg
                      │
                ┌─────┴─────┐
                │           │
                ▼           ▼
             < 50 MB      > 50 MB
                │           │
                ▼           ▼
            Telegram      Catbox
                │           │
                └─────┬─────┘
                      ▼
                 👤 USER
```

---

# 📦 File Processing

## Small Files

When the file is below the configured Telegram limit:

```text
TikTok
   ↓
Download
   ↓
Process
   ↓
Telegram
   ↓
User
```

---

## Large Files

When the file is above the configured limit:

```text
TikTok
   ↓
Download
   ↓
Process
   ↓
Catbox
   ↓
Generate Link
   ↓
Telegram
   ↓
User
```

---

# 🗂️ Caching

MAX can use Telegram `file_id` caching.

This allows previously uploaded Telegram files to be reused without uploading the same media again.

Example:

```text
FIRST REQUEST

TikTok
  ↓
Download
  ↓
Telegram Upload
  ↓
Save Telegram file_id


SECOND REQUEST

TikTok
  ↓
Cache
  ↓
Telegram file_id
  ↓
Send instantly
```

This can significantly reduce processing time for repeated files.

---

# ⚡ Performance

Performance depends on the source and server.

Typical target ranges:

| File / Operation | Approximate Time |
|---|---:|
| Small video ~10 MB | 3–6 sec |
| HD video ~25 MB | 5–10 sec |
| Cached Telegram file | ~0.5 sec |
| Large file → Catbox | 10–15+ sec |

These values are only examples.

Actual performance can vary.

---

# 🛠️ Requirements

Before running MAX, make sure you have:

- Python 3.10+
- FFmpeg
- Telegram Bot Token
- Telegram account
- Internet connection
- Git
- Optional Render account
- Optional Catbox support

---

# 💻 Local Installation

## 1. Clone the repository

```bash
git clone https://github.com/yourname/tiktok-bot.git
cd tiktok-bot
```

Replace:

```text
https://github.com/yourname/tiktok-bot.git
```

with your actual repository URL.

---

# 📦 2. Install Python Dependencies

Run:

```bash
pip install -r requirements.txt
```

If you use a virtual environment:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

# 🎞️ 3. Install FFmpeg

FFmpeg is required for audio extraction and video processing.

## Ubuntu / Debian

```bash
sudo apt update
sudo apt install ffmpeg -y
```

Verify:

```bash
ffmpeg -version
```

---

## Windows

Install FFmpeg and add it to your system `PATH`.

Verify:

```powershell
ffmpeg -version
```

---

# 🔑 4. Create `.env`

Create a file named:

```text
.env
```

Add:

```env
BOT_TOKEN=123456:AAH_YOUR_TOKEN
ADMIN_IDS=123456789,987654321
AUTO_DELETE_MINUTES=10
BOT_USERNAME=@YourBot
CATBOX_ENABLED=True
MAX_TELEGRAM_SIZE_MB=50
```

Replace the example values with your real configuration.

---

# ▶️ 5. Start MAX

Run:

```bash
python bot.py
```

If everything is configured correctly, the bot should start.

---

# 📁 Project Structure

```text
tiktok-bot/
│
├── bot.py
│
├── TIKTOKLOGO.png
│
├── requirements.txt
│
├── Dockerfile
│
├── render.yaml
│
├── .env.example
│
├── .gitignore
│
├── bot_data.json
│
└── README.md
```

---

# 📄 requirements.txt

Create:

```text
requirements.txt
```

with:

```txt
python-telegram-bot==20.8
requests
yt-dlp
mutagen
python-dotenv
```

---

# 🐳 Dockerfile

The Dockerfile installs FFmpeg automatically.

```dockerfile
FROM python:3.10-slim

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Application directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Start MAX
CMD ["python", "bot.py"]
```

---

# ☁️ Render Deployment

MAX can be deployed to Render using Docker.

There are two main methods:

1. 🥇 Blueprint deployment
2. 🥈 Manual Web Service deployment

---

# 🥇 Method 1 — Render Blueprint

This is the recommended method.

## Step 1 — Push to GitHub

Upload the project to GitHub.

Make sure these files exist:

```text
bot.py
TIKTOKLOGO.png
requirements.txt
Dockerfile
render.yaml
.env.example
.gitignore
README.md
```

---

# Step 2 — Open Render

Open:

```text
https://dashboard.render.com
```

Create:

```text
New → Blueprint
```

Connect your GitHub repository.

Render will automatically detect:

```text
render.yaml
```

---

# Step 3 — Configure Environment Variables

Add your environment variables in Render.

```env
BOT_TOKEN=123456:AAH_YOUR_TOKEN
ADMIN_IDS=123456789
AUTO_DELETE_MINUTES=10
BOT_USERNAME=@YourBot
CATBOX_ENABLED=True
MAX_TELEGRAM_SIZE_MB=50
```

### Important

Never put your real:

```text
BOT_TOKEN
```

inside a public GitHub repository.

---

# Step 4 — Deploy

Click:

```text
Apply
```

Render will build the Docker image.

The deployment process is:

```text
GitHub
   ↓
Render
   ↓
Docker Build
   ↓
Install FFmpeg
   ↓
Install Python packages
   ↓
Start bot.py
   ↓
MAX ONLINE
```

Check the Render logs after deployment.

---

# 🥈 Method 2 — Manual Web Service

Go to:

```text
Render
   ↓
New
   ↓
Web Service
```

Connect your GitHub repository.

Use:

| Setting | Value |
|---|---|
| Environment | Docker |
| Dockerfile | `./Dockerfile` |
| Plan | Free or selected plan |

The Dockerfile already contains:

```dockerfile
CMD ["python", "bot.py"]
```

so a separate start command is normally not required.

---

# 🧾 render.yaml

Create:

```text
render.yaml
```

with:

```yaml
services:
  - type: web
    name: tiktok-ultra-bot
    env: docker
    plan: free
    dockerfilePath: ./Dockerfile

    envVars:
      - key: BOT_TOKEN
        sync: false

      - key: ADMIN_IDS
        sync: false

      - key: AUTO_DELETE_MINUTES
        value: "10"

      - key: BOT_USERNAME
        sync: false

      - key: CATBOX_ENABLED
        value: "True"

      - key: MAX_TELEGRAM_SIZE_MB
        value: "50"
```

---

# 🔐 .gitignore

Create:

```text
.gitignore
```

with:

```gitignore
.env

bot_data.json

__pycache__/
*.pyc

*.mp4
*.mp3
*.jpg
*.jpeg

venv/
.venv/

.idea/
.vscode/
```

Keep:

```text
TIKTOKLOGO.png
```

tracked if the application requires it.

---

# 📝 .env.example

Create:

```text
.env.example
```

with:

```env
BOT_TOKEN=123456:AAH_YOUR_TOKEN
ADMIN_IDS=123456789
AUTO_DELETE_MINUTES=10
BOT_USERNAME=@YourBot
CATBOX_ENABLED=True
MAX_TELEGRAM_SIZE_MB=50
```

This file should contain example values only.

Do not put your real bot token here.

---

# 🔐 Security

Security is important when deploying a Telegram bot.

## ❌ Never commit your real token

Do not do this:

```python
BOT_TOKEN = "123456:REAL_BOT_TOKEN"
```

---

## ✅ Use environment variables

Use:

```env
BOT_TOKEN=your_token_here
```

Then:

```python
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
```

---

# 🚨 If Your Token Is Exposed

If your Telegram bot token is accidentally posted publicly:

1. Open Telegram.
2. Open BotFather.
3. Revoke the exposed token.
4. Generate a new token.
5. Update the Render environment variable.
6. Remove the exposed token from your repository/history if necessary.

Never share your production token publicly.

---

# 👑 Admin Security

Admin access should be controlled using Telegram user IDs.

Example:

```env
ADMIN_IDS=123456789,987654321
```

The bot should verify the user's Telegram ID before allowing:

```text
/admin
```

or other administrator functions.

---

# ☁️ Render Notes

Render hosting behavior depends on the plan you use.

For free hosting, services may have limitations such as:

- Sleep behavior
- Startup delays
- Limited persistent storage
- Resource limitations
- Temporary filesystem
- Runtime limits

Do not rely on a local JSON file as the only permanent database for important production data.

---

# 🗄️ Database

For a production bot, consider using:

```text
PostgreSQL
```

instead of relying only on:

```text
bot_data.json
```

A production architecture could be:

```text
MAX Bot
   │
   ├── PostgreSQL
   │
   ├── Cache
   │
   ├── File Storage
   │
   └── Telegram
```

---

# 💾 Temporary Files

Downloaded files can use significant storage.

MAX should remove temporary files after processing.

Example:

```text
/downloads/video.mp4
/downloads/audio.mp3
/downloads/image.jpg
```

After the user receives the result:

```text
File → Delete
```

This helps prevent disk usage from continuously increasing.

---

# 🛠️ Troubleshooting

## ❌ FFmpeg not found

Run:

```bash
ffmpeg -version
```

If FFmpeg is missing on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install ffmpeg -y
```

On Render, the provided Dockerfile installs FFmpeg automatically.

---

# ❌ Bot doesn't start

Check your:

```text
BOT_TOKEN
```

Make sure the token is valid.

Then check the application logs.

---

# ❌ Environment variable missing

Make sure these variables exist:

```text
BOT_TOKEN
ADMIN_IDS
AUTO_DELETE_MINUTES
BOT_USERNAME
CATBOX_ENABLED
MAX_TELEGRAM_SIZE_MB
```

---

# ❌ Large files don't upload

Check:

```env
CATBOX_ENABLED=True
MAX_TELEGRAM_SIZE_MB=50
```

Also check the application logs for upload errors.

---

# ❌ TikTok download fails

Possible reasons include:

- Source changed
- API unavailable
- URL is invalid
- Video is private
- Region restrictions
- Provider rate limiting
- Network error
- Downloader dependency needs updating

Check the logs and verify the configured source/provider.

---

# 🔄 Updating the Bot

After making changes:

```bash
git add .
git commit -m "Update MAX bot"
git push
```

If connected to Render, the service can automatically deploy the new GitHub commit depending on your deployment settings.

---

# 📊 Example User Flow

A normal user experience can look like:

```text
👤 User:

https://www.tiktok.com/@user/video/123456789


🤖 MAX:

🔍 Processing TikTok...


🤖 MAX:

⚡ Downloading...


🤖 MAX:

✅ Download Complete!


🎬 Video
📦 18.5 MB
🎥 HD Quality


[📥 Download]
```

---

# 📦 Large File Example

```text
👤 User:

https://www.tiktok.com/...


🤖 MAX:

⏳ Downloading...


🤖 MAX:

📦 Large file detected

⚠️ File size: 72.3 MB
⚠️ Telegram limit: 50 MB


🔗 Catbox Upload Complete

https://files.catbox.moe/xxxx.mp4


[📥 Download]
```

---

# 🎵 MP3 Example

```text
👤 User:

https://www.tiktok.com/...


🤖 MAX:

🎵 Extracting audio...


🤖 MAX:

✅ MP3 Ready

🎵 Audio
📦 4.2 MB


[📥 Download MP3]
```

---

# 🖼️ Slideshow Example

```text
👤 User:

https://www.tiktok.com/...


🤖 MAX:

🖼️ Slideshow detected

⏳ Downloading images...


🤖 MAX:

✅ Slideshow ready

📸 12 images
```

---

# 📈 Future Features

Possible future improvements:

- 🌐 Web dashboard
- 📊 Advanced analytics
- 👥 User database
- 🏆 Advanced ranking system
- 💰 Premium subscriptions
- 🔑 API keys
- 🚀 Redis caching
- 🗄️ PostgreSQL
- 📱 Mobile application
- 🤖 AI-powered moderation
- 🔍 Advanced search
- 📥 Batch downloading
- 🎨 Custom themes
- 🌍 Multi-language support
- 🔔 Notifications
- 📡 Webhooks
- ⚙️ Advanced admin dashboard

---

# 🧩 Recommended Production Architecture

For a larger MAX deployment:

```text
                           ┌──────────────────┐
                           │    Telegram      │
                           │      Users       │
                           └────────┬─────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │    MAX Bot       │
                           │     Python       │
                           └────────┬─────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          ┌────────────┐    ┌────────────┐    ┌────────────┐
          │ TikTok/API │    │ PostgreSQL │    │   Redis    │
          └──────┬─────┘    └────────────┘    └────────────┘
                 │
                 ▼
          ┌────────────┐
          │  FFmpeg    │
          └──────┬─────┘
                 │
          ┌──────┴──────┐
          │             │
          ▼             ▼
     ┌─────────┐   ┌─────────┐
     │Telegram │   │ Catbox  │
     └─────────┘   └─────────┘
```

---

# 🧪 Development

Run the bot locally during development:

```bash
python bot.py
```

For debugging:

```bash
python -u bot.py
```

Check the terminal output for errors.

---

# 🧹 Clean Project

Before pushing to GitHub, make sure you don't accidentally upload:

```text
.env
bot_data.json
*.mp4
*.mp3
__pycache__
venv
```

Use:

```bash
git status
```

before committing.

---

# 📋 Deployment Checklist

Before deploying MAX, verify:

```text
☐ bot.py exists
☐ TIKTOKLOGO.png exists
☐ requirements.txt exists
☐ Dockerfile exists
☐ render.yaml exists
☐ .env.example exists
☐ .gitignore exists
☐ BOT_TOKEN configured
☐ ADMIN_IDS configured
☐ FFmpeg available
☐ CATBOX_ENABLED configured
☐ MAX_TELEGRAM_SIZE_MB configured
☐ No secrets committed to GitHub
```

---

# 🚀 Quick Deploy Checklist

```text
1. Create Telegram bot with BotFather
          ↓
2. Copy BOT_TOKEN
          ↓
3. Upload MAX to GitHub
          ↓
4. Include TIKTOKLOGO.png
          ↓
5. Open Render
          ↓
6. Create Blueprint
          ↓
7. Select GitHub repository
          ↓
8. Add environment variables
          ↓
9. Deploy
          ↓
10. Check Render logs
          ↓
11. Open Telegram
          ↓
12. Send /start
          ↓
13. MAX ONLINE 🚀
```

---

# 📜 License

This project is licensed under the **MIT License**.

You may use, modify and distribute the project according to the terms of the MIT License.

---

# ⚠️ Disclaimer

This project is intended for downloading content that you have permission to download.

Users are responsible for complying with:

- TikTok's Terms of Service
- Copyright laws
- Content ownership
- Privacy rights
- Applicable local laws
- Applicable platform rules

Do not use MAX to download, store or redistribute content without appropriate permission.

The developers are not responsible for misuse of the software.

---

# ⭐ Support MAX

If you like the project:

⭐ Star the repository  
🍴 Fork the repository  
🐛 Report bugs  
💡 Suggest features  
🚀 Submit improvements  

---

<p align="center">

## 💎 MAX — Fast. Powerful. Simple.

**Made with ❤️ and ⚡**

⭐ **Star the repository if you like MAX!**

</p>