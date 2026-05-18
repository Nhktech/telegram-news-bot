import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from google import genai

# =========================
# ENV VARIABLES
# =========================
API_ID = int(os.getenv("39334379"))
API_HASH = os.getenv("7fb7d9bd7c531ebba0b9b434c9744009")
SESSION = os.getenv("1BJWap1wBu2WWbvqpofNeEexW_hUVS8BPJ6OrPwZ7eZV0CNKw5NTJwjv4KB02B_M9TVn73m0jPOdN2oHKpkfrlzaxPedIYPQxtkhvNNSXkpQbFFR2hOMIleeF5GPVgWrnWXfIJGuKgmzCEJ1o1PIb2WXWUXCLMtcE0zBV3TK1FqCWqd7aTB3C8QpdZeAuXlXdPRlU6AO2U80bH82LwqNTyEfmwzpWid9bP_WamiZufeeIJY7TJTdrex0zaaVgZNud7GMuBkquNLVitQ_1FGLL1Yqky92XdhS3fvYtzjLKyWu2M5PgHNtnSlKz8Nr5_MJNd8yS92-PAXXLJUsURAoR0M40ntcQD2w=")
GEMINI_API_KEY = os.getenv("AIzaSyBFDOPwPb53MBowrRgBg87VN1hjsISg7M0")

if not SESSION:
    raise Exception("SESSION not found")
if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY not found")

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

    if text:
        translated = translate_to_hausa(text[:4000])

        caption = f"""📰 LABARAI

{translated}

📢 @yaamahdi_hausa"""
    else:
        caption = None

    if msg.media:
        await client.send_file(target_channel, msg.media, caption=caption)
    else:
        await client.send_message(target_channel, caption)

# =========================
# START BOT
# =========================
async def main():
    await client.start()
    print("Bot is running...")
    await client.run_until_disconnected()

asyncio.run(main())
