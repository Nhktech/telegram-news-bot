import asyncio
import json
import re
import time
import os
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo

# ==========================================
# SAITA BAYANANKA TA HANYAR "ENVIRONMENT VARIABLES"
# ==========================================
try:
    API_ID = int(os.environ.get("API_ID"))
    API_HASH = os.environ.get("API_HASH")
    TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")
    SESSION_STRING = os.environ.get("SESSION_STRING")
except Exception as e:
    print("⚠️ Baka saka API_ID, API_HASH, TARGET_CHANNEL ko SESSION_STRING a cikin Values din Server ba!")

SOURCE_CHANNEL = "@PressTV"
DEST_CHANNEL = "me"  

app = Client(
    name="my_account", 
    session_string=SESSION_STRING, 
    api_id=API_ID, 
    api_hash=API_HASH
)

async def send_long_message(message, text):
    if not text: return
    for i in range(0, len(text), 4000):
        await message.reply_text(text[i:i+4000])
        await asyncio.sleep(0.5)

# ==========================================
# MA'ADANAR RIKON BAYANAI 
# ==========================================
TEMP_DATA = []
GLOBAL_CLUSTERS = []
CURRENT_INDEX = 0
BOT_STATE = "IDLE"  

BATCH_SIZE = 10 
CURRENT_BATCH_TEXT = "" 
TRANSLATED_QUEUE = [] 
LAST_FETCH_TIME = None 
IS_POSTING = False 

STATE_FILE = "bot_state.json"

def ajiye_bayanai():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({
                "TEMP_DATA": TEMP_DATA,
                "GLOBAL_CLUSTERS": GLOBAL_CLUSTERS,
                "CURRENT_INDEX": CURRENT_INDEX,
                "BOT_STATE": BOT_STATE,
                "TRANSLATED_QUEUE": TRANSLATED_QUEUE,
                "LAST_FETCH_TIME": LAST_FETCH_TIME
            }, f)
    except: pass

def dauko_bayanai():
    global TEMP_DATA, GLOBAL_CLUSTERS, CURRENT_INDEX, BOT_STATE, TRANSLATED_QUEUE, LAST_FETCH_TIME
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                TEMP_DATA = data.get("TEMP_DATA", [])
                GLOBAL_CLUSTERS = data.get("GLOBAL_CLUSTERS", [])
                CURRENT_INDEX = data.get("CURRENT_INDEX", 0)
                BOT_STATE = data.get("BOT_STATE", "IDLE")
                TRANSLATED_QUEUE = data.get("TRANSLATED_QUEUE", [])
                LAST_FETCH_TIME = data.get("LAST_FETCH_TIME", None)
                return True
        except: pass
    return False

