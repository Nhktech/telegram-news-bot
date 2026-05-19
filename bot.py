import os
import sys
import asyncio
from pyrogram import Client, filters
from google import genai
from deep_translator import GoogleTranslator

# ==========================================
# 1. SAITA BAYANAN USERBOT DA API KEYS (DAGA CLOUD)
# ==========================================
# Function don gane lamba (ID) ko rubutu ("me" ko "@username")
def parse_channel(val):
    if not val:
        return ""
    try:
        return int(val)
    except ValueError:
        return val

# Karbar bayanai daga Environment Variables tare da tsaro
try:
    API_ID = int(os.environ.get("API_ID", 0))
except ValueError:
    print("[-] Kuskure: Baka saita API_ID daidai ba!")
    sys.exit(1)

API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Yanzu zai amshi ko wane irin tsari ne ("me", lamba, ko username)
SOURCE_CHANNEL = parse_channel(os.environ.get("SOURCE_CHANNEL"))
DEST_CHANNEL = parse_channel(os.environ.get("DEST_CHANNEL"))

if not all([API_HASH, SESSION_STRING, GEMINI_API_KEY, SOURCE_CHANNEL, DEST_CHANNEL]):
    print("[-] Kuskure: Akwai bayanan sirri da baka saka ba a Tranger Cloud!")
    sys.exit(1)

# Tada Pyrogram Client
app = Client(
    name="fassara_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Tada Gemini Client don fassara
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. TSARIN FASSARA TARE DA FALLBACK
# ==========================================
def fassara_zuwa_hausa(text):
    if not text:
        return ""
    
    try:
        prompt = f"""Fassara wannan rubutun zuwa harshen Hausa mai sauƙin fahimta. 
        Ka kula da kiyaye ma'anar asali ba tare da fassarar inji (literal translation) ba. 
        Kar ka sanya wani ƙarin bayani naku na AI ko gaisuwa, kawai fassarar zalla: 

        {text}"""
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text

    except Exception as e:
        print(f"[-] Gemini ya samu matsala: {e}. Ana amfani da Fallback...")
        try:
            translator = GoogleTranslator(source='auto', target='hausa')
            return translator.translate(text)
        except Exception as fallback_error:
            print(f"[-] Fallback ma ya kasa: {fallback_error}")
            return text

# ==========================================
# 3. TSARIN AUTO-REPOST
# ==========================================
@app.on_message(filters.chat(SOURCE_CHANNEL))
async def handle_posts(client, message):
    try:
        # Matakin tsaro don hana bot din yin loop idan an samu kuskure
        if str(message.chat.id) == str(DEST_CHANNEL) or message.chat.username == str(DEST_CHANNEL).replace("@", ""):
            return

        # Ciro asalin rubutun
        original_text = message.text or message.caption or ""
        hausa_text = ""
        
        if original_text:
            print("[*] An ga sabon post, ana fassara...")
            hausa_text = await asyncio.to_thread(fassara_zuwa_hausa, original_text)

        # Turawa zuwa inda aka saita (DEST_CHANNEL)
        if original_text:
            await message.copy(DEST_CHANNEL, caption=hausa_text)
        else:
            await message.copy(DEST_CHANNEL)

        print("[+] An samu nasarar turawa!")

    except Exception as e:
        print(f"[-] An samu matsala wajen turawa: {e}")

# ==========================================
# 4. TADA USERBOT
# ==========================================
if __name__ == "__main__":
    print("[*] Userbot yana aiki. Ana jiran sakonni...")
    print(f"[*] Source: {SOURCE_CHANNEL} | Destination: {DEST_CHANNEL}")
    try:
        app.run()
    except Exception as e:
        print(f"[-] Wata babbar matsala ta faru: {e}")
