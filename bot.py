import os
import sys
import asyncio
from pyrogram import Client, filters
from google import genai
from deep_translator import GoogleTranslator

# ==========================================
# 1. SAITA BAYANAN USERBOT DA API KEYS (DAGA CLOUD)
# ==========================================
def get_channel_id(env_var_name):
    """
    Wannan function din zai taimaka wajen fahimtar ko ka saka ID (lamba),
    'me' (Saved Messages), ko username (@sunanchannel).
    """
    val = os.environ.get(env_var_name)
    if not val:
        print(f"[-] Kuskure: Baka saita {env_var_name} ba a Environment Variables!")
        sys.exit(1)
    
    val = val.strip()
    if val.lower() == "me":
        return "me"
    
    try:
        return int(val)
    except ValueError:
        return val # Zai dawo da username idan ba lamba bane

try:
    API_ID = int(os.environ.get("API_ID"))
except (TypeError, ValueError):
    print("[-] Kuskure: Baka saita API_ID daidai ba (yana bukatar zama lamba)!")
    sys.exit(1)

SOURCE_CHANNEL = get_channel_id("SOURCE_CHANNEL")
DEST_CHANNEL = get_channel_id("DEST_CHANNEL")

API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not all([API_HASH, SESSION_STRING, GEMINI_API_KEY]):
    print("[-] Kuskure: Akwai bayanan sirri (kamar HASH, SESSION, ko API KEY) da baka saka ba!")
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
        # Ciro asalin rubutun
        original_text = message.text or message.caption or ""
        
        hausa_text = ""
        
        if original_text:
            print("[*] An ga sabon post, ana fassara...")
            hausa_text = await asyncio.to_thread(fassara_zuwa_hausa, original_text)

        # Turawa zuwa sabon channel da fassarar
        if original_text:
            await message.copy(DEST_CHANNEL, caption=hausa_text)
        else:
            await message.copy(DEST_CHANNEL)

        print(f"[+] An samu nasarar turawa zuwa {DEST_CHANNEL}!")

    except Exception as e:
        print(f"[-] An samu matsala wajen turawa: {e}")

# ==========================================
# 4. TADA USERBOT
# ==========================================
if __name__ == "__main__":
    print("[*] Userbot yana aiki. Ana jiran sakonni...")
    print(f"[*] Ana duba: {SOURCE_CHANNEL} | Ana turawa zuwa: {DEST_CHANNEL}")
    try:
        app.run()
    except Exception as e:
        print(f"[-] Wata babbar matsala ta faru: {e}")