# ==========================================
# 1. UMARNIN .kwaso
# ==========================================
@app.on_message(filters.me & filters.command("kwaso", prefixes="."))
async def kwaso_labarai(client, message):
    if not message.from_user or message.chat.id != message.from_user.id: return
    global TEMP_DATA, GLOBAL_CLUSTERS, CURRENT_INDEX, BOT_STATE, TRANSLATED_QUEUE, CURRENT_BATCH_TEXT, LAST_FETCH_TIME
    
    args = message.text.split()
    
    if len(args) == 4 and args[1].lower() == "yau":
        if not LAST_FETCH_TIME:
            return await message.reply_text("⚠️ Babu tarihin lokacin baya. Saka cikakken lokaci.")
        try:
            start_dt = datetime.strptime(LAST_FETCH_TIME, "%Y-%m-%d %H:%M:%S")
            today_str = datetime.now().strftime("%Y-%m-%d")
            end_dt = datetime.strptime(f"{today_str} {args[2]} {args[3].upper()}", "%Y-%m-%d %I:%M %p")
        except:
            return await message.reply_text("⚠️ Kuskure. Misali: `.kwaso yau 06:00 AM`")
            
    elif len(args) == 7:
        try:
            start_dt = datetime.strptime(f"{args[1]} {args[2]} {args[3].upper()}", "%Y-%m-%d %I:%M %p")
            end_dt = datetime.strptime(f"{args[4]} {args[5]} {args[6].upper()}", "%Y-%m-%d %I:%M %p")
        except:
            return await message.reply_text("⚠️ Kuskuren kwanan wata.")
    else:
        return await message.reply_text("⚠️ Tsari:\nCikakke: `.kwaso [Rana] [Lokaci] [AM/PM] [Rana] [Lokaci] [AM/PM]`\nSauki: `.kwaso yau [Lokaci] [AM/PM]`")

    await message.reply_text(f"⏳ *Ana kwaso labarai daga {start_dt} zuwa {end_dt}...*")
    
    messages_in_range = []
    async for msg in app.get_chat_history(SOURCE_CHANNEL, limit=None):
        if msg.date is None: continue
        msg_date = msg.date.replace(tzinfo=None)
        if msg_date > end_dt: continue
        elif start_dt <= msg_date <= end_dt: messages_in_range.append(msg)
        else: break

    if not messages_in_range:
        return await message.reply_text("❌ Babu labari a wannan lokacin.")

    messages_in_range.reverse()
    raw_items = []
    media_groups = {}
    for msg in messages_in_range:
        text = msg.text or msg.caption or ""
        if msg.media_group_id:
            if msg.media_group_id not in media_groups:
                new_item = {"texts": [], "media_ids": [], "has_video": False, "has_photo": False}
                media_groups[msg.media_group_id] = new_item
                raw_items.append(new_item) 
            group = media_groups[msg.media_group_id]
            if text and text not in group["texts"]: group["texts"].append(text)
            group["media_ids"].append(msg.id)
            if msg.video: group["has_video"] = True
            if msg.photo: group["has_photo"] = True
        else:
            raw_items.append({
                "texts": [text] if text else [], 
                "media_ids": [msg.id] if msg.media else [],
                "has_video": bool(msg.video),
                "has_photo": bool(msg.photo)
            })
            
    for item in raw_items:
        item["text"] = "\n\n".join(item["texts"])

    TEMP_DATA = raw_items 
    GLOBAL_CLUSTERS = []
    TRANSLATED_QUEUE = []
    CURRENT_INDEX = 0
    CURRENT_BATCH_TEXT = ""
    LAST_FETCH_TIME = end_dt.strftime("%Y-%m-%d %H:%M:%S") 
    
    rubutu_don_gemini = ""
    for lamba, labari in enumerate(raw_items):
        txt = str(labari["text"]).strip()
        if txt:
            gajeren_labari = " ".join(txt.split()[:30])
            rubutu_don_gemini += f"[{lamba}]: {gajeren_labari}...\n"
        else:
            rubutu_don_gemini += f"[{lamba}]: [HOTO KO BIDIYO ZALLA]\n"
            
    prompt = f"""Kai babban Edita ne. Ga gajerun kanun labarai masu lamba a kasa. 
Hada lambobin wadanda suke magana akan abu daya ko kuma suke da alaka komin kankantarta alakar kuwa
DOKA: Mayar da amsa a JSON OBJECT kamar haka: {{"clusters": [[0, 2], [1], [3, 4]]}}
Kanun Labaran:\n{rubutu_don_gemini}"""

    await message.reply_text(f"✅ **An kwaso labarai guda {len(raw_items)}!**\n\nKwafi wannan ka kai wa Gemini:")
    await send_long_message(message, prompt)
    await message.reply_text("👉 **Idan Gemini ya baka JSON din, LIKA SHI A NAN KA TURA.**")
    
    BOT_STATE = "WAITING_JSON"
    ajiye_bayanai() 

