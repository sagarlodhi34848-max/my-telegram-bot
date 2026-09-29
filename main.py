import asyncio
import os
import time
import datetime
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ChatType
from telegram.error import RetryAfter, TimedOut, NetworkError
import logging
import re
import random
from telegram.request import HTTPXRequest

from telegram.error import Conflict as TelegramConflict

# ═══════════════════════════════════════════════════════════════
#  𝐓ꫝʀɢꫀᴛ  FONT ENGINE
#  Converts all bot output text to the 𝐓ꫝʀɢꫀᴛ Unicode font style.
#  Uppercase  →  Mathematical Bold  (𝐀–𝐙)
#  Lowercase  →  Cham / Small-Cap mix  (ꫝ ʙ ᥴ ᴅ ꫀ …)
#  Numbers, emojis, symbols, already-styled Unicode → unchanged
# ═══════════════════════════════════════════════════════════════
_TGT_LOWER_FROM = "abcdefghijklmnopqrstuvwxyz"
_TGT_LOWER_TO   = "ꫝʙᥴᴅꫀꜰɢʜɪᴊᴋʟꪑꪀꪮᴘǫʀꜱᴛᴜᴠᴡꪛʏᴢ"
_TGT_LOWER_TBL  = str.maketrans(_TGT_LOWER_FROM, _TGT_LOWER_TO)
_TGT_UPPER_MAP  = {chr(ord("A") + i): chr(0x1D400 + i) for i in range(26)}

