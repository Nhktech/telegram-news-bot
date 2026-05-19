import os
import asyncio
from pyrogram import Client, filters
from google import genai
from deep_translator import GoogleTranslator

# ==========================================
# 1. SAITA BAYANAN USERBOT DA API KEYS (DAGA CLOUD)
# ==========================================
# Yanzu muna amfani da 'os.environ' domin daukar bayanan daga sabar intanet (Cloud)
# Wannan ya fi tsaro, ba sai ka rubuta su a fili a nan ba.
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SOURCE_CHANNEL = int(os.environ.get("SOURCE_CHANNEL", 0))
DEST_CHANNEL = int(os.environ.get("DEST_CHANNEL", 0))

# Tada Pyrogram Client ta hanyar amfani da Session String
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
    """
    Wannan function din zai amshi rubutu ya fassara zuwa Hausa
    ta amfani da Gemini. Idan ya kasa, zai koma kan Google Translate.
    """
    if not text:
        return ""
    
    try:
        # Prompt na musamman don tabbatar da Hausa mai kyau
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
        # Fallback: Amfani da Google Translator idan AI bai yi aiki ba
        try:
            translator = GoogleTranslator(source='auto', target='hausa')
            return translator.translate(text)
        except Exception as fallback_error:
            print(f"[-] Fallback ma ya kasa: {fallback_error}")
            return text # Idan duka biyun suka kasa, mayar da rubutun asali

# ==========================================
# 3. TSARIN AUTO-REPOST
# ==========================================
@app.on_message(filters.chat(SOURCE_CHANNEL))
async def handle_posts(client, message):
    try:
        # Ciro asalin rubutun (ko da na text ne ko kuma caption na hoto/video)
        original_text = message.text or message.caption or ""
        
        hausa_text = ""
        
        if original_text:
            print("[*] An ga sabon post, ana fassara...")
            # Yin amfani da asyncio don gudun hana bot din yin wasu ayyukan yayin jiran fassara
            hausa_text = await asyncio.to_thread(fassara_zuwa_hausa, original_text)

        # Pyrogram's copy() zai dauki duk wani nau'in sako (hoto, video, document, text) 
        # ya tura shi kai tsaye da sabon caption
        if original_text:
            await message.copy(DEST_CHANNEL, caption=hausa_text)
        else:
            # Idan sakon bashi da text kwata-kwata (misali hoto kawai ba caption)
            await message.copy(DEST_CHANNEL)

        print("[+] An samu nasarar turawa zuwa sabon channel!")

    except Exception as e:
        print(f"[-] An samu matsala wajen turawa: {e}")

# ==========================================
# 4. TADA USERBOT
# ==========================================
if __name__ == "__main__":
    print("[*] Userbot yana aiki. Ana jiran sakonni...")
    print("[*] Latsa Ctrl+C don tsayarwa.")
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[*] An tsayar da Userbot.")
    except Exception as e:
        print(f"[-] Wata babbar matsala ta faru: {e}")