# ==========================================
# 2. INJIN BADA PROMPT NA FASSARA 
# ==========================================
async def tura_prompt_na_fassara(message, index):
    global TEMP_DATA, GLOBAL_CLUSTERS, BOT_STATE, BATCH_SIZE
    
    end_idx = min(index + BATCH_SIZE, len(GLOBAL_CLUSTERS))
    batch_clusters = GLOBAL_CLUSTERS[index:end_idx]
    
    prompt = f"""Kai babban Edita ne kuma kwararren mai fassara labarai. Ga rukunonin labarai guda 10 a kasa. Kowane rukuni yana da guntatakin labarai.

Aikin ka:

1. Narkar da guntatakin kowane rukuni su koma CIKAKKEN LABARI GUDA DAYA a turance (Cohesive English Story).

2. Fassara wannan labarin daga Turanci zuwa Hausa ta hanyar yin **'fassarar ma'ana' (contextual translation)**..

3. Fitarda fassarar mai santsi da dadin karatu wadda ta dace da aikin jarida da kafafen yada labarai na zamani.
4. KADA ka yi fassarar kalma-da-kalma (literal translation). Sake tsara ginin jimlar yadda zai dace da harshen Hausa na asali.
5. KADA ka taba kirkira ko amfani da sunayen bogi (fake names); idan babu suna a asalin labarin, yi amfani da lafazin da ya dace.

DOKA: Tsara amsarka kamar haka don kowane rukuni, sannan ka raba su da kalmar ===RUKUNI===:


English

(Cikakken labarin Turancin a nan)


Hausa

(Fassarar Hausar a nan)


===RUKUNI===


Ga labaran:\n"""
    
    for i, cluster in enumerate(batch_clusters):
        raw_texts_list = [TEMP_DATA[idx]["text"].strip() for idx in cluster if idx < len(TEMP_DATA) and TEMP_DATA[idx]["text"].strip()]
        stacked_raw_text = "\n\n".join(raw_texts_list)
        if not stacked_raw_text.strip(): stacked_raw_text = "[WANNAN RUKUNIN HOTO NE/BIDIYO ZALLA, RUBUTA 'Babu Rubutu']"
        prompt += f"\n\n--- RUKUNI NA {index + i + 1} ---\n{stacked_raw_text}\n"

    await message.reply_text(f"⏳ **MATAKI 1: ANA SHIRYA RUKUNI NA {index + 1} ZUWA {end_idx} (DAGA CIKIN {len(GLOBAL_CLUSTERS)})**\n\nKwafi wannan ka kaiwa Gemini ya narkar da Turancin kuma ya fassara:\n👇👇👇")
    await send_long_message(message, prompt)
    await message.reply_text("👉 **Idan ka fassara duka a Gemini, lika su anan ka tura, sannan ka danna `.shigar`**")
    
    BOT_STATE = "WAITING_FASSARA_1"
    ajiye_bayanai()

