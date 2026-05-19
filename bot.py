import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from google import genai
from google.genai import types  # An sanya wannan don daidaita saurin tsaro

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

# GYARA 1: Muna amfani da gemini-2.5-flash-lite saboda shi ne mafi sauri (low latency)
MODEL_NAME = "gemini-2.5-flash-lite"

# GYARA 2: Mun maida wannan aikin ya zama Async don kada bot din ya dinga daskarewa (blocking)
async def translate_to_hausa(text):
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

        # GYARA 3: Rage tsauraran matakan tsaro na sakan lokaci (Safety settings optimization)
        # Wannan zai sa Gemini ya ba da amsa nan take ba tare da dogon nazarin tace kalmomi ba
        config = types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        )

        # Gudanar da kiran API a cikin background thread don kada ya hana Telegram sauri
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config
            )
        )

        if response and response.text:
            return response.text

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
    # GYARA 4: An cire jinkirin sakan 10 an maida shi sakan 1 don kiyaye saurin sakan goma (10s window)
    if is_breaking(text):
        delay = 0
    else:
        delay = 1

    await asyncio.sleep(delay)

    # Kiran sabon async fassara
    translated = await translate_to_hausa(text[:4000])

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
