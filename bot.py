import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from deep_translator import GoogleTranslator

api_id = 39334379
api_hash = "7fb7d9bd7c531ebba0b9b434c9744009"

session = os.getenv("SESSION")

client = TelegramClient(StringSession(session), api_id, api_hash)

source_channel = "presstv"
target_channel = "yaamahdi_hausa"

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    msg = event.message
    text = msg.message or ""

    if text:
        translated = GoogleTranslator(
            source='en',
            target='ha'
        ).translate(text[:3000])

        caption = f"📰 LABARAI\n\n{translated}\n\n📢 @yaamahdi_hausa"
    else:
        caption = None

    if msg.media:
        await client.send_file(target_channel, msg.media, caption=caption)
    else:
        await client.send_message(target_channel, caption)

with client:
    print("Bot is running...")
    client.run_until_disconnected()