# ==========================================
# 3. LURA DA SAKONNINKA DA .shigar
# ==========================================
@app.on_message(filters.me & ~filters.regex(r"^\."))
async def saurare_rubutu(client, message):
    if not message.from_user or message.chat.id != message.from_user.id: return
    global GLOBAL_CLUSTERS, CURRENT_INDEX, BOT_STATE, CURRENT_BATCH_TEXT
    
    if BOT_STATE == "WAITING_JSON":
        try:
            json_match = re.search(r'\{.*\}', message.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                GLOBAL_CLUSTERS = data.get("clusters", [])
            else: return 
        except:
            return await message.reply_text(f"⚠️ **Ba JSON ba ne!** Sake duba.")

        CURRENT_INDEX = 0
        CURRENT_BATCH_TEXT = ""
        await message.reply_text(f"✅ **An karbi JSON!** An gano rukuni {len(GLOBAL_CLUSTERS)}.")
        await tura_prompt_na_fassara(message, CURRENT_INDEX)

    elif BOT_STATE in ["WAITING_FASSARA_1", "WAITING_FASSARA_2"]:
        CURRENT_BATCH_TEXT += "\n\n" + message.text
        await message.reply_text("✅ *Na ajiye wannan guntun. Idan sun cika, rubuta `.shigar`*")

@app.on_message(filters.me & filters.command("shigar", prefixes="."))
async def shigar_fassara(client, message):
    if not message.from_user or message.chat.id != message.from_user.id: return
    global CURRENT_BATCH_TEXT, CURRENT_INDEX, TRANSLATED_QUEUE, BOT_STATE

    if BOT_STATE not in ["WAITING_FASSARA_1", "WAITING_FASSARA_2"]: return
    if not CURRENT_BATCH_TEXT.strip(): return await message.reply_text("⚠️ Babu rubutu tukunna.")

    translations = [t.strip() for t in re.split(r'===RUKUNI===', CURRENT_BATCH_TEXT, flags=re.IGNORECASE) if t.strip()]
    end_idx = min(CURRENT_INDEX + BATCH_SIZE, len(GLOBAL_CLUSTERS))
    expected_count = end_idx - CURRENT_INDEX

    if len(translations) != expected_count:
        await message.reply_text(f"⚠️ Matsala: Ina jiran rukuni {expected_count}, amma na gano {len(translations)}. Ka tabbatar da kalmar ===RUKUNI=== na nan a tsakaninsu. Na goge, sake turawa.")
        CURRENT_BATCH_TEXT = ""
        return

    # MATAKI NA 1: Samar da Prompt din Gyaran Fuska
    if BOT_STATE == "WAITING_FASSARA_1":
        prompt_gyara = f"""Kai kwararren masanin harshen Hausa ne. Ga labaran Turanci da fassararsu guda {len(translations)}.
Aikinka shine ka duba fassarar Hausar, ka gyara ta ta koma zallar Hausa mai dadi da santsi ba tare da sauya ma'anar asali ba. Turancin kuma ka bar shi yadda yake.
🚫 DOKA TA MUSAMMAN: Kada ka taba kirkirar sunayen bogi (fake names).

DOLA: Ka tsara amsarka kamar haka don kowane rukuni:
**English**
(Asalin Turancin da na baka)

**Hausa**
(Gyararren fassarar Hausar a nan)

===RUKUNI===

Ga labaran:\n"""
        for i, fassara in enumerate(translations):
            prompt_gyara += f"\n\n--- RUKUNI NA {CURRENT_INDEX + i + 1} ---\n{fassara}\n"

        await message.reply_text(f"✅ An karbi Rukunin Farko! \n\n⏳ **MATAKI 2 (GYARAN FUSKA):** Kwafi wannan ka kaiwa Gemini ya tace maka zuwa zallar Hausa:\n👇👇👇")
        await send_long_message(message, prompt_gyara)
        await message.reply_text("👉 **Idan ya baka gyararren rubutun, lika anan, ka sake danna `.shigar` don a watsa.**")
        BOT_STATE = "WAITING_FASSARA_2"
        CURRENT_BATCH_TEXT = ""
        ajiye_bayanai()
        return

    # MATAKI NA 2: Daukar Cikakken Rubutun da Turawa Queue
    elif BOT_STATE == "WAITING_FASSARA_2":
        await message.reply_text("✅ An karbi Gyararren Rubutun! Ana jera su a layin watsawa...")

        for i, fassara in enumerate(translations):
            cluster_idx = CURRENT_INDEX + i
            cluster = GLOBAL_CLUSTERS[cluster_idx]
            
            if "babu rubutu" in fassara.lower() and len(fassara) < 50:
                final_text = ""
            else:
                # INJIN SAKA EMOJI DANGANE DA NAU'IN LABARI
                has_video = any(TEMP_DATA[idx].get("has_video", False) for idx in cluster if idx < len(TEMP_DATA))
                has_photo = any(TEMP_DATA[idx].get("has_photo", False) for idx in cluster if idx < len(TEMP_DATA))
                
                media_icon = ""
                if has_video:
                    media_icon = "🎥 " # Ya fi baiwa bidiyo fifiko idan an samu duka biyun
                elif has_photo:
                    media_icon = "📸 "
                    
                final_text = f"{media_icon}{fassara.strip()}\n\n🔗 https://t.me/yaamahdi_hausa"
                
            caption_text = ""
            remainder_text = ""
            if len(final_text) <= 1024:
                caption_text = final_text
            else:
                split_idx = final_text.rfind('\n\n', 0, 1024)
                if split_idx == -1: split_idx = final_text.rfind('\n', 0, 1024)
                if split_idx == -1: split_idx = 1024
                caption_text = final_text[:split_idx].strip()
                remainder_text = final_text[split_idx:].strip()

            combined_media_ids = [m for idx in cluster if idx < len(TEMP_DATA) for m in TEMP_DATA[idx]["media_ids"]][:10]

            TRANSLATED_QUEUE.append({
                "caption": caption_text,
                "remainder": remainder_text,
                "media_ids": combined_media_ids
            })

        CURRENT_INDEX = end_idx
        CURRENT_BATCH_TEXT = ""
        ajiye_bayanai()

        if CURRENT_INDEX < len(GLOBAL_CLUSTERS):
            await message.reply_text("✅ **An gama na baya.** Ana shigo da rukunin gaba...")
            await asyncio.sleep(2)
            await tura_prompt_na_fassara(message, CURRENT_INDEX)
        else:
            BOT_STATE = "POSTING"
            ajiye_bayanai()
            await message.reply_text(f"🎉 **AN KAMMALA KOMAI!**\nYanzu zai fara watsa labaran a asirce zuwa **{TARGET_CHANNEL}**, kowane bayan minti 2 da rabi.")
            if not IS_POSTING: app.loop.create_task(watsa_labarai_a_hankali())

# ==========================================
# 4. INJIN WATSAWA (Minti 2.5 = 150s) & KARIYA
# ==========================================
async def watsa_labarai_a_hankali():
    global TRANSLATED_QUEUE, BOT_STATE, IS_POSTING
    IS_POSTING = True
    
    while len(TRANSLATED_QUEUE) > 0:
        if BOT_STATE == "PAUSED":
            await asyncio.sleep(5)
            continue
            
        item = TRANSLATED_QUEUE[0] 
        caption = item['caption']
        remainder = item['remainder']
        media_ids = item['media_ids']
        
        combined_media = []
        if media_ids:
            fetched = await app.get_messages(SOURCE_CHANNEL, media_ids)
            if not isinstance(fetched, list): fetched = [fetched]
            combined_media = fetched
            
        try:
            if not combined_media:
                if caption: await app.send_message(TARGET_CHANNEL, caption)
                if remainder:
                    await asyncio.sleep(1)
                    await send_long_message(message=None, text=remainder) 
                    for i in range(0, len(remainder), 4000):
                        await app.send_message(TARGET_CHANNEL, remainder[i:i+4000])
                        
            elif len(combined_media) == 1:
                await combined_media[0].copy(TARGET_CHANNEL, caption=caption)
                if remainder:
                    await asyncio.sleep(1)
                    for i in range(0, len(remainder), 4000):
                        await app.send_message(TARGET_CHANNEL, remainder[i:i+4000])
            else:
                media_group = [InputMediaPhoto(m.photo.file_id, caption=caption if i==0 else "") if m.photo else InputMediaVideo(m.video.file_id, caption=caption if i==0 else "") for i, m in enumerate(combined_media)]
                if media_group: await app.send_media_group(TARGET_CHANNEL, media_group)
                if remainder:
                    await asyncio.sleep(1)
                    for i in range(0, len(remainder), 4000):
                        await app.send_message(TARGET_CHANNEL, remainder[i:i+4000])
        except Exception as e:
            print(f"⚠️ Kuskuren tura labari: {e}")

        TRANSLATED_QUEUE.pop(0)
        ajiye_bayanai()
        
        if len(TRANSLATED_QUEUE) > 0 and BOT_STATE != "PAUSED":
            await asyncio.sleep(150) 
            
    BOT_STATE = "IDLE"
    IS_POSTING = False
    ajiye_bayanai()
    await app.send_message(DEST_CHANNEL, f"🎊 **AIKI YA KAMMALA DUKANTA!** An watsa komai a tasharka.")

# ==========================================
# 5. UMARNI MASU SAUKI (.dakata, .cigaba, .goge, .fasa)
# ==========================================
@app.on_message(filters.me & filters.command("dakata", prefixes="."))
async def dakatar_da_aiki(client, message):
    global BOT_STATE
    if BOT_STATE == "POSTING":
        BOT_STATE = "PAUSED"
        ajiye_bayanai()
        await message.reply_text("🛑 **An Dakatar da Watsa Labaran!** Rubuta `.cigaba` idan zaka ci gaba.")

@app.on_message(filters.me & filters.command("cigaba", prefixes="."))
async def cigaba_aiki(client, message):
    global BOT_STATE
    if dauko_bayanai():
        if len(TRANSLATED_QUEUE) > 0:
            BOT_STATE = "POSTING"
            ajiye_bayanai()
            await message.reply_text(f"♻️ **An Dawo Da Aikin Watsawa!** Akwai sauran labarai {len(TRANSLATED_QUEUE)}.")
            if not IS_POSTING: app.loop.create_task(watsa_labarai_a_hankali())
        elif TEMP_DATA:
            await message.reply_text(f"♻️ **An Dawo Da Aikin Baya!** Muna kan rukuni na {CURRENT_INDEX + 1}.")
            if BOT_STATE == "WAITING_JSON": await message.reply_text("👉 Ina jiran JSON.")
            elif BOT_STATE == "WAITING_FASSARA_1": await tura_prompt_na_fassara(message, CURRENT_INDEX)
            elif BOT_STATE == "WAITING_FASSARA_2": await message.reply_text("👉 Ina jiran Gyararren Hausa.")
    else:
        await message.reply_text("❌ Babu aiki a ajiye.")

@app.on_message(filters.me & filters.command("fasa", prefixes="."))
async def fasa_aiki(client, message):
    global TEMP_DATA, GLOBAL_CLUSTERS, CURRENT_INDEX, BOT_STATE, TRANSLATED_QUEUE, CURRENT_BATCH_TEXT
    TEMP_DATA, GLOBAL_CLUSTERS, TRANSLATED_QUEUE, CURRENT_INDEX, CURRENT_BATCH_TEXT, BOT_STATE = [], [], [], 0, "", "IDLE"
    ajiye_bayanai()
    await message.reply_text("🛑 **An watsar da aikin gaba daya!**")

@app.on_message(filters.me & filters.command("goge", prefixes="."))
async def goge_sakanni(client, message):
    cmd_text = message.text.replace(".goge", "").strip()
    if not cmd_text: return await message.reply_text("⚠️ Saka kalma ko kwanan wata. Misali: `.goge RUKUNI`")
    
    args = cmd_text.split()
    if len(args) == 6: 
        try:
            start_dt = datetime.strptime(f"{args[0]} {args[1]} {args[2].upper()}", "%Y-%m-%d %I:%M %p")
            end_dt = datetime.strptime(f"{args[3]} {args[4]} {args[5].upper()}", "%Y-%m-%d %I:%M %p")
            count = 0
            async for msg in app.get_chat_history("me"):
                if msg.date and start_dt <= msg.date.replace(tzinfo=None) <= end_dt:
                    await msg.delete(); count += 1; await asyncio.sleep(0.5)
            await message.reply_text(f"✅ An goge sakonni {count}.")
        except: await message.reply_text("⚠️ Kuskuren kwanan wata.")
    else: 
        count = 0
        keyword = cmd_text.lower()
        await message.reply_text(f"⏳ Ana goge sakonni masu kalmar '{keyword}'...")
        async for msg in app.get_chat_history("me"):
            if msg.text and keyword in msg.text.lower():
                await msg.delete(); count += 1; await asyncio.sleep(0.5)
            elif msg.caption and keyword in msg.caption.lower():
                await msg.delete(); count += 1; await asyncio.sleep(0.5)
        await app.send_message("me", f"✅ An goge sakonni {count} masu dauke da kalmar nan.")

if __name__ == "__main__":
    dauko_bayanai()
    app.run()
