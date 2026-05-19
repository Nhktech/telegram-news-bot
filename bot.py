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

if not all([API_ID, API_HASH, SESSION, GEMINI_API_KEY]):
    raise Exception("Missing environment variables")

API_ID = int(API_ID)

# =========================
# GEMINI CLIENT
# =========================
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-1.5-flash"

def translate_to_hausa(text):
    try:
        prompt = f"""
Translate the following English news into SIMPLE, CLEAR Hausa.

Rules:
- Keep meaning accurate
- Do NOT add extra info
- Keep paragraph structure
- Make it natural Hausa

TEXT:
{text}
"""

        response = gemini_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        if response and response.candidates:
            return response.candidates[0].content.parts[0].text

        return "Translation failed"

    except Exception as e:
        return f"Translation error: {str(e)}"

# =========================
# BREAKING NEWS DETECTOR
# =========================
def is_breaking(text):
    text = text.lower()
    return any(keyword in text for keyword in [
        "breaking",
        "urgent",
        "alert",
        "just in",
        "now",
        "update",
        "developing"
    ])

# =========================
# TELEGRAM CLIENT
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

    # =========================
    # PRIORITY DELAY SYSTEM
    # =========================
    if is_breaking(text):
        delay = 0
    else:
        delay = 10

    await asyncio.sleep(delay)

    translated = translate_to_hausa(text[:4000])

    caption = f"""📰 LABARAI

{translated}

📢 @yaamahdi_hausa"""

    try:
        if msg.media:
            await client.send_file(
                target_channel,
                file=msg.media,
                caption=caption
            )
        else:
            await client.send_message(
                target_channel,
                caption
            )

    except Exception as e:
        print("Send error:", e)

# =========================
# START BOT
# =========================
async def main():
    await client.start()
    print("Bot is running...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
