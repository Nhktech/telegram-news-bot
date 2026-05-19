import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from google import genai

# =========================
# ENV VARIABLES
# =========================
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# CHECKS
if not API_ID:
    raise Exception("API_ID not found in environment variables")
if not API_HASH:
    raise Exception("API_HASH not found in environment variables")
if not SESSION:
    raise Exception("SESSION not found in environment variables")
if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY not found in environment variables")

API_ID = int(API_ID)

# =========================
# GEMINI CLIENT
# =========================
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def translate_to_hausa(text):
    try:
        prompt = f"""
Translate the following English news into SIMPLE, CLEAR Hausa.

Rules:
- Keep meaning accurate
- Do NOT add extra info
- Keep paragraphs same structure
- Make it natural Hausa

TEXT:
{text}
"""

        response = gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"Translation error: {str(e)}"

# =========================
# TELETHON CLIENT
# =========================
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

source_channel = "presstv"
target_channel = "yaamahdi_hausa"

# =========================
# HANDLER
# =========================
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    msg = event.message
    text = msg.message or ""

    if not text:
        return

    translated = translate_to_hausa(text[:4000])

    caption = f"""📰 LABARAI

{translated}

📢 @yaamahdi_hausa"""

    try:
        if msg.media:
            await client.send_file(target_channel, msg.media, caption=caption)
        else:
            await client.send_message(target_channel, caption)
    except Exception as e:
        print("Send error:", e)

# =========================
# START BOT
# =========================
async def main():
    await client.start()
    print("Bot is running...")
    await client.run_until_disconnected()

asyncio.run(main())
