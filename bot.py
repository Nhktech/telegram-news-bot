import asyncio
import json
import re
import time
import os
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from pyrogram.errors import FloodWait
from pyrogram.enums import ParseMode

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
    api_hash=API_HASH,
    sleep_threshold=300
)

async def send_long_message(message, text):
    if not text: 
        return
    for i in range(0, len(text), 4000):
        while True:
            try:
                if message:
                    await message.reply_text(text[i:i+4000])
                else:
                    await app.send_message(TARGET_CHANNEL, text[i:i+4000])
                await asyncio.sleep(2.5)  
                break  
            except FloodWait as e:
                print(f"⏳ Telegram ta nemi a dakata na daƙiƙa {e.value}. Injin yana jiran ta...")
                await asyncio.sleep(e.value + 2)

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
        msg_date_str = msg.date.strftime("%Y-%m-%d %I:%M %p")
        
        if msg.media_group_id:
            if msg.media_group_id not in media_groups:
                new_item = {"texts": [], "media_ids": [], "has_video": False, "has_photo": False, "date": msg_date_str}
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
                "has_photo": bool(msg.photo),
                "date": msg_date_str
            })
            
    for item in raw_items:
        joined_texts = "\n\n".join(item["texts"])
        if joined_texts.strip():
            item["text"] = f"🗓 LOKACI: {item['date']}\n{joined_texts}"
        else:
            item["text"] = f"🗓 LOKACI: {item['date']}\n[HOTO KO BIDIYO ZALLA]"

    TEMP_DATA = raw_items 
    GLOBAL_CLUSTERS = []
    TRANSLATED_QUEUE = []
    CURRENT_INDEX = 0
    CURRENT_BATCH_TEXT = ""
    LAST_FETCH_TIME = end_dt.strftime("%Y-%m-%d %H:%M:%S") 
    
    rubutu_don_gemini = ""
    for lamba, labari in enumerate(raw_items):
        txt = str(labari["text"]).replace(f"🗓 LOKACI: {labari['date']}\n", "").strip()
        if txt and txt != "[HOTO KO BIDIYO ZALLA]":
            gajeren_labari = " ".join(txt.split()[:30])
            rubutu_don_gemini += f"[{lamba}] (Aka wallafa: {labari['date']}): {gajeren_labari}...\n"
        else:
            rubutu_don_gemini += f"[{lamba}] (Aka wallafa: {labari['date']}): [HOTO KO BIDIYO ZALLA]\n"
            
    prompt = f"""Kai babban Edita ne. Ga gajerun kanun labarai masu lamba a kasa. 
Hada lambobin wadanda suke magana akan abu daya ta amfani da hankali da kuma kwanan wata.
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
    
    prompt = f"""Kai babban Edita ne. Ga rukunonin labarai guda {len(batch_clusters)} a kasa. 
Aikin ka:
1. Idan rukunin yana da guntatakin labarai fiye da daya, KA NARKE SU GUDANAR DA CIKAKKEN LABARI GUDA DAYA a turance ba gutsure-gutsure ba. 
2. Ka kawo wannan narkarren Turancin a sama sannan ka kawo fassarar Hausa a kasa. 
🚫 DOKA: Kada ka kirkiri sunayen bogi (fake names).

DOLA TA MUSAMMAN: Dole ne ka rufe amsar kowane rukuni a cikin Tag na <LABARI> da </LABARI>.

Misali na yadda zaka tsara amsarka:
<LABARI>
**English**
(Cikakken labarin Turancin da ka narke anan)

**Hausa**
(Fassarar Hausar anan)
</LABARI>

