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