def to_tgt_font(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    converted = [_TGT_UPPER_MAP.get(ch, ch) for ch in text]
    return "".join(converted).translate(_TGT_LOWER_TBL)

# Monkey-patch telegram send methods so every bot reply auto-converts
from telegram import Message as _TgMsg, Bot as _TgBot
from telegram.constants import ParseMode as _PM

_orig_reply_text   = _TgMsg.reply_text
_orig_send_message = _TgBot.send_message

async def _patched_reply_text(self, text, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if parse_mode not in (_PM.HTML, "HTML", "html"):
        text = to_tgt_font(text)
    return await _orig_reply_text(self, text, *args, **kwargs)

async def _patched_send_message(self, chat_id, text, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if parse_mode not in (_PM.HTML, "HTML", "html"):
        text = to_tgt_font(text)
    return await _orig_send_message(self, chat_id, text, *args, **kwargs)

_TgMsg.reply_text   = _patched_reply_text
_TgBot.send_message = _patched_send_message
# ═══════════════════════════════════════════════════════════════


try:
    from pyrogram import Client as PyroClient
    from pyrogram.raw import functions as pyro_functions
    from pyrogram.errors import FloodWait as PyroFloodWait
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)

class _SuppressConflict(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "Conflict" in msg or "terminated by other getUpdates" in msg:
            return False
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            exc_name = type(exc).__name__
            exc_str = str(exc)
            if "Conflict" in exc_name or "Conflict" in exc_str or "terminated by other getUpdates" in exc_str:
                return False
        return True

logging.getLogger("telegram").addFilter(_SuppressConflict())
logging.getLogger("telegram.ext._updater").addFilter(_SuppressConflict())
logging.getLogger("telegram.ext._application").addFilter(_SuppressConflict())
logging.getLogger("httpx").setLevel(logging.CRITICAL)

for _h in logging.root.handlers:
    _h.addFilter(_SuppressConflict())

OWNER_ID = 6686436142



API_ID        = "37678680"
API_HASH      = "25698468c2dd2a90f188717605893f80"  
SESSION_STRING = "Ghjjhgg"  # Paste your Pyrogram session string here


USERBOT = None  # Pyrogram MTProto client (auto-started when SESSION_STRING is set)

SUDO_IDS = [
    #6533652838 ,
]

BOT_TOKENS = [t for t in [
"8645097088:AAH7t1QZgCREJa-cgfdS-3ss3snzNek1X-0",

"8801406072:AAFZyP5Kd6opM7LQHFnvd4B_rvwA-S_B3u4",

"8805100005:AAFWxIRGnocFBeWeMHlfc4bAlySKephhcD0",

"8922227406:AAH8XPnykfAg6P70Boo7uYNMCmvPM6HkBoU",

"8590479598:AAHKheUD1S6E99PahTQZqsQpBlpUZq5iMq0",

"8898336568:AAGNFY8FDv7cvpT2OMbjf2-aUnbPuRJVAP8",

"8717914985:AAHqXhYx1NeXkrJGpfFFp_4ONbO1Ct3M4dY",

"8623329053:AAG-5pVCm5vxJ5ljdig-YNeQdMI2q0rylwE",

"8523403683:AAEp6QkhuBDyf-lO70e4AqBzFB2O2Zd_7WE",

"8673168374:AAHvo3f_D7DbFyQSf4J0Q8MvfTI-KCqfGj0",

] if t.strip()]

if not BOT_TOKENS:
    print("ERROR: No bot tokens configured.")
    exit(1)

ALL_BOT_IDS = set()
ALL_BOTS = {}
SYSTEM_START_TIME = time.time()

BOT_START_TIMES = {}

GLOBAL_STATS = {
    "messages_sent": 0,
    "name_changes": 0,
    "replies_sent": 0,
    "fwd_spam_sent": 0,
}

KNOWN_CHATS = set()

HEART_EMOJIS = ['❤️', '🧡', '💛', '💚', '💙', '💜', '🤎', '🖤', '🤍', '💘', '💝', '💖', '💗', '💓', '💞', '💌', '💕', '💟', '♥️', '❣️', '💔']

MOON_EMOJIS = ['🌙', '🌛', '🌜', '🌝', '🌚', '🌕', '🌖', '🌗', '🌘', '🌑', '🌒', '🌓', '🌔', '✨', '⭐', '🌟', '💫', '🌠']

NC_MOON_MESSAGES = [
    "🌑 {target} 𝙏𝙍𝙔 𝙈𝘼𝘼 𝙆𝙄 𝘾𝙃𝙃𝙐𝙏 𝙁𝘼𝘼𝘿 𝘿𝙐𝙉𝙂𝙄 𝙍𝙉𝘿𝙔𝙆𝙀 🌑",
    "🌔 {target} 𝙇𝙐𝙉 𝘾𝙃𝙃𝙐𝙎 𝙍𝙉𝘿𝙔𝙆𝙀 𝘽𝘾𝙃𝙀🌔",
    "🌕 {target} 𝙏𝙍𝙔 𝘽𝘼𝙃𝙀𝙉 𝙆𝘼 𝘽𝙃𝙊𝙎𝘿𝘼🌕",
    "🌖 {target} 𝙃𝘼𝙆𝙇𝙀 𝙏𝙍𝙔𝙔 𝙈𝘼𝘼 𝘾𝙃𝙃𝙊𝘿 𝘿𝙐𝙉𝙂𝙄🌖",
    "🌗 {target} 𝘼𝘼𝙅𝘼 𝙍𝙉𝘿𝙔𝙆𝙀 𝙏𝙐𝙅𝙃𝙀 𝙎𝙋𝘼𝙈𝙈𝙀𝙍 𝘽𝘼𝙉𝘼𝙏𝙄 𝙃𝙐🌗",
    "🌘 {target} 𝙍𝙊𝙊 𝙍𝙉𝘿𝙔𝙆𝙀 𝙏𝙍𝙔𝙔 𝘽𝙃𝙀𝙉 𝙆𝙄 𝙆𝘼𝙇𝙄 𝘾𝙃𝙐𝙏🌘",
    "🌙 {target} 𝙂𝘼𝙔 𝙎𝙇𝘼𝙑𝙀 𝙍𝘼𝙉𝘿🌙",
]

RAND_NC_MESSAGES = [
    "{target} ᴛᴇʀɪ बहन ʀɴᴅ ❤️",
    "{target} ᴛᴇʀɪ  मां  ʀɴᴅ 🧡",
    "{target} ᴛᴇʀɪ चाची ʀɴᴅ 💛",
    "{target} ᴛᴇʀɪ मोसी ʀɴᴅ 💙",
    "{target} ᴛᴇʀɪ ननद ʀɴᴅ 💜",
    "{target} ᴛᴇʀɪ दादी ʀɴᴅ 🤎",
    "{target} ᴛᴇʀɪ बुआ ʀɴᴅ 🖤",
    "{target} ᴛᴇʀɪ बीबी ʀɴᴅ 🤍",
    "{target} ᴛᴇʀɪ जेठानी ʀɴᴅ 🩷",
    "{target} ᴛᴇʀɪ मोसी ʀɴᴅ 🩵",
    "{target} ᴛᴇʀɪ बहन ʀɴᴅ 🩶",
    "{target} ᴛᴇʀɪ बीबी ʀɴᴅ ♥️",
]

# ======== FAST NC LOOP (EMOJI + TEXT) ========
FAST_NC_MESSAGES = [
    "༼😍༽{target} ᴛᴇʀɪ ᴍᴀᴀ ʀɴᴅ",
    "༼🙃༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʀɴᴅ",
    "༼😗༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ʀɴᴅ",
    "༼😙༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ʀɴᴅ",
    "༼😚༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼🤗༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼🙂༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼😋༽{target} ᴛᴇʀɪ ʙᴇʜᴇɴ ᴄʜᴜᴅ",
    "༼🫣༽ {target} ɢᴀɴᴅᴜ ʙsᴅᴋ",
    "༼🤫༽ {target} ᴄʜᴜᴛɪʏᴀ ʟᴀᴠᴅᴇ",
    "༼🥸༽ {target} ʀᴀɴᴅɪ ᴋᴀ ʙᴀᴄʜᴀ",
    "༼😺༽ {target} ᴍᴄ ʙᴄ ᴋᴀ ʙᴀᴄʜᴀ",
    "༼😸༽ {target} ʙsᴅᴋ ᴛᴇʀɪ ᴍᴀᴀ",
    "༼😹༽ {target} ᴄʜᴀᴍᴀʀ ʜɪᴊᴅᴀ",
    "༼😻༽ {target} ᴋᴜᴛɪʏᴀ ᴋᴀ ʙᴀᴄʜᴀ",
    "༼😼༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴀ ʙʜᴏsᴅᴀ",
    "༼🐼༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴀ ʙʜᴏsᴅᴀ",
    "༼🙉༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅᴇ",
    "༼🙊༽ {target} ᴍᴀᴅᴀʀᴄʜᴏᴅ ᴛᴜ",
    "༼🐱༽ {target} ʜɪᴊᴅᴇ ᴋᴀ ʙᴀᴄʜᴀ",
    "༼🐶༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ᴄʜᴜᴅᴇ",
    "༼🦊༽ {target} ʙᴋʟ ᴛᴜ ᴋʜᴜᴅ",
    "༼🐨༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʀᴀɴᴅɪ",
    "༼🐉༽ {target} ʀᴀɴᴅɪ ᴋᴀ ʙᴀᴄʜᴀ",
    "༼🐢༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼🐬༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ʀɴᴅ",
    "༼🦈༽ {target} ᴄʜᴜᴛɪʏᴀ ᴛᴜ",
    "༼🐞༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴜᴛɪʏᴀ",
    "༼🕷️༽ {target} ɢᴀɴᴅᴜ ʜɪᴊᴅᴀ",
    "༼🦂༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʀɴᴅ",
    "༼✨༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼🌟༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ᴄʜᴜᴅ",
    "༼⭐༽ {target} ᴍᴄ ʙᴄ ᴛᴜ",
    "༼☀️༽ {target} ʙsᴅᴋ ᴛᴇʀɪ ᴍᴀᴀ",
    "༼🌈༽ {target} ʀᴀɴᴅɪ ᴋᴀ ʙᴀᴄʜᴀ",
    "༼🪐༽ {target} ᴄʜᴜᴛɪʏᴀ ᴛᴇʀɪ ᴍᴀᴀ",
    "༼🌍༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅᴋᴇ ᴀᴀ",
    "༼🌏༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ᴋʜᴜʟɪ",
    "༼☄️༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʟᴀᴠᴅᴇ",
    "༼💫༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ʟᴀᴠᴅᴇ",
    "༼🍀༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴀ ʙʜᴏsᴅᴀ",
    "༼🌹༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʀɴᴅ",
    "༼🌺༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ʀɴᴅ",
    "༼🌻༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼🌼༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴜᴛɪʏᴀ",
    "༼🎁༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴛᴜᴍᴋᴄ",
    "༼💎༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼❤️༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʀᴀɴᴅɪ",
    "༼💛༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ʀᴀɴᴅɪ",
    "༼💚༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅᴇ",
    "༼💕༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʙʜᴏsᴅɪ",
    "༼💞༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ᴄʜᴜᴅᴇ",
    "༼💓༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼💗༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴜᴛɪʏᴀ",
    "༼💖༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʜɪᴊᴅɪ",
    "༼🤎༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʀɴᴅ",
    "༼💘༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʙsᴅᴋ",
    "༼🏍️༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼🚓༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴘᴀᴋᴅɪ",
    "༼✈️༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴜᴅ ɢᴀʏɪ",
    "༼🚁༽ {target} ᴛᴇʀɪ ʙᴇʜᴇɴ ᴜᴅɪ",
    "༼⛵༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴅᴜʙɪ",
    "༼🚗༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜᴅ",
    "༼🎶༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴀ ʀᴀɢ",
    "༼🎹༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ʙᴀᴊᴀ",
    "༼🥁༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴀ ᴅᴏʟ",
    "༼🍔༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴀ ʙᴜʀɢᴇʀ",
    "༼🍜༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴀ ᴀᴛᴀ",
    "༼💵༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴋɪᴍᴀᴛ",
    "༼💸༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴋɪᴍᴀᴛ ᴢᴇʀᴏ",
    "༼🏦༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴅɪᴠᴀʟɪᴀ",
    "༼🧃༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴜs",
    "༼🍫༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴄʜᴏᴄᴏ ʀɴᴅ",
    "༼💰༽ {target} ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴋɪᴍᴀᴛ",
    "༼📉༽ {target} ᴛᴇʀɪ ᴀᴜᴋᴀᴛ ᴊɪʀᴏ",
]

FLAG_EMOJIS = ['🏳️', '🏴', '🚩', '🎌', '🏁', '🏳️‍🌈', '🏴‍☠️', '⛳', '🎏', '🏴󠁧󠁢󠁥󠁮󠁧󠁿', '🏴󠁧󠁢󠁳󠁣󠁴󠁿', '🏴󠁧󠁢󠁷󠁬󠁳󠁿', '🇦🇨', '🇦🇩', '🇦🇪', '🇦🇫', '🇦🇬', '🇦🇮', '🇦🇱', '🇦🇲', '🇦🇴', '🇦🇶', '🇦🇷', '🇦🇸', '🇦🇹', '🇦🇺', '🇦🇼', '🇦🇽', '🇦🇿', '🇧🇦', '🇧🇧', '🇧🇩', '🇧🇪', '🇧🇫', '🇧🇬', '🇧🇭', '🇧🇮', '🇧🇯', '🇧🇱', '🇧🇲', '🇧🇳', '🇧🇴', '🇧🇶', '🇧🇷', '🇧🇸', '🇧🇹', '🇧🇻', '🇧🇼', '🇧🇾', '🇧🇿', '🇨🇦', '🇨🇨', '🇨🇩', '🇨🇫', '🇨🇬', '🇨🇭', '🇨🇮', '🇨🇰', '🇨🇱', '🇨🇲', '🇨🇳', '🇨🇴', '🇨🇵', '🇨🇷', '🇨🇺', '🇨🇻', '🇨🇼', '🇨🇽', '🇨🇾', '🇨🇿', '🇩🇪', '🇩🇬', '🇩🇯', '🇩🇰', '🇩🇲', '🇩🇴', '🇩🇿', '🇪🇦', '🇪🇨', '🇪🇪', '🇪🇬', '🇪🇭', '🇪🇷', '🇪🇸', '🇪🇹', '🇪🇺', '🇫🇮', '🇫🇯', '🇫🇰', '🇫🇲', '🇫🇴', '🇫🇷', '🇬🇦', '🇬🇧', '🇬🇩', '🇬🇪', '🇬🇫', '🇬🇬', '🇬🇭', '🇬🇮', '🇬🇱', '🇬🇲', '🇬🇳', '🇬🇵', '🇬🇶', '🇬🇷', '🇬🇸', '🇬🇹', '🇬🇺', '🇬🇼', '🇬🇾', '🇭🇰', '🇭🇲', '🇭🇳', '🇭🇷', '🇭🇹', '🇭🇺', '🇮🇨', '🇮🇩', '🇮🇪', '🇮🇱', '🇮🇲', '🇮🇳', '🇮🇴', '🇮🇶', '🇮🇷', '🇮🇸', '🇮🇹', '🇯🇪', '🇯🇲', '🇯🇴', '🇯🇵', '🇰🇪', '🇰🇬', '🇰🇭', '🇰🇮', '🇰🇲', '🇰🇳', '🇰🇵', '🇰🇷', '🇰🇼', '🇰🇾', '🇰🇿', '🇱🇦', '🇱🇧', '🇱🇨', '🇱🇮', '🇱🇰', '🇱🇷', '🇱🇸', '🇱🇹', '🇱🇺', '🇱🇻', '🇱🇾', '🇲🇦', '🇲🇨', '🇲🇩', '🇲🇪', '🇲🇫', '🇲🇬', '🇲🇭', '🇲🇰', '🇲🇱', '🇲🇲', '🇲🇳', '🇲🇴', '🇲🇵', '🇲🇶', '🇲🇷', '🇲🇸', '🇲🇹', '🇲🇺', '🇲🇻', '🇲🇼', '🇲🇽', '🇲🇾', '🇲🇿', '🇳🇦', '🇳🇨', '🇳🇪', '🇳🇫', '🇳🇬', '🇳🇮', '🇳🇱', '🇳🇴', '🇳🇵', '🇳🇷', '🇳🇺', '🇳🇿', '🇴🇲', '🇵🇦', '🇵🇪', '🇵🇫', '🇵🇬', '🇵🇭', '🇵🇰', '🇵🇱', '🇵🇲', '🇵🇳', '🇵🇷', '🇵🇸', '🇵🇹', '🇵🇼', '🇵🇾', '🇶🇦', '🇷🇪', '🇷🇴', '🇷🇸', '🇷🇺', '🇷🇼', '🇸🇦', '🇸🇧', '🇸🇨', '🇸🇩', '🇸🇪', '🇸🇬', '🇸🇭', '🇸🇮', '🇸🇯', '🇸🇰', '🇸🇱', '🇸🇲', '🇸🇳', '🇸🇴', '🇸🇷', '🇸🇸', '🇸🇹', '🇸🇻', '🇸🇽', '🇸🇾', '🇸🇿', '🇹🇦', '🇹🇨', '🇹🇩', '🇹🇫', '🇹🇬', '🇹🇭', '🇹🇯', '🇹🇰', '🇹🇱', '🇹🇲', '🇹🇳', '🇹🇴', '🇹🇷', '🇹🇹', '🇹🇻', '🇹🇼', '🇹🇿', '🇺🇦', '🇺🇬', '🇺🇲', '🇺🇳', '🇺🇸', '🇺🇾', '🇺🇿', '🇻🇦', '🇻🇨', '🇻🇪', '🇻🇬', '🇻🇮', '🇻🇳', '🇻🇺', '🇼🇫', '🇼🇸', '🇽🇰', '🇾🇪', '🇾🇹', '🇿🇦', '🇿🇲', '🇿🇼']

NC_FLAG_MESSAGES = [
    "{target} 〘🇰🇵〙",
    "{target} 〘🇰🇷〙",
    "{target} 〘🇵🇰〙",
    "{target} 〘🇳🇬〙",
    "{target} 〘🇲🇰〙",
    "{target} 〘🇳🇫〙",
    "{target} 〘🇨🇾〙",
    "{target} 〘🇮🇳〙",
    "{target} 〘🇧🇩〙",
    "{target} 〘🇦🇫〙",
    "{target} 〘🇸🇴〙",
    "{target} 〘🇸🇾〙",
    "{target} 〘🇱🇾〙",
    "{target} 〘🇾🇪〙",
    "{target} 〘🇮🇶〙",
    "{target} 〘🇷🇺〙",
    "{target} 〘🇨🇳〙",
    "{target} 〘🇵🇸〙",
    "{target} 〘🇲🇲〙",
    "{target} 〘🇭🇹〙",
]

TIME_NC_MESSAGES = [
    " {target} 12:382:229",
    " {target}  12:382:230",
    " {target}  12:382:231 ",
    " {target}  12:382:232",
    " {target}  12:382:233",
    "{target}   12:382:234  ",
    " {target}  12:382:235",
    " {target}  12:382:236",
    " {target}  12:382:237",
    " {target}  12:382:238",
    " {target}  12:382:239",
    "{target}   12:382:240  ",
    " {target}  12:382:241",
    " {target}  12:382:242",
    " {target}  12:382:243",
    " {target}  12:382:244",
    "{target}   12:382:245  ",
]

NC_CURLY_MESSAGES = [
    "{target} 𝐑𝐀𝐍𝐃➿",
    "{target} 𝐂𝐇𝐀𝐌𝐀𝐃➿",
    "{target} 𝐁𝐇𝐎𝐒𝐀𝐃𝐈𝐊𝐄➿",
    "{target} 𝐑𝐍𝐃𝐘𝐊𝐄➿",
    "{target} 𝐇𝐈𝐉𝐑𝐄➿",
    "{target} 𝐁𝐇𝐄𝐍 𝐊𝐄 𝐋𝐋𝐃𝐄➿",
    "{target} 𝐂𝐇𝐀𝐊𝐊𝐃➿",
    "{target} 𝐑𝐀𝐍𝐃𝐈➿",
    "{target} 𝐁𝐇𝐎𝐒𝐀𝐃𝐈𝐖𝐀𝐋𝐀➿",
    "{target} 𝐌𝐀𝐃𝐀𝐑𝐂𝐇𝐎𝐃➿",
    "{target} 𝐂𝐇𝐔𝐓𝐈𝐘𝐀➿",
    "{target} 𝐆𝐀𝐍𝐃𝐔➿",
    "{target} 𝐋𝐀𝐔𝐃𝐄➿",
    "{target} 𝐓𝐑𝐘𝐘 𝐌𝐀𝐀 𝐊𝐈 𝐂𝐇𝐔𝐓➿",
    "{target} 𝐓𝐑𝐘 𝐌𝐀 𝐊𝐀 𝐁𝐇𝐎𝐒𝐃𝐀➿",
    "{target} 𝐖𝐇𝐎𝐑𝐄➿",
    "{target} 𝐓𝐑𝐘𝐘 𝐌𝐀𝐀 𝐊𝐈 𝐊𝐀𝐋𝐈 𝐂𝐇𝐔𝐓➿",
]

RR_MESSAGES =  ["Chup rndyk kone mein baith 😂😂😂",
"Teri Maa Ke भोसड़े में Theater Kholke सैयारा चाला दुंगी 🔈🔈🔥🔥🔥🔥😂😂😂🔈🔈🔈",
"_✍🏻 𝐘ᴇ 𝐃ᴇᴋʜ ˢᶜʳⁱᵖᵗ ˡⁱᵏʰ ʳᵃʰⁱ ʰᵘ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐁ʜᴏsᴅᴇ 𝐌ᴇɪɴ 😂😂😂",
"Sᴜᴀʀ Tᴇʀɪ Mᴀᴀ Kɪ Cʜᴜᴛ 😌😌💤💤",
"𝐓ᴜ 𝐈ᴅ𝐑 𝐂ᴏᴍᴇʙᴀᴄ𝐊 𝐃ᴇᴛ𝐀 𝐑ᴇ𝐇 𝐆ʏ𝐀 𝐔ᴅʜ𝐑 ᶜʰᵉᵉʳʸ 𝐓ᴇʀ𝐈 𝐌ᴀ𝐀 𝐂ʜᴏᴅ 𝐊ᴇ 𝐆ʏɪ 🩷🩶🩵",
"Choding ho rhi hai teri maa ki 😬👨🏻‍💻🔥",
"Teri Maa Ki Chut Mein Loda Dalugi Beta 🥵💯",
"🧐 Teri maa ka bh🤪sda dikh rha hai 😎",
"😉🔥 Cya 😉🔥 re 😉 🔥 sapri 😉🔥 try 😉🔥 maa 😉🔥 tujh 😉🔥 nehlati 😉🔥 ny 😉🔥 ey 😉🔥 Cya 😉🔥",
"Oye Madarchod Uth 😤😡🥵 Teri Maa Ka Choding Tem 😈👻🦶🏻",
"Teri Maa Ko Football ⚽ bnake uske 𝗕𝗛😈𝗦𝗗𝗘 pe laat 🦶🏻 marungi 🤩🔥",
"इस मंगलवार को ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴄʜᴜᴛ ᴋᴀ ʙʜᴀɴᴅᴀʀᴀ ʜᴏɢᴀ 😈😘👌🏻",
"TᗴᖇI ᗰᗩᗩ Kᗩ ᗷOOᖇ ᗷᗴTᗩ 🤣🤮🔥😏🔥😂💞🌧️",
"𝙈𝘼𝘼 𝙆𝙀 𝙇𝙊𝘿𝙀 🤮",
"𝗣ᴇʜʟ𝗘 𝗧ᴇʀ𝗜 𝗕ᴇʜᴇ𝗡 𝗖ʜᴏᴅᴜɢɪ 𝗙ɪ𝗥 𝗧ᴇʀ𝗜 𝗠ᴀ𝗔 😆😂😆🔥🤢😂🤍😤",
"ƇӇƲƤ ƬЄƦƖ Mƛƛ Ƙƛ ƁӇƠƧƊƛ ♻️",
"𝘚𝘱𝘢𝘮𝘮𝘦𝘳 𝘣𝘢𝘯𝘦𝘨𝘢 𝘳𝘢𝘯𝘥𝘪𝘬𝘦 🤢🔥",
"𝐀ᴊ𝐀 𝐌ᴄ 𝐁ᴀɴᴀ𝐔 𝐓ᴜᴊʜ𝐄 𝐒ᴘᴀᴍᴍᴇ𝐑 👻💥🤍😹👑",
"𝘣𝘰𝘭 #𝘊𝘩𝘦𝘦𝘳𝘺 𝘉𝘢𝘢𝘱 👑",
"😍 Teri 😡 Randi 🤪 Maa 😤 Ko 😎 Pel 😭 Dungi 😍",
"Idhar Aa Beta 🤪💔 Teri Maa Chodu 😂😘",
"Oye bihari kaam pe ja 🔥⛏️🔥⛏️⛏️🔥⛏️💞💞🔥💞⛏️🔥💞⛏️⛏️",
"Teri Maa Chodne K liye Pura Gc Khada Hai 🥴😁🩷💯",
"Teri Maa Bio Mein #Proudrandi 💔🥀 likhti hai 🤩🔥🩷",
"Rndyk lund se utr 😩👏🏻",
"Arey Yarr Apni Maa Matt Nangi Kar 😩🔥💞😩⛏️🔥🥀🤩💞😩🔥😩🩷💞",
"Tu hasta reh gya yaaro mein 😁💯💔 Teri maa chudgyi baazaro mein 😂🌹",
"Teri Maa Chudwa denge re 🪖🔥⛏️🥴🤪💔🩷💯😁😩💞",
"🩷 Gud ❤️ nyt 🧡 rndyk 💛 kal 🩵 Aaungi 💙 Teri 🖤 Maa 🩶 Chodne 🤍",
"🥶 Are 😱 Mc 😩 Ye 🤔 Kaise 🤪 Kiya 😏 Teri 😎 Maa 😬 Randi 🙄 Hai 🤮 100% 😂",
"🩷🩵🤍🩶🖤❤️💚 Ye sare dill teri maa k naam beta 😂😜🔥",
"Hat peche hat tera baap aya 😂😂🥴😹🤲🏻💪🏻",
"Leave le rndyk psnd nai aya tu meko 🤢👎🏻",
"Teri maa chodu 💯 if yes then reply to my message 💀💀💀💪🏻🔥💯👆🏻💔😂😂💔💔💔",
"#𝘊𝘩𝘦𝘦𝘳𝘺 𝘉𝘢𝘢𝘱 𝐊ᴏ 𝐃ʙᴀ ɴʜɪ 𝐏ᴀʀᴇ ᴄʏᴀ?? 🥶🥱😂",
"😹 Tᴇʀɪ 🤪 Rᴀɴᴅɪ 😫 Mᴀᴀ 🤗 Kᴇ 🤢 Bᴜʀ 🤣 Pᴇ 😤 Lᴀᴀᴛ 🙄 Mᴀʀ 😆 Kᴇ 😍 Tᴇʀɪ 😍 Bᴇʜᴇɴ 😈 Cʜᴏᴅ 😅 Dᴜɢɪ 🤩",
"Gᴀʀᴇᴇʙ Ghar Ke Ladke Baap Log Ke Gc Mein Kya Krr Rha 🤢👞",
"🔮 𝐘ᴇ 𝐃ᴇᴋʜ 𝐉ᴀᴅᴜ 𝐒ᴇ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐂ʜᴏᴅ 𝐃ɪyᴀ 😂🪄😂🪄", "Teri Maa Ko बाहुबली style mein chodungi🥶💔🤪😹", "Tumhare Pitashree Cheery 💯🔥🗿🌙"]





POOKIE_NC_MESSAGES = [
    "{target} >  LᴜɴɴCʜᴜssᴇʀ Bɪᴛᴄʜs  ⸻➤(🎀)'",
    "{target} > WᴏʀsHɪᴘ Us AɴD Sᴀʏ ᴏᴏ LᴏRᴅ Gɪᴠᴇ Mᴇ SᴏᴍE CʜᴜDᴀɪ ⸻➤(🎀)'",
    "{target} > Sᴀʏ FᴜᴄK Mᴇʜʜ ⸻➤(🎀)'",
    "{target} > TᴍᴋᴄKɪᴅᴅᴏ ⸻➤(🎀)'",
    "{target} > TʙᴋC ⸻➤(🎀)'",
    "{target} > GʜɪNᴏɴɪ RɴᴅY Kᴇ Bᴄᴄʜᴇ ⸻➤(🎀)'",
    "{target} > HɪᴢRᴜBᴏɪ ⸻➤(🎀)'",
    "{target} > TʀʏᴍAᴋɪ Pᴜssʏ P sᴛᴏNᴇ PᴇʟᴛɪNɢ Kʀᴜ? ⸻➤(🎀)'",
    "{target} > Lᴜɴ Kʜᴀ PᴏᴋEᴍᴏN ⸻➤(🎀)'",
    "{target} > TʀʏMᴀᴀ ᴄʜᴜD CʜᴜD Kᴇ sɪᴄK Hɢʏɪ ⸻➤(🎀)'",
    "{target} > Sᴘᴇᴄs PʜN ᴋE TᴍᴋC ᴘ AᴀJᴊ RᴇʜPᴀᴛ LᴀɴɢEɴɢᴇ ⸻➤(🎀)'",
    "{target} > TᴇRɪ MᴀA Kᴏ ᴘʜUɴsɪ PʜᴏD BᴀBᴀ Kᴇ PᴀsS ᴄʜᴏRᴅ Nɪ ᴘᴀDᴇɢɪ ⸻➤(🎀)'",
    "{target} > CʜᴜᴅEɢɪ Tʀʏᴍᴀ ⸻➤(🎀)'",
    "{target} > HɪᴊAʙ MᴄʜᴜDʟᴇ ⸻➤(🎀)'",
    "{target} > Sᴀʏ Cʜᴇᴇʀʏ DᴀᴅDʏ ⸻➤(🎀)'",
    "{target} > GᴀɴD Mʀᴡᴀ Bsᴅᴋ ⸻➤(🎀)'",
    "{target} > TʀɪMᴀ CʜᴜDᴋᴅ ⸻➤(🎀)'",
]

FLOWER_NC_MESSAGES = [
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફἳ9પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🏵️પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🌸પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ💐પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🌷પ₊‿˵ ˚₊⊕¥",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🪳પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ₊˚ ˵‿₊ફ💮પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🌼પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🌻પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🌹પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🪷પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🌺પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🍀પ₊‿˵ ˚₊⊕¥ ",
    "{target} Cʜᴇᴇʀʏ ᴋᴀ Lᴜɴᴅ ᴄʜᴜᴍ Dᴜɴɪʏᴀ ɢʜᴜᴍ˚ ˵‿₊ફ🌿પ₊‿˵ ˚₊⊕¥ ",
]

NC_BOLT_MESSAGES = [
    "👣 {target} 👣",
    " 🦠 {target} 🦠",
    "🦋 {target} 🦋",
    "🔁 {target} 🔁",
    "😈 {target} 😈",
    "🤮 {target} 🤮",
    "🕸️ {target} 🕸️",
    "💋 {target} 💋",
]

UNAUTHORIZED_MESSAGE = "-# 𝙍𝙣𝙙𝙮𝙨𝙤𝙣 𝙂𝙚𝙩 𝙎𝙪𝙙𝙤 𝙁𝙞𝙧𝙨𝙩 𝙏𝙝𝙚𝙣 𝙘𝙤𝙢𝙚 𝙬𝙞𝙩𝙝 𝙮𝙤𝙪𝙧 𝙢𝙤𝙢 𝙖𝙣𝙙 𝙝𝙖𝙣𝙙 𝙮𝙤𝙪𝙧 𝙢𝙤𝙢 𝙩𝙤 𝙢𝙚 💘 "

NAME_CHANGE_MESSAGES = [
    "{target} 𝐂ʜᴜᴘ 𝐌ᴀᴅᴀʀᴄʜᴏᴅ ━━━》━━━》━━》━━━━━━》━━━━》━━━━━ 😹🔥😹🔥😹",
    "{target} 𝐂ʜᴜᴘ 𝐌ᴀᴅᴀʀᴄʜᴏᴅ ━━━》━━━》━━》━━━━━━》━━━━》━━━━━ 🪐🩷🪐🩷🪐",
    "{target} 𝐂ʜᴜᴘ 𝐌ᴀᴅᴀʀᴄʜᴏᴅ ━━━》━━━》━━》━━━━━━》━━━━》━━━━━ 🧚🏻💃🏻🧚🏻💃🏻",
    "{target} 𝐂ʜᴜᴘ 𝐌ᴀᴅᴀʀᴄʜᴏᴅ ━━━》━━━》━━》━━━━━━》━━━━》━━━━━ 🧃🍭🧃🍭",
    "{target} 𝐂ʜᴜᴘ 𝐌ᴀᴅᴀʀᴄʜᴏᴅ ━━━》━━━》━━》━━━━━━》━━━━》━━━━━ ☁️❤️☁️❤️",
    "{target} 𝐂ʜᴜᴘ 𝐌ᴀᴅᴀʀᴄʜᴏᴅ ━━━》━━━》━━》━━━━━━》━━━━》━━━━━ 🕸️🖤🕸️🖤🕸️",
    "{target} 𝐂ʜᴜᴘ 𝐌ᴀᴅᴀʀᴄʜᴏᴅ ━━━》━━━》━━》━━━━━━》━━━━》━━━━━ 👅🫦👅🫦",
]

REPLY_MESSAGES = [
    "{target} 𝘍𝘈𝘜𝘑𝘐 𝘊𝘜𝘛𝘛𝘐𝘕𝘎 𝘞𝘈𝘓𝘌 𝘏𝘐𝘑𝘋𝘌 𝘗𝘌𝘏𝘓𝘌 𝘑𝘈𝘒𝘌 𝘈𝘗𝘕𝘐 𝘔𝘈𝘒𝘌 𝘑𝘏𝘈𝘛 𝘒𝘌 𝘉𝘈𝘈𝘓𝘖𝘕 𝘒𝘖 𝘞𝘖𝘓𝘍 𝘊𝘜𝘛 𝘒𝘙𝘞𝘈 😁🤟🏻💥❤️",
    "{target} 𝘉𝘢𝘤𝘩𝘒𝘦 𝘙𝘦𝘩𝘯𝘢 𝘉𝘦𝘵𝘢 𝘞𝘳𝘯𝘢 𝘈𝘣𝘥𝘶𝘭 𝘴𝘢𝘮𝘢𝘥 𝘒𝘐 𝘔𝘜𝘜𝘏 𝘗 𝘊𝘏𝘖𝘖𝘛 𝘙𝘈𝘎𝘈𝘋 𝘋𝘌𝘛𝘐 𝘏 🌈🤢🤮🫰🏻",
    "{target} 𝘊𝘏𝘜𝘋𝘈𝘐 𝘒𝘏𝘈𝘈 𝘔𝘋𝘊 𝘉𝘚𝘚 𝘛𝘜 🍭🍭🍭🍭",
    "{target} 𝘈𝘑𝘈 𝘛𝘙𝘠 𝘔𝘈𝘒𝘈 𝘉𝘏𝘖𝘚𝘋𝘈 𝘔𝘌𝘈𝘚𝘜𝘙𝘌 𝘒𝘙𝘜𝘕𝘎𝘐😁🖖🏻📐📐",
    "{target} 𝘙𝘕𝘋𝘠𝘒𝘌 𝘊𝘈𝘓𝘓 𝘍𝘠𝘛𝘌𝘙 𝘉𝘈𝘕𝘌𝘎𝘈 𝘌𝘒 𝘙𝘌𝘏𝘗𝘈𝘛 𝘔 𝘙𝘈𝘗𝘌 𝘒𝘙𝘋𝘌𝘕𝘎𝘌 𝘛𝘌𝘙𝘈 ❄️🫰🏻🚓🚨💘😅",
    "{target} تیری مکی چوت ایم عبدل بلیگرام😁👁️👄👁️🫄🏻🍁🪻",
    "{target} 𝘠𝘰 𝘞𝘢𝘯𝘯𝘢 𝘉𝘦 𝘌𝘯𝘨𝘭𝘪𝘴𝘩 𝘚𝘱𝘦𝘢𝘬𝘦𝘳 🔇 𝘵𝘮𝘬𝘤 𝘮 𝘴𝘪𝘳𝘦𝘯 𝘨𝘩𝘶𝘴𝘢 𝘥𝘶𝘯𝘨𝘪 𝘧𝘩𝘪𝘳 𝘫𝘢𝘣 𝘷 𝘵𝘶 𝘦𝘯𝘨𝘭𝘪𝘴𝘩 𝘣𝘰𝘭𝘦𝘨𝘢 𝘵𝘦𝘳𝘪 𝘮𝘢𝘢 𝘳𝘰 𝘥𝘦𝘨𝘪",
    "{target} 𝘚𝘗𝘈𝘔𝘔𝘌𝘙 𝘈𝘎𝘈𝘠𝘈 𝘉𝘊 𝘈𝘉 𝘠𝘌𝘏 𝘊𝘏𝘜𝘋𝘌𝘎𝘈 𝘉𝘏𝘌𝘕𝘊𝘏𝘖𝘋 𝘊𝘏𝘜𝘋𝘕𝘌 𝘞𝘈𝘓𝘈 𝘚𝘗𝘈𝘔𝘔𝘌𝘙 𝘈𝘈𝘎𝘠𝘈 😭😭😭😂😂💔🧑🏻‍🩰🧑🏻‍🏫🧑🏻‍🎨",
    "{target} 𝘒𝘈𝘓𝘐 𝘙𝘕𝘋𝘠𝘒𝘌 𝘉𝘈𝘊𝘊𝘏𝘌 𝘊𝘏𝘌𝘌𝘙𝘠 𝘒𝘌 𝘚𝘈𝘔𝘕𝘌 𝘈𝘞𝘈𝘑 𝘜𝘛𝘏𝘈𝘠𝘌𝘎𝘈 𝘓𝘌 𝘊𝘏𝘜𝘋 🫯💘🩸💋👣",
    "{target} 𝙏𝙍𝙔 𝙈𝘼 𝙅𝙤𝙙𝙝 𝙈 𝙋𝙖𝙙𝙞 𝙝𝙪𝙞 𝙍𝙖𝙣𝙙𝙞 𝙝 🥺♿🌙🫪 ",
    "{target} 𝘛𝘳𝘺 𝘮𝘢 𝘬𝘰 𝘛𝘢𝘯𝘵𝘳𝘪𝘬 𝘊𝘩𝘰𝘥𝘬𝘦 𝘉𝘩𝘢𝘴𝘢𝘮 کرگیا 😷😂💔✨",
    "{target} 🧑🏻‍🎤💃🏻🌹🌷𝘭𝘶𝘯𝘥 𝘤𝘩𝘶𝘴𝘴𝘦𝘳 𝘮𝘤",
    "{target} 🎯 𝘏𝘐𝘑𝘙𝘌 𝘛𝘌𝘙𝘐 𝘔𝘈𝘒𝘖 𝘊𝘏𝘖𝘋𝘕𝘌 𝘈𝘈𝘛𝘐 𝘏𝘌 𝘊𝘏𝘌𝘌𝘙𝘠 𝘙𝘖𝘡 💋🩸💘",
    "{target} 𝐂ʜᴇᴇʀʏ 𝘉𝘢𝘨𝘩𝘸𝘢𝘯 𝘚𝘦 𝘭𝘢𝘥𝘯𝘦 𝘬𝘪 𝘩𝘪𝘮𝘮𝘢𝘵 𝘬𝘦𝘴𝘦 𝘢𝘢𝘺𝘪 𝘵𝘦𝘳𝘦𝘮𝘦 𝘳𝘯𝘥𝘢𝘪𝘭 🚵🏻🚵🏻🤺🧚🏻🥷🏻",
    "{target} 𝘛𝘦𝘳𝘪 𝘔𝘢𝘬𝘢 𝘏𝘰𝘳𝘴𝘦𝘗𝘰𝘸𝘦𝘳 𝘒𝘩𝘢𝘬𝘦 𝘤𝘩𝘰𝘥𝘶𝘯𝘨𝘪🩺🥼🧑🏻‍⚕️😷💉💉💊",
    "{target} 𝘛𝘶 𝘒𝘩𝘢𝘺𝘦𝘨𝘢 𝘗𝘪𝘻𝘻𝘢 𝘛𝘳𝘺𝘮𝘢𝘊?? 𝘊𝘩𝘰𝘥??𝘨𝘪 𝘊𝘩𝘦𝘦𝘳𝘺 𝘡𝘪𝘻𝘢🪼🐳🦋🫐🍕😁",
    "{target} Ab 𝘔𝘦𝘳𝘢 𝘏𝘌𝘈𝘙𝘛 𝘉𝘙𝘌𝘈𝘒 𝘏𝘎𝘠𝘈 𝘛𝘙𝘠 𝘔𝘈 𝘉𝘏𝘌𝘕 𝘒𝘖 𝘚𝘈𝘋 𝘚𝘖𝘕𝘎 𝘒𝘐 𝘗𝘓𝘈𝘠𝘓𝘐𝘚𝘛 𝘓𝘈𝘎𝘈 𝘒𝘌 𝘊𝘖𝘋𝘜𝘕𝘎𝘐 😫😵😵‍💫🫨🥴🥵🥶👿🤡💩",
    "{target}✓𝘞𝘩𝘢𝘵 𝘪𝘴 8 ➗ 2 2 2 )=𝘛𝘦𝘳𝘪 𝘔𝘢𝘬𝘪 𝘤𝘩𝘶𝘵 😂😁🍕🌷?",
    "{target} 𝘛𝘶𝘫𝘩𝘦𝘺 𝘗𝘢𝘵𝘢 𝘏𝘢𝘺 𝘛𝘶 𝘬𝘦𝘴𝘦 𝘢𝘢𝘺𝘢 𝘵𝘩𝘢 𝘪𝘴𝘴 𝘥𝘩𝘢𝘳𝘵𝘪 𝘱? 😁⚡ 𝘔 𝘋𝘩𝘶𝘳𝘢𝘯𝘥𝘢𝘳 2 𝘥𝘦𝘩𝘬 𝘳𝘩𝘢 𝘵𝘩𝘢 𝘢𝘶𝘳 𝘵𝘦𝘳𝘪 𝘮𝘢𝘯𝘦 𝘮𝘦𝘳𝘢 𝘭𝘶𝘯 𝘢𝘱𝘯𝘪 𝘤𝘩𝘶𝘵 𝘮 𝘥𝘢𝘭 𝘭𝘪𝘺𝘢",
    "{target} 𝘛𝘦𝘳𝘪 𝘔𝘢 𝘬𝘰 𝘜𝘯𝘥𝘦𝘳𝘙𝘰𝘰𝘵 2 𝘭𝘦𝘬𝘦 3𝘹𝘺-2 𝘴𝘰𝘭𝘷𝘦 𝘬𝘳𝘬𝘦 𝘭𝘶𝘯𝘥𝘱 𝘣𝘦𝘵𝘩𝘢 𝘥𝘶𝘯𝘨𝘪 ⚡😾💨",
]

MULTIGC_NC_MESSAGES = [
    " {target} ʟᴜꪀᴅᥴʜꫝᴛᴜ -(💭)-",
    "{target} Cʜɪꪀꫝʟ -(🥏)-",
    "{target} ᴄʜꪊᴅ -(🌀)-",
    "{target} ꪑꫝᴅꫝʀCʜꪮᴅ -(☢)-",
    "{target} ᴋꫝꪑᴊꪮʀ -(🌊)-",
    "{target} ʟꪊꪀᴅ ᥴʜᴜડ -(🧞‍♂️)-",
    "{target} ᴄʜꪊᴛꫝᴅ -(🏵️)-",
]

MULTIGC_SPAM_MESSAGES = [
    "{target} ᴋꫝꪑᴊꪮʀ ﴾🌙﴿ \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n {target} ᴋꫝꪑᴊꪮʀ ﴾🌙﴿ ",
    "{target} Cʜɪꪀꫝʟ ﴾🐕﴿ \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n {target} Cʜɪꪀꫝʟ ﴾🐕﴿",
    "{target} ʟᴜꪀᴅᥴʜꫝᴛᴜ ﴾❄️﴿ \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n {target} ʟᴜꪀᴅᥴʜꫝᴛᴜ ﴾❄️﴿",
    "{target} ʟꪊꪀᴅ ᥴʜᴜડ ﴾🌊﴿ \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n {target} ʟꪊꪀᴅ ᥴʜᴜડ ﴾🌊﴿",
    "{target} ᴄʜꪊᴅ ﴾🫧﴿ \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n {target} ᴄʜꪊᴅ ﴾🫧﴿",
    "{target} ꪑꫝᴅꫝʀCʜꪮᴅ ﴾🌀﴿ \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n. {target} ꪑꫝᴅꫝʀCʜꪮᴅ ﴾🌀﴿",
    "{target} ᴄʜꪊᴛꫝᴅ ﴾🦠﴿ \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n {target} ᴄʜꪊᴛꫝᴅ ﴾🦠﴿",
]

SPAM_MESSAGE_TEMPLATE = """{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀{target} Tᴇʀɪ Mᴀᴀ Cʜᴏᴅ Dᴀʟᴇɴɢᴇ ʀᴇ ─•────➤ ┆ ⤿🌀"""

SPAM_MESSAGE_2 = """ < {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ➤──────────Yᴀ - Hᴀʀᴅ Sᴘᴀᴍ Sᴇ ?¿!___------_-_-< {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ➤──────────Yᴀ - Hᴀʀᴅ Sᴘᴀᴍ Sᴇ ?¿!___------_-_-< {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ➤──────────Yᴀ - Hᴀʀᴅ Sᴘᴀᴍ Sᴇ ?¿!___------_-_-< {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ➤──────────Yᴀ - Hᴀʀᴅ Sᴘᴀᴍ Sᴇ ?¿!___------_-_-< {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ➤──────────Yᴀ - Hᴀʀᴅ Sᴘᴀᴍ Sᴇ ?¿!___------_-_-< {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ➤──────────Yᴀ - Hᴀʀᴅ Sᴘᴀᴍ Sᴇ ?¿!___------_-_-< {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ➤──────────Yᴀ - Hᴀʀᴅ Sᴘᴀᴍ Sᴇ ?¿!___------_-_-< {target} > ●───────────────────₎Sᴏғᴛ Sᴘᴀᴍ sᴇ Tᴇʀɪ ᴍᴀ ᴄᴏᴅᴜ ?¿?_-_-_-_----__-----__⚡ ࣪»"""

SETDESC_MESSAGES = [
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ ❄️ ",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 🫧",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 🦈",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 🌊",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 🌙",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 🔥",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 🔆",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 👑",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 🪷",
    "< {target} > ᥴʜꪊᴅꫝɪ ᛕꫀ 𝑩ꫝᴋʀᴇ 👾",
]

BIGNC_MESSAGES = [
    "〔 {target} 〕𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️𒐫𒐫𒐫☢️",
    "〔 {target} 〕𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷𒐫𒐫𒐫🩷",
    "〔 {target} 〕𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥𒐫𒐫𒐫🔥",
    "〔 {target} 〕𒐫𒐫𒐫🦈𒐫𒐫𒐫🦈𒐫𒐫𒐫🦈??𒐫𒐫🦈𒐫𒐫𒐫🦈𒐫𒐫𒐫🦈𒐫𒐫𒐫🦈𒐫𒐫𒐫🦈𒐫𒐫𒐫🦈",
    "〔 {target} 〕𒐫𒐫𒐫👾𒐫𒐫𒐫👾𒐫𒐫𒐫👾𒐫𒐫𒐫👾𒐫𒐫𒐫👾𒐫𒐫𒐫👾𒐫𒐫𒐫👾𒐫𒐫𒐫👾𒐫𒐫𒐫👾",
    "〔 {target} 〕𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️𒐫𒐫𒐫❄️",
    "〔 {target} 〕𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁𒐫𒐫𒐫🥁",
    "〔 {target} 〕𒐫𒐫𒐫💠𒐫𒐫𒐫💠𒐫𒐫𒐫💠𒐫𒐫𒐫💠𒐫𒐫𒐫💠𒐫𒐫𒐫💠𒐫𒐫𒐫💠𒐫𒐫𒐫💠𒐫𒐫𒐫💠",
    "〔 {target} 〕𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄𒐫𒐫𒐫🀄",
    "〔 {target} 〕𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃",
    "〔 {target} 〕𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️𒐫𒐫𒐫☀️",
    "〔 {target} 〕𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧𒐫𒐫𒐫🫧",
]

SPAM_MESSAGE_3 = """
〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』


〘{target}〙ᴛᴇʀɪ ᴍᴀᴀ ᴍᴀᴀ ᴋᴀ ßʜᴏsᴅᴀ ғᴀᴛ ɢᴀʏᴀ 𖨩⁣    『💙』."""


def extract_retry_after(error_str):
    match = re.search(r'retry after (\d+)', error_str.lower())
    if match:
        return int(match.group(1))
    return None


class BotInstance:
    def __init__(self, bot_number, owner_id):
        self.bot_number = bot_number
        self.owner_id = owner_id
        self.sudo_users = set(SUDO_IDS)
        self.active_spam_tasks = {}
        self.active_name_change_tasks = {}
        self.active_ncmoon_tasks = {}
        self.active_ncflag_tasks = {}
        self.active_ncbolt_tasks = {}
        self.active_cheerync_tasks = {}
        self.active_curly_tasks = {}
        self.active_timenc_tasks = {}
        self.active_multigc_tasks = {}
        self.active_reply_tasks = {}
        self.active_reply_targets = {}
        self.active_react_chats = {}
        self.pending_replies = {}
        self.active_rr_tasks = {}
        self.active_rr_targets = {}  # chat_id -> user_id
        self.pending_rr_replies = {}  # chat_id -> [msg_ids]
        self.active_rrspam_tasks = {}
        self.active_rrspam_targets = {}  # chat_id -> (target_user_id, message_id)
        self.active_imagespam_tasks = {}
        self.imagespam_file_ids = {}  # chat_id -> file_id
        self.active_fwdspam_tasks = {}
        self.fwdspam_sources = {}  # chat_id -> (from_chat_id, message_id)
        self.active_emojirain_tasks = {}
        self.active_setdesc_tasks = {}
        self.active_bignc_tasks = {}
        self.active_fastnc_tasks = {}

        self.chat_delays = {}
        self.chat_threads = {}
        self.locks = {}
        self.proxy = None
        self.proxies_list = []
        self._load_proxies()

    def _load_proxies(self):
        if os.path.exists("proxies.txt"):
            with open("proxies.txt", "r") as f:
                self.proxies_list = [line.strip() for line in f if line.strip()]
            if self.proxies_list:
                self.proxy = random.choice(self.proxies_list)

    async def join_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        if not context.args:
            await update.message.reply_text("Usage: .join <invite_link_or_username>")
            return
            
        link = context.args[0]
        # Clean the link if it's a full URL
        if "t.me/" in link:
            link = link.split("t.me/")[-1]
        if link.startswith("+"):
            link = link[1:]
        if link.startswith("@"):
            link = link[1:]
            
        print(f"[Bot {self.bot_number}] Attempting to join: {link}")
        try:
            await context.bot.do_api_request("joinChat", {"chat_id": link})
            await update.message.reply_text(f"Bot {self.bot_number} joined! ✅")
        except Exception as e:
            print(f"[Bot {self.bot_number}] Join error: {e}")
            await update.message.reply_text(f"Bot {self.bot_number} failed: {e}")

    async def joinall_command(self, update, context):
        if not await self.check_owner(update):
            return

        if not context.args:
            await update.message.reply_text("Usage: .joinall <invite_link_or_username>")
            return

        raw = context.args[0]

        if not ALL_BOTS:
            await update.message.reply_text("No bots registered yet!")
            return

        await update.message.reply_text(f"⚡ All bots joining...")

        joined = 0
        failed = 0
        for bot_id, bot_obj in list(ALL_BOTS.items()):
            try:
                await bot_obj.do_api_request("joinChat", {"chat_id": raw})
                joined += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                failed += 1
                print(f"[joinall] Bot {bot_id} failed: {e}")

        await update.message.reply_text(f"✅ {joined} bot(s) joined! ❌ {failed} failed.")

    async def fjoin_command(self, update, context):
        if not await self.check_owner(update):
            return

        global USERBOT

        if not context.args:
            await update.message.reply_text(
                "Usage: .fjoin <folder_link>\n"
                "Example: .fjoin https://t.me/addlist/XXXXXXXX\n\n"
                "Requires API_ID, API_HASH, and SESSION_STRING set in op.py."
            )
            return

        if not PYROGRAM_AVAILABLE:
            await update.message.reply_text("❌ Pyrogram not installed. Run: pip install pyrogram tgcrypto")
            return

        if not API_ID or not API_HASH:
            await update.message.reply_text("❌ API_ID / API_HASH not set in op.py.")
            return

        if not SESSION_STRING:
            await update.message.reply_text(
                "❌ SESSION_STRING is empty.\n\n"
                "Generate it once:\n"
                "  from pyrogram import Client\n"
                "  async with Client('x', API_ID, API_HASH) as c:\n"
                "      print(await c.export_session_string())\n\n"
                "Then paste the string into SESSION_STRING in op.py."
            )
            return

        folder_link = context.args[0].strip()
        if "t.me/addlist/" not in folder_link:
            await update.message.reply_text(
                "❌ Invalid link. Provide a Telegram folder link:\n"
                "https://t.me/addlist/XXXXXXXX"
            )
            return

        folder_slug = folder_link.split("t.me/addlist/")[-1].strip("/").split("?")[0]
        if not folder_slug:
            await update.message.reply_text("❌ Could not extract folder slug from the link.")
            return

        status_msg = await update.message.reply_text("🔌 Connecting via MTProto…")

        # Start / reuse userbot
        if USERBOT is None:
            try:
                USERBOT = PyroClient(
                    name="userbot_session",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    session_string=SESSION_STRING,
                    no_updates=True,
                )
                await USERBOT.start()
                me = await USERBOT.get_me()
                print(f"[Userbot] Connected as @{me.username} ({me.id})")
            except Exception as e:
                USERBOT = None
                await status_msg.edit_text(f"❌ Userbot connect failed: {e}")
                return

        await status_msg.edit_text("🔍 Fetching folder via MTProto…")

        # Resolve folder chats via raw MTProto
        try:
            folder_info = await USERBOT.invoke(
                pyro_functions.chatlists.CheckChatlistInvite(slug=folder_slug)
            )
            already_peers = list(getattr(folder_info, "already_peers", []))
            new_peers     = list(getattr(folder_info, "peers", []))
        except Exception as e:
            await status_msg.edit_text(f"❌ Failed to fetch folder: {e}\nLink may be expired or invalid.")
            return

        to_join = new_peers
        total   = len(already_peers) + len(to_join)

        if not to_join:
            await status_msg.edit_text(
                f"📂 Folder has {total} chat(s) — already a member of all of them."
            )
            return

        await status_msg.edit_text(
            f"📂 𝙁𝙤𝙡𝙙𝙚𝙧 𝘿𝙚𝙩𝙚𝙘𝙩𝙚𝙙\n"
            f"🔢 Total  : {total}\n"
            f"✅ Already: {len(already_peers)}\n"
            f"🎯 To join: {len(to_join)}\n\n"
            f"⏳ Joining…"
        )

        joined  = 0
        failed  = 0
        skipped = 0
        errors  = []

        for idx, peer in enumerate(to_join, 1):
            chat_id = (
                getattr(peer, "channel_id", None)
                or getattr(peer, "chat_id", None)
                or getattr(peer, "user_id", None)
            )
            label = str(chat_id) if chat_id else f"peer#{idx}"
            try:
                await USERBOT.invoke(
                    pyro_functions.channels.JoinChannel(
                        channel=await USERBOT.resolve_peer(peer)
                    )
                )
                joined += 1
            except PyroFloodWait as e:
                wait = e.value + 3
                await status_msg.edit_text(
                    f"⏳ FloodWait {e.value}s — cooling down…\n"
                    f"Progress: {joined} joined / {failed} failed"
                )
                await asyncio.sleep(wait)
                try:
                    await USERBOT.invoke(
                        pyro_functions.channels.JoinChannel(
                            channel=await USERBOT.resolve_peer(peer)
                        )
                    )
                    joined += 1
                except Exception as e2:
                    failed += 1
                    if len(errors) < 5:
                        errors.append(f"{label}: {str(e2)[:60]}")
            except Exception as e:
                err = str(e).lower()
                if "already" in err or "member" in err:
                    skipped += 1
                else:
                    failed += 1
                    if len(errors) < 5:
                        errors.append(f"{label}: {str(e)[:60]}")

            await asyncio.sleep(1)

        lines = [
            "✅ 𝙁𝙅𝙊𝙄𝙉 𝘾𝙤𝙢𝙥𝙡𝙚𝙩𝙚!",
            f"📂 Folder : t.me/addlist/{folder_slug}",
            f"🔢 Total  : {total}",
            f"✅ Joined : {joined}",
            f"⏭ Skipped: {skipped + len(already_peers)}",
            f"❌ Failed : {failed}",
        ]
        if errors:
            lines.append("\n⚠️ Sample errors:")
            for err in errors:
                lines.append(f"  • {err}")
        await status_msg.edit_text("\n".join(lines))

    async def proxy_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        if not context.args:
            status = f"Current Proxy: {self.proxy}" if self.proxy else "No proxy configured."
            await update.message.reply_text(f"{status}\nUsage: .proxy add <url> or .proxy reload")
            return

        cmd = context.args[0].lower()
        if cmd == "add" and len(context.args) > 1:
            proxy_url = context.args[1]
            with open("proxies.txt", "a") as f:
                f.write(f"{proxy_url}\n")
            self._load_proxies()
            await update.message.reply_text(f"Proxy added and reloaded! ✅")
        elif cmd == "reload":
            self._load_proxies()
            await update.message.reply_text(f"Proxies reloaded! Total: {len(self.proxies_list)} ✅")

    def get_lock(self, chat_id):
        if chat_id not in self.locks:
            self.locks[chat_id] = asyncio.Lock()
        return self.locks[chat_id]

    def is_owner(self, user_id):
        return user_id == self.owner_id or user_id in self.sudo_users

    async def sudo_command(self, update, context):
        if update.effective_user.id != self.owner_id:
            return

        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text("Usage: .sudo @username or reply to a message with .sudo")
            return

        user_to_sudo = None
        if update.message.reply_to_message:
            user_to_sudo = update.message.reply_to_message.from_user.id
        else:
            # Try to get user from mention or ID
            arg = context.args[0]
            if arg.startswith("@"):
                # Note: CommandHandler doesn't resolve usernames to IDs automatically
                # This usually requires the user to be in the bot's cache
                await update.message.reply_text("Please reply to the user's message with .sudo to grant sudo.")
                return
            else:
                try:
                    user_to_sudo = int(arg)
                except ValueError:
                    await update.message.reply_text("Invalid User ID.")
                    return

        if user_to_sudo:
            self.sudo_users.add(user_to_sudo)
            await update.message.reply_text(f"User {user_to_sudo} 𝙜𝙧𝙖𝙣𝙩𝙚𝙙 𝙎𝙐𝘿𝙊 𝙥𝙤𝙬𝙚𝙧𝙨!  ✅")

    async def refresh_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        await update.message.reply_text(f"Bot {self.bot_number} 𝙞𝙨 𝙖𝙘𝙩𝙞𝙫𝙚 𝙖𝙣𝙙 𝙧𝙚𝙛𝙧𝙚𝙨𝙝𝙚𝙙! ⚡")

    async def check_owner(self, update):
        user_id = update.effective_user.id
        if not self.is_owner(user_id):
            try:
                await update.message.reply_text(UNAUTHORIZED_MESSAGE)
            except Exception:
                pass
            return False
        if update.effective_chat:
            KNOWN_CHATS.add(update.effective_chat.id)
        return True

    async def start(self, update, context):
        if not await self.check_owner(update):
            return

        help_text = f"""

ㅤㅤㅤㅤㅤ
✧══════════════════════✧
      🜃 𝐂ʜᴇᴇʀʏ v²¹ 🜃
✧══════════════════════✧

▣ ──「 Nᴀᴍᴇ Cʜᴀɴɢᴇʀ 」── ▣
.ɴᴄ .ᴛɪᴍᴇɴᴄ .ɴᴄғʟᴀɢ .ɴᴄʙᴏʟᴛ
.ɴᴄᴄᴜʀʟʏ .ᴋᴇɴɢɴᴄ .ғʟᴏᴡᴇʀɴᴄ
.ɴᴄᴇᴍᴏ .ᴀɴɴᴜɴᴄ .ʙɪɢɴᴄ .ᴄʜᴇᴇʀʏɴᴄ .ғᴀsᴛɴᴄ

▣ ──「 Sʟɪᴅᴇ & Sᴘᴀᴍ 」── ▣
.ʀʀ          ⇢ ʀᴇᴘʟʏ ᴛᴏ ᴛᴀʀɢᴇᴛ
.ʀᴇᴘʟʏ      ⇢ < @ᴛᴀʀɢᴇᴛ >
.sᴘᴀᴍ       ⇢ < @ᴛᴀʀɢᴇᴛ >
.ᴍᴜʟᴛɪɢᴄ   ⇢ < @ᴛᴀʀɢᴇᴛ >
.ʀʀsᴘᴀᴍ    ⇢ ʀᴇᴘʟʏ sᴘᴀᴍ
.ғᴡᴅsᴘᴀᴍ   ⇢ ғᴏʀᴡᴀʀᴅ sᴘᴀᴍ

▣ ──「 Pɪxᴇʟ Sᴘᴀᴍ 」── ▣
.sᴇᴛɢᴄ    ⇢ sᴇᴛ ɢᴄ ᴘғᴘ
.ɢᴄ        ⇢ ɢʟᴏʙᴀʟ ᴘʜᴏᴛᴏ ᴄʜᴀɴɢᴇʀ
.ɪᴍᴀɢᴇsᴘᴀᴍ ⇢ ʀᴇᴘʟʏ ᴛᴏ ɪᴍᴀɢᴇ

▣ ──「 Aᴅᴍɪɴ Zᴏɴᴇ 」── ▣
.ᴜᴘᴀᴅᴍɪɴ  ⇢ ғᴜʟʟ ᴘᴇʀᴍs ᴛᴏ ʙᴏᴛ
.ʟᴇᴀᴠᴇᴀʟʟ ⇢ ᴀᴜᴛᴏ ʟᴇᴀᴠᴇ
.ʙʀᴏᴅᴄᴀsᴛ ⇢ ʙʀᴏᴀᴅᴄᴀsᴛ ᴛᴏ ɢᴄs
.ʟᴏᴄᴋ/ᴜɴʟᴏᴄᴋ ⇢ ᴛᴏɢɢʟᴇ ɢᴄ

▣ ──「 Exᴛʀᴀ Sᴜᴅᴏ 」── ▣
.sᴜᴅᴏ    ⇢ ʀᴇᴘʟʏ ᴛᴏ ʜᴏᴍɪᴇ
.ᴘɪɴɢ    ⇢ sᴘᴇᴇᴅ ᴛᴇsᴛ
.ᴅᴇʟᴀʏ   ⇢ sᴇᴛ [0.1 - 100]
.ʀᴇғʀᴇsʜ ⇢ ᴄʟᴇᴀʀ ʟᴀɢ
.sᴛᴀᴛs   ⇢ ᴄᴍᴅ sᴛᴀᴛs
.ʀᴇᴀᴄᴛ   ⇢ ʀᴇᴀᴄᴛ ᴏɴ ᴍsɢ
.sᴇᴛᴅᴇsᴄ ⇢ ᴄʜᴀɴɢᴇ ɢᴄ ᴅᴇsᴄ
.ᴇᴍᴏᴊɪʀᴀɪɴ ⇢ ᴇᴍᴏᴊɪ sᴘᴀᴍ
.ғᴊᴏɪɴ   ⇢ ᴊᴏɪɴ ᴠɪᴀ ᴀᴘɪ

▣ ──「 Sᴛᴏᴘ Cᴍᴅs 」── ▣
.sᴛᴏᴘʀʀ        ⇢ sᴛᴏᴘ ʀᴇᴘʟʏ sʟɪᴅᴇ
.sᴛᴏᴘʀᴇᴘʟʏ    ⇢ sᴛᴏᴘ ʀᴇᴘʟʏ sᴘᴀᴍ
.sᴛᴏᴘsᴘᴀᴍ     ⇢ sᴛᴏᴘ sᴘᴀᴍ
.sᴛᴏᴘᴍᴜʟᴛɪɢᴄ  ⇢ sᴛᴏᴘ ᴍᴜʟᴛɪɢᴄ
.sᴛᴏᴘʀʀsᴘᴀᴍ   ⇢ sᴛᴏᴘ ʀʀ sᴘᴀᴍ
.sᴛᴏᴘғᴡᴅ      ⇢ sᴛᴏᴘ ғᴏʀᴡᴀʀᴅ sᴘᴀᴍ
.sᴛᴏᴘɢᴄ       ⇢ sᴛᴏᴘ ɢᴄ ᴘғᴘ ᴄʜᴀɴɢᴇʀ
.sᴛᴏᴘɪᴍɢ      ⇢ sᴛᴏᴘ ɪᴍᴀɢᴇ sᴘᴀᴍ
.sᴛᴏᴘᴇᴍᴏᴊɪ    ⇢ sᴛᴏᴘ ᴇᴍᴏᴊɪ ʀᴀɪɴ

        ✦ ── "𝐂ʜᴇᴇʀʏ V²¹ " ── ✦
  ══════════════════════════
       🜁 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐂ʜᴇᴇʀʏ 🜁 """
        await update.message.reply_text(help_text)

    async def auto_name_loop(self, context, target_name):
        msg_index = 0
        num_messages = len(NAME_CHANGE_MESSAGES)
        print(f"[Bot {self.bot_number}] AUTO NAME LOOP started for {target_name}")
        try:
            while True:
                try:
                    display_name = target_name
                    await context.bot.set_my_name(name=display_name)
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + 1.0)
                except Exception:
                    await asyncio.sleep(10.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] AUTO NAME LOOP stopped")

    async def auto_name_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        target_name = " ".join(context.args) if context.args else "BOT"
        chat_id = update.effective_chat.id
        
        # Stop existing auto_name tasks for this chat
        if chat_id in self.active_name_change_tasks:
            for task in self.active_name_change_tasks[chat_id]:
                task.cancel()
            del self.active_name_change_tasks[chat_id]

        task = asyncio.create_task(self.auto_name_loop(context, target_name))
        if chat_id not in self.active_name_change_tasks:
            self.active_name_change_tasks[chat_id] = []
        self.active_name_change_tasks[chat_id].append(task)
        await update.message.reply_text(f"Auto 𝙣𝙖𝙢𝙚 𝙘𝙝𝙖𝙣𝙜𝙚 𝙡𝙤𝙤𝙥 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙛𝙤𝙧 {target_name}! 🔄")

    async def stop_auto_name(self, update, context):
        if not await self.check_owner(update):
            return
        
        chat_id = update.effective_chat.id
        if chat_id in self.active_name_change_tasks:
            for task in self.active_name_change_tasks[chat_id]:
                task.cancel()
            del self.active_name_change_tasks[chat_id]
        await update.message.reply_text("Auto name 𝙘𝙝𝙖𝙣𝙜𝙚 𝙨𝙩𝙤𝙥𝙥𝙚𝙙! 🛑")

    async def multispam_command(self, update, context):
        if not await self.check_owner(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: .multispam <target>")
            return
        
        target = " ".join(context.args)
        chat_id = update.effective_chat.id
        await update.message.reply_text(f"🚀 𝘾𝙤𝙤𝙧𝙙𝙞𝙣𝙖𝙩𝙚𝙙 𝙢𝙪𝙡𝙩𝙞-𝙨𝙥𝙖𝙢 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙛𝙤𝙧 {target}!")
        
        # This will be triggered on all bot instances since they share the same command handlers
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_spam_tasks[chat_id] = [asyncio.create_task(self.spam_loop(chat_id, target, context, i)) for i in range(num_threads)]

    async def react_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        chat_id = update.effective_chat.id
        if chat_id in self.active_react_chats:
            del self.active_react_chats[chat_id]
            await update.message.reply_text("𝙍𝙚𝙖𝙘𝙩𝙞𝙤𝙣𝙨 𝙙𝙞𝙨𝙖𝙗𝙡𝙚𝙙! ❌")
        else:
            self.active_react_chats[chat_id] = True
            await update.message.reply_text("𝙍𝙚𝙖𝙘𝙩𝙞𝙤𝙣𝙨 𝙚𝙣𝙖𝙗𝙡𝙙! 💀✅")

    async def time_nc_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        num_messages = len(TIME_NC_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] TIME NC LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = TIME_NC_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except Exception:
                    await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] TIME NC LOOP stopped after {success_count} changes")

    async def time_nc_command(self, update, context):
        if not await self.check_owner(update): return
        if not context.args:
            await update.message.reply_text("Usage: .timenc <target>")
            return
        target = " ".join(context.args)
        chat_id = update.effective_chat.id
        num_threads = self.chat_threads.get(chat_id, 1)
        self.active_timenc_tasks[chat_id] = [asyncio.create_task(self.time_nc_loop(chat_id, target, context, i+1)) for i in range(num_threads)]
        await update.message.reply_text(f"Time NC 𝙇𝙤𝙤𝙥 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙛𝙤𝙧 {target} 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨! ⌚🔥")

    async def stop_time_nc(self, update, context):
        if not await self.check_owner(update): return
        chat_id = update.effective_chat.id
        if chat_id in self.active_timenc_tasks:
            for task in self.active_timenc_tasks[chat_id]: task.cancel()
            del self.active_timenc_tasks[chat_id]
        await update.message.reply_text("𝙏𝙞𝙢𝙚 𝙉𝘾 𝙇𝙤𝙤𝙥 𝙨𝙩𝙤𝙥𝙥𝙚𝙙! 🛑")

    async def ownrp_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        reply_to_message = update.message.reply_to_message
        if not reply_to_message:
            await update.message.reply_text("Please reply to a message with .ownrp to see details.")
            return

        target_user = reply_to_message.from_user
        target_name = target_user.first_name if target_user else "Unknown"
        target_id = target_user.id if target_user else "Unknown"
        target_username = f"@{target_user.username}" if target_user and target_user.username else "None"
        
        owner_info = f"OWNER ID: `{self.owner_id}`"
        target_info = f"TARGET NAME: `{target_name}`\nTARGET ID: `{target_id}`\nTARGET USERNAME: {target_username}"
        
        await update.message.reply_text(
            f"〘 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 〙\n\n"
            f"{owner_info}\n\n"
            f"{target_info}\n\n"
            f"𝘾𝙃𝙀𝙀𝙍𝙔 𝘽𝘼𝘼𝙋 𝙑21",
            parse_mode='Markdown'
        )

    async def rr_command(self, update, context):
        if not await self.check_owner(update):
            return

        reply_to = update.message.reply_to_message
        if not reply_to:
            await update.message.reply_text("Reply to someone's message with .rr to start auto-replying them.")
            return

        chat_id = update.effective_chat.id
        target_user = reply_to.from_user
        if not target_user:
            await update.message.reply_text("Could not identify the target user.")
            return

        target_user_id = target_user.id
        target_name = target_user.first_name or str(target_user_id)

        # Stop existing rr loop for this chat if any
        if chat_id in self.active_rr_tasks:
            old_task = self.active_rr_tasks[chat_id]
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass

        self.active_rr_targets[chat_id] = target_user_id
        self.pending_rr_replies[chat_id] = []
        task = asyncio.create_task(self.rr_loop(chat_id, context))
        self.active_rr_tasks[chat_id] = task

        # Send one immediate reply to the replied-to message
        text = random.choice(RR_MESSAGES)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to.message_id
            )
        except Exception:
            pass

        await update.message.reply_text(
            f"[Bot {self.bot_number}] 🔁 Auto-RR started! Replying to every message from {target_name}. Use .stoprr to stop."
        )

    async def stoprr_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat_id = update.effective_chat.id

        if chat_id in self.active_rr_tasks:
            task = self.active_rr_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_rr_tasks[chat_id]

        if chat_id in self.active_rr_targets:
            del self.active_rr_targets[chat_id]

        if chat_id in self.pending_rr_replies:
            del self.pending_rr_replies[chat_id]

        await update.message.reply_text(f"[Bot {self.bot_number}] 🛑 Auto-RR stopped!")

    async def rrspam_loop(self, chat_id, msg_id, context):
        print(f"[Bot {self.bot_number}] RRSPAM LOOP started for chat {chat_id}")
        success_count = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    text = random.choice(RR_MESSAGES)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_to_message_id=msg_id
                    )
                    success_count += 1
                    GLOBAL_STATS["messages_sent"] += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] RRSPAM LOOP stopped after {success_count} messages")

    async def rrspam_command(self, update, context):
        if not await self.check_owner(update):
            return

        reply_to = update.message.reply_to_message
        if not reply_to:
            await update.message.reply_text("Reply to someone's message with .rrspam to start spamming RR replies.")
            return

        chat_id = update.effective_chat.id
        target_user = reply_to.from_user
        if not target_user:
            await update.message.reply_text("Could not identify the target user.")
            return

        target_name = target_user.first_name or str(target_user.id)
        msg_id = reply_to.message_id

        if chat_id in self.active_rrspam_tasks:
            old_task = self.active_rrspam_tasks[chat_id]
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass

        self.active_rrspam_targets[chat_id] = (target_user.id, msg_id)
        task = asyncio.create_task(self.rrspam_loop(chat_id, msg_id, context))
        self.active_rrspam_tasks[chat_id] = task

        await update.message.reply_text(
            f"[Bot {self.bot_number}] 💥 RRSPAM started on {target_name}! Use .stoprrspam to stop."
        )

    async def stop_rrspam_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat_id = update.effective_chat.id

        if chat_id in self.active_rrspam_tasks:
            task = self.active_rrspam_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_rrspam_tasks[chat_id]

        if chat_id in self.active_rrspam_targets:
            del self.active_rrspam_targets[chat_id]

        await update.message.reply_text(f"[Bot {self.bot_number}] 🛑 RRSPAM stopped!")


    async def name_change_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        num_messages = len(NAME_CHANGE_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] Name change LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = NAME_CHANGE_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    GLOBAL_STATS["name_changes"] += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] Name change LOOP #{worker_id} stopped after {success_count} changes")

    async def flower_nc_loop(self, chat_id, base_name, context):
        msg_index = 0
        num_messages = len(FLOWER_NC_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] FLOWER NC LOOP started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1)
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = FLOWER_NC_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] FLOWER NC LOOP stopped after {success_count} changes")
    async def pookie_nc_loop(self, chat_id, base_name, context):
        msg_index = 0
        num_messages = len(POOKIE_NC_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] POOKIE NC LOOP started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1)
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = POOKIE_NC_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] POOKIE NC LOOP stopped after {success_count} changes")


    async def nc_emo_loop(self, chat_id, base_name, context):
        success_count = 0
        print(f"[Bot {self.bot_number}] NC EMO LOOP started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1)
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    emoji = random.choice(HEART_EMOJIS)
                    display_name = f"{emoji} {base_name} {emoji}"
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except Exception:
                    await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] NC EMO LOOP stopped after {success_count} changes")

    async def nc_moon_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        num_messages = len(NC_MOON_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] NC MOON LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = NC_MOON_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] NC MOON LOOP #{worker_id} stopped after {success_count} changes")

    async def rand_nc_loop(self, chat_id, base_name, context, worker_id=1):
        success_count = 0
        print(f"[Bot {self.bot_number}] RAND NC LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = random.choice(RAND_NC_MESSAGES)
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] RAND NC LOOP #{worker_id} stopped after {success_count} changes")

    # ======== FAST NC LOOP (EMOJI + TEXT) ========
    async def fast_nc_loop(self, chat_id, base_name, context, worker_id=1):
        success_count = 0
        msg_index = 0
        num_messages = len(FAST_NC_MESSAGES)
        print(f"[Bot {self.bot_number}] FAST NC LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = FAST_NC_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] FAST NC LOOP #{worker_id} stopped after {success_count} changes")

    async def nc_flag_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        num_messages = len(NC_FLAG_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] NC FLAG LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = NC_FLAG_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] NC FLAG LOOP #{worker_id} stopped after {success_count} changes")

    async def nc_bolt_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        num_messages = len(NC_BOLT_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] NC BOLT LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = NC_BOLT_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] NC BOLT LOOP #{worker_id} stopped after {success_count} changes")

    async def curly_loop(self, chat_id, base_name, context, worker_id=1):
        msg_index = 0
        num_messages = len(NC_CURLY_MESSAGES)
        success_count = 0
        print(f"[Bot {self.bot_number}] CURLY LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    current_msg = NC_CURLY_MESSAGES[msg_index % num_messages]
                    display_name = current_msg.format(target=base_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=display_name)
                    msg_index += 1
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(2.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(2.0)
                    msg_index += 1
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] CURLY LOOP #{worker_id} stopped after {success_count} changes")

    async def gc_loop(self, chat_id, context):
        success_count = 0
        print(f"[Bot {self.bot_number}] GC LOOP started for chat {chat_id}")
        image_paths = ["gc_image_1.png", "gc_image_2.png"]
        msg_index = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                available_images = [p for p in image_paths if os.path.exists(p)]
                if not available_images:
                    await asyncio.sleep(2.0)
                    continue
                current_path = available_images[msg_index % len(available_images)]
                for bot_obj in ALL_BOTS.values():
                    try:
                        with open(current_path, 'rb') as photo:
                            await bot_obj.set_chat_photo(chat_id=chat_id, photo=photo)
                        success_count += 1
                        await asyncio.sleep(0.3)
                    except asyncio.CancelledError:
                        raise
                    except RetryAfter as e:
                        wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                        await asyncio.sleep(wait_time)
                    except (TimedOut, NetworkError) as e:
                        print(f"[Bot {self.bot_number}] GC Error: {e}")
                        await asyncio.sleep(1.0)
                    except Exception as e:
                        print(f"[Bot {self.bot_number}] GC Error: {e}")
                        await asyncio.sleep(1.0)
                msg_index += 1
                if delay > 0:
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] GC LOOP stopped after {success_count} changes")

    async def set_gc_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        message = update.message
        photo = None
        
        if message.reply_to_message and message.reply_to_message.photo:
            photo = message.reply_to_message.photo[-1]
        elif message.photo:
            photo = message.photo[-1]
            
        if not photo:
            await update.message.reply_text("Usage: Reply to a photo with -setgc [1 or 2] or send a photo with .setgc [1 or 2] caption")
            return
            
        # Determine slot
        slot = "1"
        if context.args:
            if context.args[0] in ["1", "2"]:
                slot = context.args[0]
            
        filename = f"gc_image_{slot}.png"
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(filename)
        await update.message.reply_text(f"Group 𝙞𝙢𝙖𝙜𝙚 𝙨𝙖𝙫𝙚𝙙 𝙩𝙤 𝙎𝙡𝙤𝙩  {slot}! ✅ Use .??𝙘 𝙩𝙤 𝙨𝙩𝙖𝙧𝙩 𝙩𝙝𝙚 𝙡𝙤𝙤𝙥 𝙘𝙮𝙘𝙡𝙞𝙣𝙜 𝙗𝙚𝙩𝙬𝙚𝙚𝙣 𝙖𝙫𝙖𝙞𝙡𝙖𝙗𝙡𝙚 𝙞𝙢𝙖𝙜𝙚𝙨.")

    async def ping_command(self, update, context):
        if not await self.check_owner(update):
            return
        
        start_time = time.time()
        sent_message = await update.message.reply_text("Pinging...")
        end_time = time.time()
        
        latency = (end_time - start_time) * 1000
        await sent_message.edit_text(f"Bot {self.bot_number} Ping: {latency:.2f}𝙢𝙨 ⚡")

    async def uptime_command(self, update, context):
        if not await self.check_owner(update):
            return

        def fmt_duration(seconds):
            seconds = int(seconds)
            d, rem = divmod(seconds, 86400)
            h, rem = divmod(rem, 3600)
            m, s = divmod(rem, 60)
            parts = []
            if d: parts.append(f"{d}d")
            if h: parts.append(f"{h}h")
            if m: parts.append(f"{m}m")
            parts.append(f"{s}s")
            return " ".join(parts)

        now = time.time()
        system_uptime = fmt_duration(now - SYSTEM_START_TIME)
        started_at = datetime.datetime.fromtimestamp(SYSTEM_START_TIME).strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"⚡ 𝙎𝙮𝙨𝙩𝙚𝙢 𝙐𝙥𝙩𝙞𝙢𝙚: {system_uptime}",
            f"🕐 𝙎𝙩𝙖𝙧𝙩𝙚𝙙 𝘼𝙩: {started_at}",
            f"",
            f"Bot Status:",
        ]
        for bot_num in sorted(BOT_START_TIMES.keys()):
            bot_up = fmt_duration(now - BOT_START_TIMES[bot_num])
            bot_time = datetime.datetime.fromtimestamp(BOT_START_TIMES[bot_num]).strftime("%H:%M:%S")
            lines.append(f"  Bot {bot_num} — up {bot_up} (since {bot_time})")

        if not BOT_START_TIMES:
            lines.append("  No bots registered yet.")

        await update.message.reply_text("\n".join(lines))

    async def spam_loop(self, chat_id, target_name, context, worker_id):
        success_count = 0
        templates = [SPAM_MESSAGE_TEMPLATE, SPAM_MESSAGE_2, SPAM_MESSAGE_3]
        print(f"[Bot {self.bot_number}] Spam LOOP #{worker_id} started for chat {chat_id}")
        stagger = (self.bot_number - 1) * 0.15 + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    template = templates[success_count % len(templates)]
                    spam_msg = template.format(target=target_name)
                    await context.bot.send_message(chat_id=chat_id, text=spam_msg)
                    success_count += 1
                    GLOBAL_STATS["messages_sent"] += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] Spam LOOP #{worker_id} stopped after {success_count} messages")

    async def reply_loop(self, chat_id, target_name, context):
        success_count = 0
        print(f"[Bot {self.bot_number}] Reply LOOP started for chat {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                if chat_id in self.pending_replies and self.pending_replies[chat_id]:
                    async with self.get_lock(chat_id):
                        messages_to_reply = self.pending_replies[chat_id].copy()
                        self.pending_replies[chat_id] = []

                    for msg_id in messages_to_reply:
                        try:
                            reply_msg = random.choice(REPLY_MESSAGES).format(target=target_name)
                            await context.bot.send_message(
                                chat_id=chat_id, 
                                text=reply_msg,
                                reply_to_message_id=msg_id
                            )
                            success_count += 1
                            GLOBAL_STATS["replies_sent"] += 1
                            if delay > 0:
                                await asyncio.sleep(delay)
                        except asyncio.CancelledError:
                            raise
                        except RetryAfter as e:
                            wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                            await asyncio.sleep(wait_time)
                        except Exception:
                            await asyncio.sleep(1.0)
                else:
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] Reply LOOP stopped after {success_count} replies")

    async def rr_loop(self, chat_id, context):
        print(f"[Bot {self.bot_number}] RR LOOP started for chat {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                if chat_id in self.pending_rr_replies and self.pending_rr_replies[chat_id]:
                    async with self.get_lock(chat_id):
                        messages_to_reply = self.pending_rr_replies[chat_id].copy()
                        self.pending_rr_replies[chat_id] = []
                    for msg_id in messages_to_reply:
                        try:
                            text = random.choice(RR_MESSAGES)
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=text,
                                reply_to_message_id=msg_id
                            )
                            if delay > 0:
                                await asyncio.sleep(delay)
                        except asyncio.CancelledError:
                            raise
                        except RetryAfter as e:
                            wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                            await asyncio.sleep(wait_time)
                        except Exception:
                            await asyncio.sleep(1.0)
                else:
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] RR LOOP stopped for chat {chat_id}")

    async def message_collector(self, update, context):
        # We need to handle both message and channel_post
        msg = update.message or update.channel_post
        if not msg:
            return
            
        chat_id = update.effective_chat.id
        
        # Custom reaction logic
        if chat_id in self.active_react_chats:
            try:
                # Use set_message_reaction which is the modern method
                # Removing reaction limit checks for max speed
                await msg.react(reaction="🤣")
            except Exception as e:
                # Fallback to bot method if message object reaction fails
                try:
                    await context.bot.set_message_reaction(
                        chat_id=chat_id,
                        message_id=msg.message_id,
                        reaction=[{"type": "emoji", "emoji": "🤣"}]
                    )
                except Exception:
                    pass
                pass


        if not msg.text:
            return

        text = msg.text.lower()
        chat_id = update.effective_chat.id

        # Trigger for taixochutiya
        if "taixochutiya" in text:
            await update.message.reply_text("HATER Tᴇʀɪ ᴍᴏᴍ Cᴏᴍ Qᴜᴇᴇɴ 👑♥️")
            return

        if chat_id in self.active_reply_targets:
            msg_id = update.message.message_id
            async with self.get_lock(chat_id):
                if chat_id not in self.pending_replies:
                    self.pending_replies[chat_id] = []
                self.pending_replies[chat_id].append(msg_id)

        if chat_id in self.active_rr_targets:
            sender_id = msg.from_user.id if msg.from_user else None
            if sender_id and sender_id == self.active_rr_targets[chat_id]:
                msg_id = msg.message_id
                async with self.get_lock(chat_id):
                    if chat_id not in self.pending_rr_replies:
                        self.pending_rr_replies[chat_id] = []
                    self.pending_rr_replies[chat_id].append(msg_id)

    async def nc_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat = update.effective_chat

        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        if not context.args:
            await update.message.reply_text("Usage: /nc <name>")
            return

        base_name = " ".join(context.args)
        chat_id = chat.id

        if chat_id in self.active_name_change_tasks:
            old_tasks = self.active_name_change_tasks[chat_id]
            for task in old_tasks:
                task.cancel()
            for task in old_tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.name_change_loop(chat_id, base_name, context, i+1))
            tasks.append(task)

        self.active_name_change_tasks[chat_id] = tasks

        await update.message.reply_text(f"[Bot {self.bot_number}] ⚡ 𝙉𝙖𝙢𝙚 𝙘𝙝𝙖𝙣𝙜𝙚 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧??𝙚𝙙 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨!")

    async def stop_nc_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat_id = update.effective_chat.id

        if chat_id in self.active_name_change_tasks:
            tasks = self.active_name_change_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_name_change_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] Name change LOOP stopped!")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active name change loop!")

    async def spam_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat = update.effective_chat

        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        if not context.args:
            await update.message.reply_text("Usage: /spam <target>")
            return

        target_name = " ".join(context.args)
        chat_id = chat.id

        if chat_id in self.active_spam_tasks:
            tasks = self.active_spam_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.spam_loop(chat_id, target_name, context, i+1))
            tasks.append(task)

        self.active_spam_tasks[chat_id] = tasks
        await update.message.reply_text(f"[Bot {self.bot_number}] 💣 𝙎𝙥𝙖𝙢 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨! 𝙍𝙪𝙣𝙣𝙞𝙣𝙜 𝙘𝙤𝙣𝙩𝙞𝙣𝙪𝙤𝙪𝙨𝙡𝙮...")

    async def stop_spam_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat_id = update.effective_chat.id

        if chat_id in self.active_spam_tasks:
            tasks = self.active_spam_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_spam_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] Spam LOOP stopped!")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active spam loop!")


    async def multigc_nc_loop(self, chat_id, target_name, context, worker_id=1):
        msg_index = 0
        num_messages = len(MULTIGC_NC_MESSAGES)
        stagger = (self.bot_number - 1) / max(len(BOT_TOKENS), 1) + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    msg = MULTIGC_NC_MESSAGES[msg_index % num_messages].format(target=target_name)
                    await context.bot.set_chat_title(chat_id=chat_id, title=msg)
                    msg_index += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time + random.uniform(0, 0.5))
                except Exception:
                    await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass

    async def multigc_spam_loop(self, chat_id, target_name, context, worker_id=1):
        success_count = 0
        num_messages = len(MULTIGC_SPAM_MESSAGES)
        stagger = (self.bot_number - 1) * 0.15 + (worker_id - 1) * 0.05
        if stagger > 0:
            await asyncio.sleep(stagger)
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    msg = MULTIGC_SPAM_MESSAGES[success_count % num_messages].format(target=target_name)
                    await context.bot.send_message(chat_id=chat_id, text=msg)
                    success_count += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(0.05)
                except Exception:
                    await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass

    async def multigc_gc_loop(self, chat_id, context):
        image_paths = ["gc_image_1.png", "gc_image_2.png"]
        msg_index = 0
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                available = [p for p in image_paths if os.path.exists(p)]
                if not available:
                    await asyncio.sleep(2.0)
                    continue
                path = available[msg_index % len(available)]
                for bot_obj in ALL_BOTS.values():
                    try:
                        with open(path, 'rb') as photo:
                            await bot_obj.set_chat_photo(chat_id=chat_id, photo=photo)
                        await asyncio.sleep(0.3)
                    except asyncio.CancelledError:
                        raise
                    except RetryAfter as e:
                        wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                        await asyncio.sleep(wait_time)
                    except Exception:
                        await asyncio.sleep(1.0)
                msg_index += 1
                if delay > 0:
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass

    async def multigc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .multigc <target>")
            return
        target_name = " ".join(context.args)
        chat_id = chat.id

        if chat_id in self.active_multigc_tasks:
            for task in self.active_multigc_tasks[chat_id]:
                task.cancel()
            for task in self.active_multigc_tasks[chat_id]:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_multigc_tasks[chat_id]

        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            tasks.append(asyncio.create_task(self.fast_nc_loop(chat_id, target_name, context, i + 1)))
            tasks.append(asyncio.create_task(self.multigc_spam_loop(chat_id, target_name, context, i + 1)))
        tasks.append(asyncio.create_task(self.multigc_gc_loop(chat_id, context)))
        self.active_multigc_tasks[chat_id] = tasks

        await update.message.reply_text(
            f"[Bot {self.bot_number}] 💥 MULTIGC STARTED! NC + SPAM + GC PFP running for {target_name} with {num_threads} threads! 🔥"
        )

    async def stop_multigc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_multigc_tasks:
            for task in self.active_multigc_tasks[chat_id]:
                task.cancel()
            for task in self.active_multigc_tasks[chat_id]:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_multigc_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] MULTIGC stopped! 🛑")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active MULTIGC loop!")

    async def target_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat = update.effective_chat

        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        if not context.args:
            await update.message.reply_text("Usage: /target <name>")
            return

        target_name = " ".join(context.args)
        chat_id = chat.id

        if chat_id in self.active_name_change_tasks:
            old_tasks = self.active_name_change_tasks[chat_id]
            for task in old_tasks:
                task.cancel()
            for task in old_tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if chat_id in self.active_spam_tasks:
            tasks = self.active_spam_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        num_threads = self.chat_threads.get(chat_id, 1)

        nc_tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.name_change_loop(chat_id, target_name, context, i+1))
            nc_tasks.append(task)
        self.active_name_change_tasks[chat_id] = nc_tasks

        spam_tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.spam_loop(chat_id, target_name, context, i+1))
            spam_tasks.append(task)
        self.active_spam_tasks[chat_id] = spam_tasks

        total_threads = num_threads * 2
        await update.message.reply_text(f"[Bot {self.bot_number}] 🎯 TARGET MODE: NC ({num_threads}) + SPAM ({num_threads}) = {total_threads} threads running!")

    async def reply_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat = update.effective_chat

        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        if not context.args:
            await update.message.reply_text("Usage: /reply <target>")
            return

        target_name = " ".join(context.args)
        chat_id = chat.id

        if chat_id in self.active_reply_tasks:
            old_task = self.active_reply_tasks[chat_id]
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass

        self.active_reply_targets[chat_id] = target_name
        self.pending_replies[chat_id] = []

        task = asyncio.create_task(self.reply_loop(chat_id, target_name, context))
        self.active_reply_tasks[chat_id] = task

        await update.message.reply_text(f"[Bot {self.bot_number}] 💬 𝙍𝙚𝙥𝙡𝙮 𝙇𝙊𝙊𝙋 𝙖𝙘𝙩𝙞𝙫𝙖𝙩𝙚𝙙! 𝙍𝙚𝙥𝙡𝙮𝙞𝙣𝙜 𝙩𝙤 𝙚𝙫𝙚𝙧𝙮 𝙢𝙚𝙨𝙨𝙖𝙜𝙚...")

    async def stop_reply_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat_id = update.effective_chat.id

        if chat_id in self.active_reply_tasks:
            task = self.active_reply_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_reply_tasks[chat_id]

        if chat_id in self.active_reply_targets:
            del self.active_reply_targets[chat_id]

        if chat_id in self.pending_replies:
            del self.pending_replies[chat_id]

        await update.message.reply_text(f"[Bot {self.bot_number}] Reply LOOP stopped!")

    async def imagespam_loop(self, chat_id, file_id, context):
        print(f"[Bot {self.bot_number}] IMAGESPAM LOOP started for chat {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=file_id)
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time)
                except Exception:
                    await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] IMAGESPAM LOOP stopped for chat {chat_id}")

    async def imagespam_command(self, update, context):
        if not await self.check_owner(update):
            return
        msg = update.message
        if not msg:
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await msg.reply_text("This command only works in groups!")
            return
        if not msg.reply_to_message or not msg.reply_to_message.photo:
            await msg.reply_text("❌ Reply to a photo with .imagespam")
            return
        file_id = msg.reply_to_message.photo[-1].file_id
        chat_id = chat.id
        if chat_id in self.active_imagespam_tasks:
            self.active_imagespam_tasks[chat_id].cancel()
            try:
                await self.active_imagespam_tasks[chat_id]
            except asyncio.CancelledError:
                pass
        self.imagespam_file_ids[chat_id] = file_id
        task = asyncio.create_task(self.imagespam_loop(chat_id, file_id, context))
        self.active_imagespam_tasks[chat_id] = task
        await msg.reply_text(f"[Bot {self.bot_number}] 📷 𝙄𝙈𝘼𝙂𝙀𝙎𝙋𝘼𝙈 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙!")

    async def stop_imagespam_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_imagespam_tasks:
            self.active_imagespam_tasks[chat_id].cancel()
            try:
                await self.active_imagespam_tasks[chat_id]
            except asyncio.CancelledError:
                pass
            del self.active_imagespam_tasks[chat_id]
        if chat_id in self.imagespam_file_ids:
            del self.imagespam_file_ids[chat_id]
        await update.message.reply_text(f"[Bot {self.bot_number}] 📷 IMAGESPAM LOOP stopped!")

    async def delay_command(self, update, context):
        if not await self.check_owner(update):
            return

        if not context.args:
            await update.message.reply_text("Usage: /delay <seconds>")
            return

        try:
            delay = float(context.args[0])
            if delay < 0:
                await update.message.reply_text("Delay must be >= 0")
                return

            chat_id = update.effective_chat.id
            self.chat_delays[chat_id] = delay
            await update.message.reply_text(f"[Bot {self.bot_number}] Delay set to {delay}s (applies to all loops)")
        except ValueError:
            await update.message.reply_text("Invalid delay value!")

    async def threads_command(self, update, context):
        if not await self.check_owner(update):
            return

        if not context.args:
            await update.message.reply_text("Usage: /threads <number>")
            return

        try:
            threads = int(context.args[0])
            if threads < 1 or threads > 50:
                await update.message.reply_text("Threads must be between 1 and 50")
                return

            chat_id = update.effective_chat.id
            self.chat_threads[chat_id] = threads
            await update.message.reply_text(f"[Bot {self.bot_number}] Threads set to {threads} (applies to NC + SPAM)")
        except ValueError:
            await update.message.reply_text("Invalid threads value!")

    async def stop_all_command(self, update, context):
        if not await self.check_owner(update):
            return

        chat_id = update.effective_chat.id
        stopped = []

        # List of all task categories to stop
        task_categories = [
            (self.active_name_change_tasks, "name change loop"),
            (self.active_ncmoon_tasks, "nc moon loop"),
            (self.active_ncflag_tasks, "nc flag loop"),
            (self.active_ncbolt_tasks, "nc bolt loop"),
            (self.active_cheerync_tasks, "rand nc loop"),
            (self.active_curly_tasks, "curly loop"),
            (self.active_spam_tasks, "spam loop"),
            (self.active_multigc_tasks, "multigc loop"),
        ]

        for task_dict, label in task_categories:
            if chat_id in task_dict:
                tasks = task_dict[chat_id]
                # Handle both list of tasks and single task
                if not isinstance(tasks, list):
                    tasks = [tasks]
                for task in tasks:
                    task.cancel()
                for task in tasks:
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del task_dict[chat_id]
                stopped.append(label)

        if chat_id in self.active_reply_tasks:
            task = self.active_reply_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_reply_tasks[chat_id]
            stopped.append("reply loop")

        if chat_id in self.active_reply_targets:
            del self.active_reply_targets[chat_id]

        if chat_id in self.pending_replies:
            del self.pending_replies[chat_id]

        if chat_id in self.active_rrspam_tasks:
            task = self.active_rrspam_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_rrspam_tasks[chat_id]
            self.active_rrspam_targets.pop(chat_id, None)
            stopped.append("rrspam loop")

        if chat_id in self.active_imagespam_tasks:
            task = self.active_imagespam_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_imagespam_tasks[chat_id]
            if chat_id in self.imagespam_file_ids:
                del self.imagespam_file_ids[chat_id]
            stopped.append("imagespam loop")

        if chat_id in self.active_fwdspam_tasks:
            task = self.active_fwdspam_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_fwdspam_tasks[chat_id]
            self.fwdspam_sources.pop(chat_id, None)
            stopped.append("fwdspam loop")

        if chat_id in self.active_emojirain_tasks:
            task = self.active_emojirain_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_emojirain_tasks[chat_id]
            stopped.append("emojirain loop")

        if chat_id in self.active_setdesc_tasks:
            task = self.active_setdesc_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_setdesc_tasks[chat_id]
            stopped.append("setdesc loop")

        if chat_id in self.active_bignc_tasks:
            task = self.active_bignc_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_bignc_tasks[chat_id]
            stopped.append("bignc loop")

        if chat_id in self.active_fastnc_tasks:
            tasks = self.active_fastnc_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_fastnc_tasks[chat_id]
            stopped.append("fastnc loop")

        if hasattr(self, 'active_gc_tasks') and chat_id in self.active_gc_tasks:
            task = self.active_gc_tasks[chat_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_gc_tasks[chat_id]
            stopped.append("gc loop")

        if stopped:
            await update.message.reply_text(f"[Bot {self.bot_number}] 𝙎𝙩𝙤𝙥𝙥𝙚𝙙: {', '.join(stopped)} ✅")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active loops to stop!")

    async def flower_nc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .flowernc <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id

        if chat_id in self.active_name_change_tasks:
            tasks = self.active_name_change_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            del self.active_name_change_tasks[chat_id]

        task = asyncio.create_task(self.flower_nc_loop(chat_id, base_name, context))
        self.active_name_change_tasks[chat_id] = [task]
        await update.message.reply_text(f"[Bot {self.bot_number}] 🌸 𝖙𝖳𝖼𝖺𝗘𝗒 𝖝𝗖 𝖳𝖼𝖼𝖿 𝘀𝖙𝖮𝖿𝖙𝗘𝗗!")


    async def annunc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: /annunc <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id

        if chat_id in self.active_name_change_tasks:
            tasks = self.active_name_change_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            del self.active_name_change_tasks[chat_id]

        task = asyncio.create_task(self.pookie_nc_loop(chat_id, base_name, context))
        self.active_name_change_tasks[chat_id] = [task]
        await update.message.reply_text(f"[Bot {self.bot_number}] 🍬 𝘼𝙉𝙉𝙐 𝙉𝘾 𝙇𝙊𝙊𝙋 𝙎𝙏𝘼𝙍𝙏𝙀𝘿!")

    async def nc_emo_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: /ncemo <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id
        if chat_id in self.active_name_change_tasks:
            tasks = self.active_name_change_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            del self.active_name_change_tasks[chat_id]
        task = asyncio.create_task(self.nc_emo_loop(chat_id, base_name, context))
        self.active_name_change_tasks[chat_id] = [task]
        await update.message.reply_text(f"[Bot {self.bot_number}] ⚡ 𝙉𝘾 𝙀𝙈𝙊 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙!")

    async def ncmoon_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: /ncmoon <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id
        if chat_id in self.active_ncmoon_tasks:
            old_tasks = self.active_ncmoon_tasks[chat_id]
            for task in old_tasks:
                task.cancel()
            for task in old_tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.nc_moon_loop(chat_id, base_name, context, i+1))
            tasks.append(task)
        self.active_ncmoon_tasks[chat_id] = tasks
        await update.message.reply_text(f"[Bot {self.bot_number}] 🌙 𝙉𝘾 𝙈𝙊𝙊𝙉 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨!")

    async def stop_ncmoon_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_ncmoon_tasks:
            tasks = self.active_ncmoon_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_ncmoon_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] NC MOON LOOP stopped!")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active NC Moon loop!")

    async def cheerync_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .cheerync <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id
        if chat_id in self.active_cheerync_tasks:
            old_tasks = self.active_cheerync_tasks[chat_id]
            for task in old_tasks:
                task.cancel()
            for task in old_tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.rand_nc_loop(chat_id, base_name, context, i + 1))
            tasks.append(task)
        self.active_cheerync_tasks[chat_id] = tasks
        await update.message.reply_text(
            f"[Bot {self.bot_number}] 🎲 𝘾𝙃𝙀𝙀𝙍𝙔 𝙉𝘾 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨! 𝘾𝙮𝙘𝙡𝙞𝙣𝙜 12 𝙧𝙖𝙣𝙙𝙤𝙢 𝙩𝙚𝙭𝙩𝙨!"
        )

    async def stop_cheerync_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_cheerync_tasks:
            tasks = self.active_cheerync_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_cheerync_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] 🛑 𝙍𝘼𝙉𝘿 𝙉𝘾 𝙇𝙊𝙊𝙋 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active RAND NC loop!")

    async def fastnc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .fastnc <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id
        if chat_id in self.active_fastnc_tasks:
            old_tasks = self.active_fastnc_tasks[chat_id]
            for task in old_tasks:
                task.cancel()
            for task in old_tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.fast_nc_loop(chat_id, base_name, context, i + 1))
            tasks.append(task)
        self.active_fastnc_tasks[chat_id] = tasks
        await update.message.reply_text(
            f"[Bot {self.bot_number}] ⚡ 𝙁𝘼𝙎𝙏 𝙉𝘾 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨! 🔥 {len(FAST_NC_MESSAGES)} 𝙀𝙢𝙤𝙟𝙞+𝙏𝙚𝙭𝙩 𝙩𝙞𝙩𝙡𝙚𝙨 𝙘𝙮𝙘𝙡𝙞𝙣𝙜!"
        )

    async def stopfastnc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_fastnc_tasks:
            tasks = self.active_fastnc_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_fastnc_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] 🛑 𝙁𝘼𝙎𝙏 𝙉𝘾 𝙇𝙊𝙊𝙋 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active FAST NC loop!")

    async def ncflag_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: /ncflag <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id
        if chat_id in self.active_ncflag_tasks:
            old_tasks = self.active_ncflag_tasks[chat_id]
            for task in old_tasks:
                task.cancel()
            for task in old_tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.nc_flag_loop(chat_id, base_name, context, i+1))
            tasks.append(task)
        self.active_ncflag_tasks[chat_id] = tasks
        await update.message.reply_text(f"[Bot {self.bot_number}] 🚩 𝙉𝘾 𝙁𝙇𝘼𝙂 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨!")

    async def stop_ncflag_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_ncflag_tasks:
            tasks = self.active_ncflag_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_ncflag_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] NC FLAG LOOP stopped!")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active NC Flag loop!")

    async def ncbolt_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .ncbolt <name>")
            return
        base_name = " ".join(context.args)
        chat_id = chat.id
        if chat_id in self.active_ncbolt_tasks:
            old_tasks = self.active_ncbolt_tasks[chat_id]
            for task in old_tasks:
                task.cancel()
            for task in old_tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        num_threads = self.chat_threads.get(chat_id, 1)
        tasks = []
        for i in range(num_threads):
            task = asyncio.create_task(self.nc_bolt_loop(chat_id, base_name, context, i+1))
            tasks.append(task)
        self.active_ncbolt_tasks[chat_id] = tasks
        await update.message.reply_text(f"[Bot {self.bot_number}] ⚡ 𝙉𝘾 𝘽𝙊𝙇𝙏 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙬𝙞𝙩𝙝 {num_threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨!")

    async def stop_ncbolt_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_ncbolt_tasks:
            tasks = self.active_ncbolt_tasks[chat_id]
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_ncbolt_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] ⚡ 𝙉𝘾 𝘽𝙊𝙇𝙏 𝙇𝙊𝙊𝙋 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active NC Bolt loop!")

    async def nccurly_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .nccurly <name>")
            return
        
        target_name = " ".join(context.args)
        chat_id = chat.id
        threads = self.chat_threads.get(chat_id, 1)

        if chat_id in self.active_curly_tasks:
            for task in self.active_curly_tasks[chat_id]:
                task.cancel()
        
        self.active_curly_tasks[chat_id] = []
        for i in range(threads):
            task = asyncio.create_task(self.curly_loop(chat_id, target_name, context, i+1))
            self.active_curly_tasks[chat_id].append(task)
        
        await update.message.reply_text(f"[Bot {self.bot_number}] 𝘿𝙤𝙪𝙗𝙡𝙚 𝘾𝙪𝙧𝙡𝙮 𝙡𝙤𝙤𝙥 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙛𝙤𝙧 '{target_name}' with {threads} 𝙩𝙝𝙧𝙚𝙖𝙙𝙨! 🌀")

    async def stop_nccurly_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_curly_tasks:
            for task in self.active_curly_tasks[chat_id]:
                task.cancel()
            for task in self.active_curly_tasks[chat_id]:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.active_curly_tasks[chat_id]
            await update.message.reply_text(f"[Bot {self.bot_number}] 𝘿𝙤𝙪𝙗𝙡𝙚 𝘾𝙪𝙧𝙡𝙮 𝙡𝙤𝙤𝙥 𝙨𝙩𝙤𝙥𝙥𝙚𝙙! 🛑")
        else:
            await update.message.reply_text(f"[Bot {self.bot_number}] No active Double Curly loop!")

    async def gc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        chat_id = chat.id
        task = asyncio.create_task(self.gc_loop(chat_id, context))
        # Store in a new dict or reuse active_spam_tasks if appropriate
        if not hasattr(self, 'active_gc_tasks'): self.active_gc_tasks = {}
        self.active_gc_tasks[chat_id] = task
        await update.message.reply_text(f"[Bot {self.bot_number}] 🖼️ 𝙂𝙧𝙤𝙪𝙥 𝙄𝙢𝙖𝙜𝙚 𝘾𝙝𝙖𝙣𝙜𝙚 𝙇𝙊𝙊𝙋 𝙨𝙩𝙖𝙧𝙩𝙚𝙙!")

    async def upadmin_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        try:
            me = await context.bot.get_me()
        except Exception as e:
            await update.message.reply_text(f"Failed to get bot info: {e}")
            return

        target_ids = [bid for bid in ALL_BOT_IDS if bid != me.id]
        if not target_ids:
            await update.message.reply_text("No other bots registered to promote!")
            return

        promoted = 0
        failed = 0
        errors = []
        for bot_id in target_ids:
            try:
                await context.bot.promote_chat_member(
                    chat_id=chat.id,
                    user_id=bot_id,
                    can_change_info=True,
                    can_delete_messages=True,
                    can_invite_users=True,
                    can_restrict_members=True,
                    can_pin_messages=True,
                    can_promote_members=True,
                    can_manage_chat=True,
                    can_manage_video_chats=True,
                )
                promoted += 1
            except Exception as e:
                failed += 1
                errors.append(f"{bot_id}: {e}")
                print(f"[Bot {self.bot_number}] Failed to promote {bot_id}: {e}")

        msg = f"✅ 𝙋𝙧𝙤𝙢𝙤𝙩𝙚𝙙 {promoted} 𝙗𝙤𝙩(s) 𝙩𝙤 𝙖𝙙𝙢𝙞𝙣!"
        if failed:
            msg += f"\n❌ {failed} failed (this bot must be admin with 'Add New Admins' permission)."
        await update.message.reply_text(msg)

    async def fwdspam_loop(self, chat_id, from_chat_id, message_id, context):
        success_count = 0
        print(f"[Bot {self.bot_number}] FwdSpam LOOP started for chat {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    await context.bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=from_chat_id,
                        message_id=message_id,
                    )
                    success_count += 1
                    GLOBAL_STATS["fwd_spam_sent"] += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except Exception as e:
                    error_str = str(e).lower()
                    retry_after = extract_retry_after(error_str)
                    if retry_after:
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] FwdSpam LOOP stopped after {success_count} forwards")

    async def fwdspam_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        msg = update.message

        from_chat_id = None
        message_id = None

        if msg.reply_to_message:
            from_chat_id = chat_id
            message_id = msg.reply_to_message.message_id
        elif context.args:
            link = context.args[0].strip()
            import re as _re
            m = _re.search(r't\.me/c/(\d+)/(\d+)', link)
            if m:
                from_chat_id = int(f"-100{m.group(1)}")
                message_id = int(m.group(2))
            else:
                m2 = _re.search(r't\.me/(\w+)/(\d+)', link)
                if m2:
                    from_chat_id = f"@{m2.group(1)}"
                    message_id = int(m2.group(2))
        
        if from_chat_id is None or message_id is None:
            await msg.reply_text("Usage: reply to a message with .fwdspam\nOR: .fwdspam <t.me/c/CHATID/MSGID>")
            return

        if chat_id in self.active_fwdspam_tasks:
            self.active_fwdspam_tasks[chat_id].cancel()

        self.fwdspam_sources[chat_id] = (from_chat_id, message_id)
        task = asyncio.create_task(self.fwdspam_loop(chat_id, from_chat_id, message_id, context))
        self.active_fwdspam_tasks[chat_id] = task
        await msg.reply_text(f"📨 𝙁𝙬𝙙𝙎𝙥𝙖𝙢 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙞𝙣 𝙩𝙝𝙞𝙨 𝙘𝙝𝙖𝙩! (msg_id: {message_id})")

    async def stopfwdspam_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_fwdspam_tasks:
            self.active_fwdspam_tasks[chat_id].cancel()
            del self.active_fwdspam_tasks[chat_id]
            self.fwdspam_sources.pop(chat_id, None)
            await update.message.reply_text("✅ 𝙁𝙬𝙙𝙎𝙥𝙖𝙢 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!")
        else:
            await update.message.reply_text("No fwdspam running in this chat.")

    async def emojirain_loop(self, chat_id, emoji, context):
        line = emoji * 30
        block = "\n".join([line] * 20)
        print(f"[Bot {self.bot_number}] EmojiRain LOOP started for chat {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                try:
                    await context.bot.send_message(chat_id=chat_id, text=block)
                    GLOBAL_STATS["messages_sent"] += 1
                    if delay > 0:
                        await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                except RetryAfter as e:
                    wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                    await asyncio.sleep(wait_time)
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except Exception as e:
                    retry_after = extract_retry_after(str(e).lower())
                    await asyncio.sleep(retry_after if retry_after else 1.0)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] EmojiRain LOOP stopped for chat {chat_id}")

    async def emojirain_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        emoji = context.args[0] if context.args else "🔥"

        if chat_id in self.active_emojirain_tasks:
            self.active_emojirain_tasks[chat_id].cancel()

        task = asyncio.create_task(self.emojirain_loop(chat_id, emoji, context))
        self.active_emojirain_tasks[chat_id] = task
        await update.message.reply_text(f"🌧️ 𝙀𝙢𝙤𝙟𝙞𝙍𝙖𝙞𝙣 𝙨𝙩𝙖𝙧𝙩𝙚𝙙! ({emoji})")

    async def stopemojirain_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_emojirain_tasks:
            self.active_emojirain_tasks[chat_id].cancel()
            del self.active_emojirain_tasks[chat_id]
            await update.message.reply_text("✅ 𝙀𝙢𝙤𝙟𝙞𝙍𝙖𝙞𝙣 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!")
        else:
            await update.message.reply_text("No emojirain running in this chat.")

    async def setdesc_loop(self, chat_id, descriptions, context, target_name=""):
        index = 0
        print(f"[Bot {self.bot_number}] SetDesc LOOP started for chat {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 3)
                raw_desc = descriptions[index % len(descriptions)]
                desc = raw_desc.format(target=target_name) if target_name else raw_desc
                for bot_obj in ALL_BOTS.values():
                    try:
                        await bot_obj.set_chat_description(chat_id=chat_id, description=desc)
                        await asyncio.sleep(0.5)
                    except asyncio.CancelledError:
                        raise
                    except RetryAfter as e:
                        wait_time = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                        await asyncio.sleep(wait_time)
                    except (TimedOut, NetworkError):
                        await asyncio.sleep(2.0)
                    except Exception as e:
                        retry_after = extract_retry_after(str(e).lower())
                        await asyncio.sleep(retry_after if retry_after else 2.0)
                index += 1
                await asyncio.sleep(max(delay, 1))
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] SetDesc LOOP stopped for chat {chat_id}")

    async def setdesc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .setdesc <target name>")
            return

        target_name = " ".join(context.args)
        descriptions = SETDESC_MESSAGES

        if chat.id in self.active_setdesc_tasks:
            self.active_setdesc_tasks[chat.id].cancel()

        task = asyncio.create_task(self.setdesc_loop(chat.id, descriptions, context, target_name))
        self.active_setdesc_tasks[chat.id] = task
        await update.message.reply_text(
            f"🔄 𝙎𝙚𝙩𝘿𝙚𝙨𝙘 𝙡𝙤𝙤𝙥 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙛𝙤𝙧 {target_name}!"
        )

    async def stopsetdesc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_setdesc_tasks:
            self.active_setdesc_tasks[chat_id].cancel()
            del self.active_setdesc_tasks[chat_id]
            await update.message.reply_text("✅ 𝙎𝙚𝙩𝘿𝙚𝙨𝙘 𝙡𝙤𝙤𝙥 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!")
        else:
            await update.message.reply_text("No setdesc loop running in this chat.")

    async def bignc_loop(self, chat_id, titles, context):
        index = 0
        _flood_hits = 0
        print(f"[Bot {self.bot_number}] BIGNC LOOP started for chat {chat_id}")
        try:
            while True:
                delay = self.chat_delays.get(chat_id, 0)
                title = titles[index % len(titles)]

                # — STEALTH ENGINE: jitter delay to avoid pattern detection —
                jitter = random.uniform(0.05, 0.25)

                # — OPTIMIZE ENGINE: blast all bots concurrently —
                success = 0
                for bot_obj in ALL_BOTS.values():
                    try:
                        await bot_obj.set_chat_title(chat_id=chat_id, title=title)
                        success += 1
                        await asyncio.sleep(jitter)
                    except asyncio.CancelledError:
                        raise
                    except RetryAfter as e:
                        # — FLOODBYPASS: respect RetryAfter exactly —
                        _flood_hits += 1
                        wait = int(e.retry_after) if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
                        print(f"[Bot {self.bot_number}] BIGNC FloodWait {wait}s (hit #{_flood_hits})")
                        await asyncio.sleep(wait + random.uniform(0.5, 1.5))
                    except (TimedOut, NetworkError):
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        err = str(e).lower()
                        retry = extract_retry_after(err)
                        if retry:
                            await asyncio.sleep(retry + random.uniform(0.3, 0.8))
                        elif "not enough rights" in err or "chat_admin_required" in err:
                            await asyncio.sleep(2.0)
                        else:
                            await asyncio.sleep(1.0)

                index += 1
                if delay > 0:
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            print(f"[Bot {self.bot_number}] BIGNC LOOP stopped for chat {chat_id}")

    async def bignc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return
        if not context.args:
            await update.message.reply_text("Usage: .bignc <target name>")
            return

        target_name = " ".join(context.args)
        titles = [t.format(target=target_name) for t in BIGNC_MESSAGES]

        if chat.id in self.active_bignc_tasks:
            self.active_bignc_tasks[chat.id].cancel()

        task = asyncio.create_task(self.bignc_loop(chat.id, titles, context))
        self.active_bignc_tasks[chat.id] = task
        await update.message.reply_text(
            f"💀 𝘽𝙞𝙜𝙉𝘾 𝙡𝙤𝙤𝙥 𝙨𝙩𝙖𝙧𝙩𝙚𝙙 𝙛𝙤𝙧 {target_name}!\n"
            f"🔥 {len(titles)} 𝙩𝙞𝙩𝙡𝙚𝙨 𝙘𝙮𝙘𝙡𝙞𝙣𝙜 ⚡ 𝙎𝙩𝙚𝙖𝙡𝙩𝙝 + 𝙁𝙡𝙤𝙤𝙙𝘽𝙮𝙥𝙖𝙨𝙨 𝙖𝙘𝙩𝙞𝙫𝙚"
        )

    async def stopbignc_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat_id = update.effective_chat.id
        if chat_id in self.active_bignc_tasks:
            self.active_bignc_tasks[chat_id].cancel()
            del self.active_bignc_tasks[chat_id]
            await update.message.reply_text("✅ 𝘽𝙞𝙜𝙉𝘾 𝙡𝙤𝙤𝙥 𝙨𝙩𝙤𝙥𝙥𝙚𝙙!")
        else:
            await update.message.reply_text("No bignc loop running in this chat.")

    async def lock_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        from telegram import ChatPermissions
        no_perms = ChatPermissions(
            can_send_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )
        success = 0
        for bot_obj in ALL_BOTS.values():
            try:
                await bot_obj.set_chat_permissions(chat_id=chat.id, permissions=no_perms)
                success += 1
                break
            except Exception as e:
                print(f"[lock] Failed: {e}")

        if success:
            await update.message.reply_text("🔒 𝘾𝙝𝙖𝙩 𝙡𝙤𝙘𝙠𝙚𝙙! 𝙈𝙚𝙢𝙗𝙚𝙧𝙨 𝙘𝙖𝙣𝙣𝙤𝙩 𝙨𝙚𝙣𝙙 𝙢𝙚𝙨𝙨𝙖𝙜𝙚𝙨.")
        else:
            await update.message.reply_text("❌ Failed — make sure at least one bot is admin.")

    async def unlock_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        from telegram import ChatPermissions
        all_perms = ChatPermissions(
            can_send_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
        )
        success = 0
        for bot_obj in ALL_BOTS.values():
            try:
                await bot_obj.set_chat_permissions(chat_id=chat.id, permissions=all_perms)
                success += 1
                break
            except Exception as e:
                print(f"[unlock] Failed: {e}")

        if success:
            await update.message.reply_text("🔓 𝘾𝙝𝙖𝙩 𝙪𝙣𝙡𝙤𝙘𝙠𝙚𝙙! 𝙈𝙚𝙢𝙗𝙚𝙧𝙨 𝙘𝙖𝙣 𝙨𝙚𝙣𝙙 𝙢𝙚𝙨𝙨𝙖𝙜𝙚𝙨 𝙖𝙜𝙖𝙞𝙣.")
        else:
            await update.message.reply_text("❌ Failed — make sure at least one bot is admin.")

    async def broadcast_command(self, update, context):
        if not await self.check_owner(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: .broadcast <message>")
            return

        text = " ".join(context.args)
        if not KNOWN_CHATS:
            await update.message.reply_text("No known chats yet. Use any command in a group first.")
            return

        total = len(KNOWN_CHATS) * len(ALL_BOTS)
        sent = 0
        failed = 0
        status_msg = await update.message.reply_text(
            f"📢 𝘽𝙧𝙤𝙖𝙙𝙘𝙖𝙨𝙩𝙞𝙣𝙜 𝙩𝙤 {len(KNOWN_CHATS)} 𝙘𝙝𝙖𝙩(s) 𝙫𝙞𝙖 {len(ALL_BOTS)} 𝙗𝙤𝙩(s)..."
        )

        for chat_id in list(KNOWN_CHATS):
            for bot_obj in ALL_BOTS.values():
                try:
                    await bot_obj.send_message(chat_id=chat_id, text=text)
                    sent += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    failed += 1
                    print(f"[broadcast] Failed to send to {chat_id}: {e}")

        result = (
            f"📢 𝘽𝙧𝙤𝙖𝙙𝙘𝙖𝙨𝙩 𝙘𝙤𝙢𝙥𝙡𝙚𝙩𝙚!\n"
            f"├ ✅ 𝙎𝙚𝙣𝙩: {sent}/{total}\n"
            f"└ ❌ 𝙁𝙖𝙞𝙡𝙚𝙙: {failed}"
        )
        try:
            await status_msg.edit_text(result)
        except Exception:
            await update.message.reply_text(result)

    async def stats_command(self, update, context):
        if not await self.check_owner(update):
            return
        now = time.time()
        uptime_secs = int(now - SYSTEM_START_TIME)

        def fmt(secs):
            h, rem = divmod(secs, 3600)
            m, s = divmod(rem, 60)
            parts = []
            if h: parts.append(f"{h}h")
            if m: parts.append(f"{m}m")
            parts.append(f"{s}s")
            return " ".join(parts)

        total_bots = len(ALL_BOT_IDS)
        msg = (
            f"📊 𝙂𝙡𝙤𝙗𝙖𝙡 𝙎𝙩𝙖𝙩𝙨\n"
            f"├ 🤖 𝘽𝙤𝙩𝙨 𝙍𝙪𝙣𝙣𝙞𝙣𝙜: {total_bots}\n"
            f"├ ⏱️ 𝙐𝙥𝙩𝙞𝙢𝙚: {fmt(uptime_secs)}\n"
            f"├ 💬 𝙈𝙚𝙨𝙨𝙖𝙜𝙚𝙨 𝙎𝙚𝙣𝙩: {GLOBAL_STATS['messages_sent']:,}\n"
            f"├ 🔄 𝙉𝙖𝙢𝙚 𝘾𝙝𝙖𝙣𝙜𝙚𝙨: {GLOBAL_STATS['name_changes']:,}\n"
            f"├ ↩️ 𝙍𝙚𝙥𝙡𝙞𝙚𝙨 𝙎𝙚𝙣𝙩: {GLOBAL_STATS['replies_sent']:,}\n"
            f"└ 📨 𝙁𝙬𝙙 𝙎𝙥𝙖𝙢: {GLOBAL_STATS['fwd_spam_sent']:,}"
        )
        await update.message.reply_text(msg)

    async def leaveall_command(self, update, context):
        if not await self.check_owner(update):
            return
        chat = update.effective_chat
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("This command only works in groups!")
            return

        chat_id = chat.id
        try:
            await update.message.reply_text(f"👋 𝘽𝙮𝙚...")
        except Exception:
            pass

        left = 0
        failed = 0
        for bot_id, bot_obj in list(ALL_BOTS.items()):
            try:
                await bot_obj.leave_chat(chat_id)
                left += 1
                await asyncio.sleep(0.2)
            except Exception as e:
                failed += 1
                print(f"[leaveall] Bot {bot_id} failed to leave {chat_id}: {e}")
        print(f"[leaveall] {left} bot(s) left chat {chat_id}, {failed} failed")



def create_bot_application(token, bot_number, owner_id):
    application = Application.builder().token(token).build()
    bot_instance = BotInstance(bot_number, owner_id)

    # Standard command handlers
    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(CommandHandler("nc", bot_instance.nc_command))
    application.add_handler(CommandHandler("ncemo", bot_instance.nc_emo_command))
    application.add_handler(CommandHandler("ncmoon", bot_instance.ncmoon_command))
    application.add_handler(CommandHandler("ncflag", bot_instance.ncflag_command))
    application.add_handler(CommandHandler("ncbolt", bot_instance.ncbolt_command))
    application.add_handler(CommandHandler("stopnc", bot_instance.stop_nc_command))
    application.add_handler(CommandHandler("stopncmoon", bot_instance.stop_ncmoon_command))
    application.add_handler(CommandHandler("stopncflag", bot_instance.stop_ncflag_command))
    application.add_handler(CommandHandler("stopncbolt", bot_instance.stop_ncbolt_command))
    application.add_handler(CommandHandler("spam", bot_instance.spam_command))
    application.add_handler(CommandHandler("stopspam", bot_instance.stop_spam_command))
    application.add_handler(CommandHandler("rrspam", bot_instance.rrspam_command))
    application.add_handler(CommandHandler("stoprrspam", bot_instance.stop_rrspam_command))
    application.add_handler(CommandHandler("target", bot_instance.target_command))
    application.add_handler(CommandHandler("reply", bot_instance.reply_command))
    application.add_handler(CommandHandler("stopreply", bot_instance.stop_reply_command))
    application.add_handler(CommandHandler("delay", bot_instance.delay_command))
    application.add_handler(CommandHandler("threads", bot_instance.threads_command))
    application.add_handler(CommandHandler("stopall", bot_instance.stop_all_command))
    application.add_handler(CommandHandler("gc", bot_instance.gc_command))
    application.add_handler(CommandHandler("sudo", bot_instance.sudo_command))
    application.add_handler(CommandHandler("upadmin", bot_instance.upadmin_command))
    application.add_handler(CommandHandler("leaveall", bot_instance.leaveall_command))
    application.add_handler(CommandHandler("joinall", bot_instance.joinall_command))
    application.add_handler(CommandHandler("fjoin", bot_instance.fjoin_command))
    application.add_handler(CommandHandler("uptime", bot_instance.uptime_command))
    application.add_handler(CommandHandler("multigc", bot_instance.multigc_command))
    application.add_handler(CommandHandler("stopmultigc", bot_instance.stop_multigc_command))
    application.add_handler(CommandHandler("cheerync", bot_instance.cheerync_command))
    application.add_handler(CommandHandler("stopcheerync", bot_instance.stop_cheerync_command))
    application.add_handler(CommandHandler("fwdspam", bot_instance.fwdspam_command))
    application.add_handler(CommandHandler("stopfwdspam", bot_instance.stopfwdspam_command))
    application.add_handler(CommandHandler("stats", bot_instance.stats_command))
    application.add_handler(CommandHandler("broadcast", bot_instance.broadcast_command))
    application.add_handler(CommandHandler("emojirain", bot_instance.emojirain_command))
    application.add_handler(CommandHandler("stopemojirain", bot_instance.stopemojirain_command))
    application.add_handler(CommandHandler("setdesc", bot_instance.setdesc_command))
    application.add_handler(CommandHandler("stopsetdesc", bot_instance.stopsetdesc_command))
    application.add_handler(CommandHandler("bignc", bot_instance.bignc_command))
    application.add_handler(CommandHandler("stopbignc", bot_instance.stopbignc_command))
    application.add_handler(CommandHandler("fastnc", bot_instance.fastnc_command))
    application.add_handler(CommandHandler("stopfastnc", bot_instance.stopfastnc_command))
    application.add_handler(CommandHandler("lock", bot_instance.lock_command))
    application.add_handler(CommandHandler("unlock", bot_instance.unlock_command))

    # Custom handler for prefix '.'
    async def prefix_handler(update, context):
        if not update.message or not update.message.text:
            return
        text = update.message.text
        if text.startswith('.'):
            parts = text[1:].split()
            if not parts:
                return
            command = parts[0].lower()
            context.args = parts[1:]
            
            cmd_map = {
                "start": bot_instance.start,
                "nc": bot_instance.nc_command,
                "stopnc": bot_instance.stop_nc_command,
                "spam": bot_instance.spam_command,
                "stopspam": bot_instance.stop_spam_command,
                "rrspam": bot_instance.rrspam_command,
                "stoprrspam": bot_instance.stop_rrspam_command,
                "delay": bot_instance.delay_command,
                "threads": bot_instance.threads_command,
                "target": bot_instance.target_command,
                "stopall": bot_instance.stop_all_command,
                "ncmoon": bot_instance.ncmoon_command,
                "stopncmoon": bot_instance.stop_ncmoon_command,
                "ncflag": bot_instance.ncflag_command,
                "stopncflag": bot_instance.stop_ncflag_command,
                "ncbolt": bot_instance.ncbolt_command,
                "stopncbolt": bot_instance.stop_ncbolt_command,
                "ncemo": bot_instance.nc_emo_command,
                "reply": bot_instance.reply_command,
                "stopreply": bot_instance.stop_reply_command,
                "imagespam": bot_instance.imagespam_command,
                "stopimagespam": bot_instance.stop_imagespam_command,
                "gc": bot_instance.gc_command,
                "sudo": bot_instance.sudo_command,
                "refresh": bot_instance.refresh_command,
                "upadmin": bot_instance.upadmin_command,
                "leaveall": bot_instance.leaveall_command,
                "joinall": bot_instance.joinall_command,
                "fjoin": bot_instance.fjoin_command,
                "uptime": bot_instance.uptime_command,
                "fwdspam": bot_instance.fwdspam_command,
                "stopfwdspam": bot_instance.stopfwdspam_command,
                "stats": bot_instance.stats_command,
                "broadcast": bot_instance.broadcast_command,
                "emojirain": bot_instance.emojirain_command,
                "stopemojirain": bot_instance.stopemojirain_command,
                "setdesc": bot_instance.setdesc_command,
                "stopsetdesc": bot_instance.stopsetdesc_command,
                "bignc": bot_instance.bignc_command,
                "stopbignc": bot_instance.stopbignc_command,
                "fastnc": bot_instance.fastnc_command,
                "stopfastnc": bot_instance.stopfastnc_command,
                "lock": bot_instance.lock_command,
                "unlock": bot_instance.unlock_command,
            }
            
            if command in cmd_map:
                await cmd_map[command](update, context)

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), prefix_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, bot_instance.message_collector))

    async def _error_handler(update, context):
        if isinstance(context.error, TelegramConflict):
            print(f"[Bot {bot_instance.bot_number}] Another instance detected — waiting to take over...")
        elif context.error:
            print(f"[Bot {bot_instance.bot_number}] Error: {context.error}")
    application.add_error_handler(_error_handler)

    return application