Ga labaran:\n"""
    
    for i, cluster in enumerate(batch_clusters):
        raw_texts_list = [TEMP_DATA[idx]["text"].strip() for idx in cluster if idx < len(TEMP_DATA) and TEMP_DATA[idx]["text"].strip()]
        stacked_raw_text = "\n\n".join(raw_texts_list)
        if not stacked_raw_text.strip(): stacked_raw_text = "[WANNAN RUKUNIN HOTO NE/BIDIYO ZALLA, RUBUTA 'Babu Rubutu']"
        prompt += f"\n\n--- RUKUNI NA {index + i + 1} ---\n{stacked_raw_text}\n"

    await message.reply_text(f"⏳ **MATAKI 1: ANA SHIRYA RUKUNI NA {index + 1} ZUWA {end_idx} (DAGA CIKIN {len(GLOBAL_CLUSTERS)})**\n\nKwafi wannan ka kaiwa Gemini:\n👇👇👇")
    await send_long_message(message, prompt)
    await message.reply_text("👉 **Idan ka fassara a Gemini, lika a nan ka danna `.shigar`**")
    
    BOT_STATE = "WAITING_FASSARA_1"
    ajiye_bayanai()

# ==========================================
# 3. LURA DA SAKONNINKA DA .shigar (MAI SASSAUCI & XML TAGS)
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
        await message.reply_text("✅ *Na ajiye wannan guntun. Idan sun cika tsarin da kake bukata, rubuta `.shigar`*")

@app.on_message(filters.me & filters.command("shigar", prefixes="."))
async def shigar_fassara(client, message):
    if not message.from_user or message.chat.id != message.from_user.id: return
    global CURRENT_BATCH_TEXT, CURRENT_INDEX, TRANSLATED_QUEUE, BOT_STATE

    if BOT_STATE not in ["WAITING_FASSARA_1", "WAITING_FASSARA_2"]: return
    if not CURRENT_BATCH_TEXT.strip(): return await message.reply_text("⚠️ Babu rubutu tukunna.")

    raw_translations = re.findall(r'<LABARI>(.*?)</LABARI>', CURRENT_BATCH_TEXT, flags=re.IGNORECASE | re.DOTALL)
    translations = [t.strip() for t in raw_translations if t.strip()]
    
    if BOT_STATE == "WAITING_FASSARA_1":
        expected_count = min(CURRENT_INDEX + BATCH_SIZE, len(GLOBAL_CLUSTERS)) - CURRENT_INDEX
        if len(translations) != expected_count:
            await message.reply_text(f"⚠️ Matsala a Mataki na 1: Ina jiran <LABARI> guda {expected_count}, amma na gano guda {len(translations)} kacal.\nKa tabbatar Gemini ya sa <LABARI> da </LABARI>. Na goge na yanzu, sake turawa.")
            CURRENT_BATCH_TEXT = ""
            return

        # ========================================================
        # SABON SALON ZALLAR RUBUTU (TEXT-BASED JOURNALISM)
        # ========================================================
        prompt_gyara = f"""Kai kwararren marubucin jarida ne kuma marubucin labarai a shafukan yanar gizo. Ga fassarar wasu labarai guda {len(translations)}.
Aikinka shine ka cire duk wani kamshin "fassarar na'ura" daga wannan Hausar, ka mayar da shi RUBUTACCEN LABARI wanda zai rike hankalin masu karatu. Bar Turancin yadda yake a narke.

🌟 SALON RUBUTU (READING TONE): 
Tunda labarin A RUBUCE yake, dole ne ka tsara shi don masu karatu (readers). Ka yi amfani da jimloli masu jan hankali irin su: "Jama'a...", "Shin kun ci karo da...", "Wani abin al'ajabi...", "Ku karanta ku ga...", "Ba za ku yarda da wannan ba...". 
🚫 DOKA TA MUSAMMAN: Kada ka yi amfani da kalaman masu yin magana a baki, rediyo ko bidiyo (kamar 'ku saurari wannan', ko 'masu kallo'). Ka sani cewa KAWAR da wannan zai tabbatar labarin ya dace da masu karatu a Telegram. 
✨ TSARI: Ka bayar da sarari mai kyau tsakanin sakin layi don gamsar da masu karatu. Ka yi amfani da BOLD (**rubutu**) a kan muhimman sunaye.

DOLA TA MUSAMMAN: Dole ne ka rufe gyaran kowane rukuni a cikin Tag na <LABARI> da </LABARI>.

Misali:
<LABARI>
**English**
(Turancin da na baka)

**Hausa**
(Gyararren fassarar Hausar don masu karatu a nan)
</LABARI>