async def run_bot(token, bot_number, owner_id):
    max_retries = 999
    retry_delay = 15
    conflict_retry_delay = 1
    
    # Load proxies
    proxies = []
    if os.path.exists("proxies.txt"):
        try:
            with open("proxies.txt", "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
        except Exception:
            pass

    for attempt in range(max_retries):
        bot_instance = BotInstance(bot_number, owner_id)
        
        # Assign proxy if available
        proxy_url = None
        if proxies:
            proxy_url = proxies[(bot_number - 1) % len(proxies)]
            bot_instance.proxy = proxy_url

        request = None
        if proxy_url:
            request = HTTPXRequest(proxy_url=proxy_url)

        builder = Application.builder().token(token)
        if request:
            builder.request(request)
        application = builder.build()
        
        # Standard command handlers
        application.add_handler(CommandHandler("start", bot_instance.start))
        application.add_handler(CommandHandler("nc", bot_instance.nc_command))
        application.add_handler(CommandHandler("ncemo", bot_instance.nc_emo_command))
        application.add_handler(CommandHandler("ncmoon", bot_instance.ncmoon_command))
        application.add_handler(CommandHandler("ncflag", bot_instance.ncflag_command))
        application.add_handler(CommandHandler("ncbolt", bot_instance.ncbolt_command))
        application.add_handler(CommandHandler("flowernc", bot_instance.flower_nc_command))
        application.add_handler(CommandHandler("annunc", bot_instance.annunc_command))
        application.add_handler(CommandHandler("nccurly", bot_instance.nccurly_command))
        application.add_handler(CommandHandler("stopnc", bot_instance.stop_nc_command))
        application.add_handler(CommandHandler("stopncmoon", bot_instance.stop_ncmoon_command))
        application.add_handler(CommandHandler("stopncflag", bot_instance.stop_ncflag_command))
        application.add_handler(CommandHandler("stopncbolt", bot_instance.stop_ncbolt_command))
        application.add_handler(CommandHandler("stopnccurly", bot_instance.stop_nccurly_command))
        application.add_handler(CommandHandler("spam", bot_instance.spam_command))
        application.add_handler(CommandHandler("stopspam", bot_instance.stop_spam_command))
        application.add_handler(CommandHandler("rrspam", bot_instance.rrspam_command))
        application.add_handler(CommandHandler("stoprrspam", bot_instance.stop_rrspam_command))
        application.add_handler(CommandHandler("target", bot_instance.target_command))
        application.add_handler(CommandHandler("reply", bot_instance.reply_command))
        application.add_handler(CommandHandler("stopreply", bot_instance.stop_reply_command))
        application.add_handler(CommandHandler("delay", bot_instance.delay_command))
        application.add_handler(CommandHandler("threads", bot_instance.threads_command))
        application.add_handler(CommandHandler("stopall", bot_instance.stop_all_command))
        application.add_handler(CommandHandler("gc", bot_instance.gc_command))
        application.add_handler(CommandHandler("setgc", bot_instance.set_gc_command))
        application.add_handler(CommandHandler("ping", bot_instance.ping_command))
        application.add_handler(CommandHandler("uptime", bot_instance.uptime_command))
        application.add_handler(CommandHandler("sudo", bot_instance.sudo_command))
        application.add_handler(CommandHandler("proxy", bot_instance.proxy_command))
        application.add_handler(CommandHandler("refresh", bot_instance.refresh_command))
        application.add_handler(CommandHandler("upadmin", bot_instance.upadmin_command))
        application.add_handler(CommandHandler("leaveall", bot_instance.leaveall_command))
        application.add_handler(CommandHandler("joinall", bot_instance.joinall_command))
        application.add_handler(CommandHandler("fjoin", bot_instance.fjoin_command))
        application.add_handler(CommandHandler("multigc", bot_instance.multigc_command))
        application.add_handler(CommandHandler("stopmultigc", bot_instance.stop_multigc_command))
        application.add_handler(CommandHandler("cheerync", bot_instance.cheerync_command))
        application.add_handler(CommandHandler("stopcheerync", bot_instance.stop_cheerync_command))
        application.add_handler(CommandHandler("fwdspam", bot_instance.fwdspam_command))
        application.add_handler(CommandHandler("stopfwdspam", bot_instance.stopfwdspam_command))
        application.add_handler(CommandHandler("stats", bot_instance.stats_command))
        application.add_handler(CommandHandler("broadcast", bot_instance.broadcast_command))
        application.add_handler(CommandHandler("emojirain", bot_instance.emojirain_command))
        application.add_handler(CommandHandler("stopemojirain", bot_instance.stopemojirain_command))
        application.add_handler(CommandHandler("setdesc", bot_instance.setdesc_command))
        application.add_handler(CommandHandler("stopsetdesc", bot_instance.stopsetdesc_command))
        application.add_handler(CommandHandler("bignc", bot_instance.bignc_command))
        application.add_handler(CommandHandler("stopbignc", bot_instance.stopbignc_command))
        application.add_handler(CommandHandler("fastnc", bot_instance.fastnc_command))
        application.add_handler(CommandHandler("stopfastnc", bot_instance.stopfastnc_command))
        application.add_handler(CommandHandler("lock", bot_instance.lock_command))
        application.add_handler(CommandHandler("unlock", bot_instance.unlock_command))

        # Custom handler for prefix '.'
        async def prefix_handler(update, context):
            if not update.message or not update.message.text:
                return
            text = update.message.text
            if text.startswith('.'):
                parts = text[1:].split()
                if not parts:
                    return
                command = parts[0].lower()
                context.args = parts[1:]
                
                cmd_map = {
                    "start": bot_instance.start,
                    "nc": bot_instance.nc_command,
                    "stopnc": bot_instance.stop_nc_command,
                    "spam": bot_instance.spam_command,
                    "stopspam": bot_instance.stop_spam_command,
                    "rrspam": bot_instance.rrspam_command,
                    "stoprrspam": bot_instance.stop_rrspam_command,
                    "delay": bot_instance.delay_command,
                    "threads": bot_instance.threads_command,
                    "target": bot_instance.target_command,
                    "stopall": bot_instance.stop_all_command,
                    "ncmoon": bot_instance.ncmoon_command,
                    "stopncmoon": bot_instance.stop_ncmoon_command,
                    "ncflag": bot_instance.ncflag_command,
                    "stopncflag": bot_instance.stop_ncflag_command,
                    "ncbolt": bot_instance.ncbolt_command,
                    "stopncbolt": bot_instance.stop_ncbolt_command,
                    "nccurly": bot_instance.nccurly_command,
                    "stopnccurly": bot_instance.stop_nccurly_command,
                                "ncemo": bot_instance.nc_emo_command,
                    "ownrp": bot_instance.ownrp_command,
                    "rr": bot_instance.rr_command,
                    "stoprr": bot_instance.stoprr_command,
                    "timenc": bot_instance.time_nc_command,
                    "stoptimenc": bot_instance.stop_time_nc,
                    "react": bot_instance.react_command,
                    "multispam": bot_instance.multispam_command,
                    "autoname": bot_instance.auto_name_command,
                    "stopautoname": bot_instance.stop_auto_name,
                    "reply": bot_instance.reply_command,
                    "stopreply": bot_instance.stop_reply_command,
                    "imagespam": bot_instance.imagespam_command,
                    "stopimagespam": bot_instance.stop_imagespam_command,
                    "ping": bot_instance.ping_command,
                    "uptime": bot_instance.uptime_command,
                    "gc": bot_instance.gc_command,
                    "setgc": bot_instance.set_gc_command,
                    "sudo": bot_instance.sudo_command,
                    "proxy": bot_instance.proxy_command,
                    "join": bot_instance.join_command,
                    "refresh": bot_instance.refresh_command,
                    "upadmin": bot_instance.upadmin_command,
                    "leaveall": bot_instance.leaveall_command,
                    "joinall": bot_instance.joinall_command,
                    "fjoin": bot_instance.fjoin_command,
                    "multigc": bot_instance.multigc_command,
                    "stopmultigc": bot_instance.stop_multigc_command,
                    "cheerync": bot_instance.cheerync_command,
                    "stopcheerync": bot_instance.stop_cheerync_command,
                    "fwdspam": bot_instance.fwdspam_command,
                    "stopfwdspam": bot_instance.stopfwdspam_command,
                    "stats": bot_instance.stats_command,
                    "broadcast": bot_instance.broadcast_command,
                    "emojirain": bot_instance.emojirain_command,
                    "stopemojirain": bot_instance.stopemojirain_command,
                    "setdesc": bot_instance.setdesc_command,
                    "stopsetdesc": bot_instance.stopsetdesc_command,
                    "bignc": bot_instance.bignc_command,
                    "stopbignc": bot_instance.stopbignc_command,
                    "fastnc": bot_instance.fastnc_command,
                    "stopfastnc": bot_instance.stopfastnc_command,
                    "lock": bot_instance.lock_command,
                    "unlock": bot_instance.unlock_command,
                }
                
                if command in cmd_map:
                    await cmd_map[command](update, context)
                elif command == "flowernc":
                    await bot_instance.flower_nc_command(update, context)
                elif command == "annunc":
                    await bot_instance.annunc_command(update, context)
            else:
                await bot_instance.message_collector(update, context)

        application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), prefix_handler))

        async def _error_handler(update, context):
            if isinstance(context.error, TelegramConflict):
                print(f"[Bot {bot_number}] Another instance detected — waiting to take over...")
            elif context.error:
                print(f"[Bot {bot_number}] Error: {context.error}")
        application.add_error_handler(_error_handler)

        try:
            await application.initialize()
            await application.start()
            try:
                me = await application.bot.get_me()
                ALL_BOT_IDS.add(me.id)
                ALL_BOTS[me.id] = application.bot
                print(f"Bot {bot_number} registered ID {me.id} (@{me.username})")
            except Exception as e:
                print(f"Bot {bot_number} could not register ID: {e}")
            if application.updater:
                # Removed large stagger per user request for 1s startup
                await asyncio.sleep(0.1)
                await application.updater.start_polling(drop_pending_updates=True)
            print(f"Bot {bot_number} started successfully!")
            BOT_START_TIMES[bot_number] = time.time()

            while True:
                await asyncio.sleep(3600)

        except Exception as e:
            error_str = str(e).lower()
            if "conflict" in error_str:
                print(f"Bot {bot_number} conflict — reclaiming in {conflict_retry_delay}s...")
                try:
                    if application.updater:
                        await application.updater.stop()
                    await application.stop()
                    await application.shutdown()
                except Exception:
                    pass
                await asyncio.sleep(conflict_retry_delay)
                continue
            else:
                print(f"Bot {bot_number} error: {e}")
                break
        finally:
            try:
                if application.updater:
                    await application.updater.stop()
                await application.stop()
                await application.shutdown()
            except Exception:
                pass
        break
    else:
        print(f"Bot {bot_number} failed after {max_retries} attempts - token may be used elsewhere")

async def keepalive_server():
    async def handle(request):
        return web.Response(text="OK")
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/ping", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("BOT_PORT", 3000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Keepalive server running on port {port}")

async def main():
    print(f"Starting {len(BOT_TOKENS)} bots for owner ID: {OWNER_ID}")
    print("All actions (name change, spam, reply) run in LOOPS!")

    asyncio.create_task(keepalive_server())

    tasks = []
    for i, token in enumerate(BOT_TOKENS, 1):
        task = asyncio.create_task(run_bot(token, i, OWNER_ID))
        tasks.append(task)
        await asyncio.sleep(0.05)

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\nShutting down all bots...")


if __name__ == "__main__":
    asyncio.run(main())