Ga fassarar:\n"""
        for i, fassara in enumerate(translations):
            prompt_gyara += f"\n\n--- RUKUNI NA {CURRENT_INDEX + i + 1} ---\n{fassara}\n"

        await message.reply_text(f"✅ An karbi Rukunin Farko! \n\n⏳ **MATAKI 2 (GYARAN FUSKA DON MASU KARATU):** Kwafi wannan ka kaiwa Gemini:\n👇👇👇")
        await send_long_message(message, prompt_gyara)
        await message.reply_text("👉 **ZABI YANA HANNUNKA:** Turo gyararren rubutun (wanda ke cikin <LABARI>...</LABARI>) daya-bayan-daya, ko gaba daya sannan ka danna `.shigar`")
        BOT_STATE = "WAITING_FASSARA_2"
        CURRENT_BATCH_TEXT = ""
        ajiye_bayanai()
        return

    # MATAKI NA 2: TSARA RUBUTUN KARSHE
    elif BOT_STATE == "WAITING_FASSARA_2":
        received_count = len(translations)
        batch_end_idx = min((CURRENT_INDEX // BATCH_SIZE) * BATCH_SIZE + BATCH_SIZE, len(GLOBAL_CLUSTERS))
        remaining_in_batch = batch_end_idx - CURRENT_INDEX

        if received_count > remaining_in_batch:
            await message.reply_text(f"⚠️ Kuskure: Ka turo labarai guda {received_count} alhali guda {remaining_in_batch} kacal suka rage a wannan rukunin. Na goge, sake turo daidai.")
            CURRENT_BATCH_TEXT = ""
            return
            
        if received_count == 0:
            await message.reply_text("⚠️ Ban gano wani labari a cikin <LABARI>...</LABARI> ba. Tabbatar Gemini ya sa wannan alamar. Na goge, sake turawa.")
            CURRENT_BATCH_TEXT = ""
            return

        await message.reply_text(f"✅ An karbi Gyararren Rubutu guda {received_count}! Ana jera su a layin watsawa...")

        for fassara in translations:
            cluster_idx = CURRENT_INDEX
            cluster = GLOBAL_CLUSTERS[cluster_idx]
            
            if "babu rubutu" in fassara.lower() and len(fassara) < 50:
                final_text = ""
            else:
                has_video = any(TEMP_DATA[idx].get("has_video", False) for idx in cluster if idx < len(TEMP_DATA))
                has_photo = any(TEMP_DATA[idx].get("has_photo", False) for idx in cluster if idx < len(TEMP_DATA))
                
                media_icon = ""
                if has_video:
                    media_icon = "🎥 "
                elif has_photo:
                    media_icon = "📸 "
                
                final_text = (
                    f"{media_icon}{fassara.strip()}\n\n"
                    f"🔗 https://t.me/yaamahdi_hausa"
                )
                
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
            
            CURRENT_INDEX += 1 

        CURRENT_BATCH_TEXT = ""
        ajiye_bayanai()

        if not IS_POSTING: app.loop.create_task(watsa_labarai_a_hankali())

        if CURRENT_INDEX == len(GLOBAL_CLUSTERS):
            BOT_STATE = "POSTING"
            ajiye_bayanai()
            await message.reply_text(f"🎉 **AN KAMMALA SHIGAR DA KOMAI!**\nYanzu zai karasa watsa labaran a asirce zuwa **{TARGET_CHANNEL}**.")
        elif CURRENT_INDEX % BATCH_SIZE == 0:
            await message.reply_text("✅ **An gama wannan rukunin.** Ana shigo da rukunin gaba...")
            await asyncio.sleep(2)
            await tura_prompt_na_fassara(message, CURRENT_INDEX)
        else:
            rem = batch_end_idx - CURRENT_INDEX
            await message.reply_text(f"⏳ **Akwai sauran labarai {rem} a wannan rukunin.**\nZaka iya kawo na gaba idan ka gama duba shi.")

# ==========================================
# 4. INJIN WATSAWA DA SABON TSARIN "FALLBACK"
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
            try:
                fetched = await app.get_messages(SOURCE_CHANNEL, media_ids)
                if not isinstance(fetched, list): fetched = [fetched]
                combined_media = [m for m in fetched if m and not m.empty]
            except Exception as e:
                print(f"⚠️ Kuskuren kwaso media: {e}")
            
        try:
            if not combined_media:
                if caption: await app.send_message(TARGET_CHANNEL, caption)
                if remainder:
                    await asyncio.sleep(2.5)
                    await send_long_message(message=None, text=remainder) 
                        
            elif len(combined_media) == 1:
                await combined_media[0].copy(TARGET_CHANNEL, caption=caption)
                if remainder:
                    await asyncio.sleep(2.5)
                    await send_long_message(message=None, text=remainder)
            else:
                media_group = []
                for i, m in enumerate(combined_media):
                    cap = caption if i == 0 else ""
                    if m.photo:
                        media_group.append(InputMediaPhoto(m.photo.file_id, caption=cap))
                    elif m.video:
                        media_group.append(InputMediaVideo(m.video.file_id, caption=cap))

                if media_group:
                    await app.send_media_group(TARGET_CHANNEL, media_group)
                else:
                    if caption: await app.send_message(TARGET_CHANNEL, caption)

                if remainder:
                    await asyncio.sleep(2.5)
                    await send_long_message(message=None, text=remainder)
                    
        except FloodWait as e:
            print(f"⏳ FloodWait wajen watsawa! Jira na daƙiƙa {e.value}")
            await asyncio.sleep(e.value + 2)
            continue 
            
        except Exception as e:
            print(f"⚠️ Kuskuren watsa labari (Zan gwada tura rubutu zalla): {e}")
            try:
                if caption:
                    await app.send_message(TARGET_CHANNEL, f"⚠️ [Babu Media - Matsalar Tsari]\n\n{caption}", parse_mode=ParseMode.DISABLED)
                if remainder:
                    await asyncio.sleep(2.5)
                    for i in range(0, len(remainder), 4000):
                        await app.send_message(TARGET_CHANNEL, remainder[i:i+4000], parse_mode=ParseMode.DISABLED)
                        await asyncio.sleep(2)
            except Exception as e2:
                await app.send_message(DEST_CHANNEL, f"❌ Wani labari ya ki shiga gaba daya!\nDalili: {str(e)[:100]}")

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
