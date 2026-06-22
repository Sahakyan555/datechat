import logging
import os
import asyncio
from aiohttp import web
from datetime import date
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)

# ── Կոնֆիգ ──────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ["BOT_TOKEN"]
PROVIDER_TOKEN = ""
ADMIN_ID       =  661440932 

DAILY_FREE     = 3   # անվճար որոնումներ ամեն օր
REFERRAL_BONUS = 5   # բոնուս հաջողված referral-ի դեպքում

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

USERS_DB:  dict       = {}
CHATS:     dict       = {}
REQUESTS:  dict       = {}
REFERRALS: dict       = {}
BOT_USERNAME: str | None = None

LANG_MAP = {
    "🇦🇲": "hy", "🇷🇺": "ru", "🇺🇸": "en", "🇫🇷": "fr",
    "🇹🇷": "tr", "🇸🇦": "ar", "🇮🇷": "fa", "🇩🇪": "de",
    "🇮🇳": "hi", "🇬🇪": "ka", "🇦🇷": "es", "🇯🇵": "ja",
    "🇨🇳": "zh", "🇮🇹": "it", "🇳🇱": "nl",
}
LANG_NAMES = {
    "🇦🇲": "Հայերեն", "🇷🇺": "Русский",  "🇺🇸": "English",
    "🇫🇷": "Français",   "🇹🇷": "Türkçe",   "🇸🇦": "العربية",
    "🇮🇷": "فارسی",      "🇩🇪": "Deutsch",   "🇮🇳": "हिन्दी",
    "🇬🇪": "ქართული",    "🇦🇷": "Español",   "🇯🇵": "日本語",
    "🇨🇳": "中文",        "🇮🇹": "Italiano",  "🇳🇱": "Nederlands",
}
REG_STEPS = 7


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def progress_bar(step: int) -> str:
    filled = "▓" * step
    empty  = "░" * (REG_STEPS - step)
    pct    = int(step / REG_STEPS * 100)
    return f"<code>{filled}{empty}</code>  <b>{pct}%</b>"


def step_ack(step: int, icon: str, choice: str) -> str:
    acks = {
        1: f"{icon} <b>{choice}</b> — հիանալի ընտրություն! 🔥\n\n",
        2: f"🎂 <b>{choice}</b> — ֆիքսված ✅\n\n",
        3: f"📏 <b>{choice} սմ</b> — կատարյալ! 💪\n\n",
        4: f"{icon} Մազերի գույնը <b>ֆիքսված</b> ✨\n\n",
        5: f"{icon} Աչքերի գույնը <b>ֆիքսված</b> 👁✨\n\n",
        6: f"{icon} Երկիրը <b>ֆիքսված</b> 🌍\n\n",
    }
    return acks.get(step, "✅\n\n")


def gender_icon(text: str) -> str:
    t = (text or "").lower()
    if any(x in t for x in ["male", "man", "տղա", "мужч", "homme"]):
        return "👨"
    if any(x in t for x in ["female", "woman", "աղջիկ", "женщ", "femme"]):
        return "👩"
    return "🌈"


async def typing_action(chat_id, delay: float = 0.6):
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(delay)


async def photo_action(chat_id, delay: float = 0.8):
    await bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)
    await asyncio.sleep(delay)


def init_user(uid: int, tg_user=None):
    if uid not in USERS_DB:
        USERS_DB[uid] = {
            "free_chats": DAILY_FREE,
            "edit_count": 0,
            "blocks":     [],
            "liked_by":   [],
            "ref_count":  0,
            "ref_bonus":  0,
            "last_daily": str(date.today()),
            "tg_info":    {},
        }
    for k, v in [("ref_count", 0), ("ref_bonus", 0),
                 ("last_daily", str(date.today())), ("tg_info", {})]:
        USERS_DB[uid].setdefault(k, v)
    if tg_user:
        USERS_DB[uid]["tg_info"] = {
            "id":         uid,
            "first_name": tg_user.first_name or "",
            "last_name":  tg_user.last_name  or "",
            "username":   tg_user.username   or "",
            "lang_code":  tg_user.language_code or "",
        }


def daily_refill(uid: int) -> int:
    today = str(date.today())
    if USERS_DB[uid].get("last_daily") != today:
        USERS_DB[uid]["free_chats"]  += DAILY_FREE
        USERS_DB[uid]["last_daily"]  = today
        return DAILY_FREE
    return 0


def build_profile_card(viewer_uid: int, data: dict) -> str:
    return get_txt(viewer_uid, "profile_card").format(
        gi=gender_icon(data.get("gender", "")),
        g=data.get("gender", "—"),
        a=data.get("age", "—"),
        h=data.get("height", "—"),
        hr=data.get("hair", "—"),
        e=data.get("eyes", "—"),
        f=data.get("flag", "—"),
    )


# ════════════════════════════════════════════════════════════════════════════
#  TEXTS
# ════════════════════════════════════════════════════════════════════════════
TEXTS = {

    # ─────────────────────────── ՀԱՅERЕН ───────────────────────────────────
    "hy": {
        "welcome_lang": (
            "💘 <b>DATE CHAT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌍 Ընտրեք ձեր լեզուն\n"
            "<i>Choose / Выберите</i>"
        ),
        "welcome": (
            "✨ <b>Բարի գալուստ DATE CHAT!</b> ✨\n\n"
            "💘 Ծանոթացեք <b>անանուն</b> կերպով\n"
            "🔒 Ձեր Telegram ID-ն երբեք չի բացահայտվի\n"
            "💬 Շփվեք, ընկերացեք, հայտնաբերեք!\n"
            f"🎁 Ամեն օր <b>{DAILY_FREE}</b> անվճար որոնում\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⬇️ Սեղմեք կոճակը՝ սկսելու"
        ),
        "register": "🚀  Ստեղծել իմ պրոֆիլը",
        "step_gender": "👤 <b>Քայլ 1 — Ձեր սեռը</b>\n{bar}\n\nԵս եմ ↓",
        "male":   "👨  Տղա",
        "female": "👩  Աղջիկ",
        "other":  "🌈  Այլ",
        "step_age":    "{ack}🎂 <b>Քայլ 2 — Տարիքային խումբ</b>\n{bar}\n\nԸնտրեք ↓",
        "step_height": "{ack}📏 <b>Քայլ 3 — Հասակ</b>\n{bar}\n\nԳրեք սմ-ով  <i>(օր. <code>173</code>)</i>",
        "step_hair":   "{ack}💇 <b>Քայլ 4 — Մազերի գույն</b>\n{bar}\n\nԸնտրեք ↓",
        "step_eyes":   "{ack}👁 <b>Քայլ 5 — Աչքերի գույն</b>\n{bar}\n\nԸնտրեք ↓",
        "step_flag":   "{ack}🌍 <b>Քայλ 6 — Ձեր երկիրը</b>\n{bar}\n\nՈւղարկեք <b>դրոշ emoji</b>  <i>(🇦🇲 🇺🇸 🇷🇺)</i>",
        "step_photo": (
            "{ack}📸 <b>Քայլ 7 — Ձեր լավագույն նկարը</b>\n{bar}\n\n"
            "🔒 <i>Ցуycаracvum e <b>ananun</b> — Ձեր անունը թաքնված է մնալու</i>\n\n"
            "⬇️  ուղարկեք նկար"
        ),
        "profile_card": (
            "👤 <b>Անանուն Պրոֆիլ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "{gi}  <b>Սեռ</b>      ›  {g}\n"
            "🎂  <b>Տարիք</b>    ›  {a}\n"
            "📏  <b>Հասակ</b>    ›  {h} сm\n"
            "💇  <b>Մազեր</b>    ›  {hr}\n"
            "👁  <b>Աչքեր</b>   ›  {e}\n"
            "🌍  <b>երկիր</b>    ›  {f}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        "profile_ready": (
            "🎊 <b>Profily PATRASТ!</b> 🎊\n\n"
            "✨ Արդեն կարող եք փնտրել ընկեր\n"
            f"⭐ <i>Аmsor aves <b>{DAILY_FREE}</b> անվճար որոնում!</i>"
        ),
        "find_friend":  "🔍  Փնտրել ընկեր",
        "edit_profile": "✏️  Փոխել պրոֆիլը",
        "invite_btn":   f"🎁  հրավիրել ընկեր (+{REFERRAL_BONUS} ⭐)",
        "blocks":       "🚫  Բլոկ ցուցակ",
        "back_menu":    "🏠  Գլխավոր ",
        "searching":    "🔍 <b>Փնտրում ենք...</b>\n<i>Փնտրում ենք լավագույն պրոֆիլը ձեր համար </i> 💫",
        "found_profile":"💫 <b>նոր պրոֆիլը գտնվեց!</b>",
        "like":         "❤️  հավանել",
        "block_btn":    "🚫  մերժել",
        "next_btn":     "⏭  հաջորդ պրոֆիլը",
        "no_users": (
            "😔 <b>դեռ ոչ ոք չկա...</b>\n\n"
            "💡 <b>Tips</b>\n"
            f"• հրավիրել ընկերներ 🎁  (+{REFERRAL_BONUS} knoum!)\n"
            "• պորձել ավելի ուշ 🕐\n"
            "• ամենուր մարդիկ են գրանցվում! 🌟"
        ),
        "req_sent":     "💌 <b>հարցումն ուղարկվել է!</b>\n\n⏳ <i>սպասել... կարող եք հենց հիմա տեսնել ✨</i>",
        "new_req":      "💘 <b>ձեզ հավանեցին!</b>\n\n👇 ընդունեք ծանոթոըթյան հրավերը",
        "accept":       "✅  ընդունել",
        "decline":      "❌  մերժել",
        "match_screen": (
            "💥 <b>MATCH!</b> 💥\n\n"
            "❤️‍🔥 երկուսդ հավանեցիք միմյանց!\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔐 ձեր ինքնությունը <b>ամբողջովին թաքնվաց է</b>\n"
            "💬 ազատ խոսեք — text, nukar, sticker 📸\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⬇️ ավարտելու համար սեղմել ստորև"
        ),
        "chat_end_btn": "🔚  ավարտել չատը",
        "chat_end": (
            "👋 <b>չատը ավարտվեց</b>\n\n"
            "💘 <i>հուսով ենք հաճելի ծանոթություն էր!</i>\n"
            "🔍 <i>ցանկանում եք գտնել նոր ընկեր?</i>"
        ),
        "partner_left": "⚠️ <b>զրուցակիցը անջատել է</b>\n\n🔍 ցանկանում եք գտնել նոր ընկեր?",
        "unblock":           "🔓  ապաբլոկավորել",
        "blocked_ok":        "🚫 բլոկվեց",
        "unblocked_ok":      "🔓 ապաբլոկվեց",
        "blocks_empty":      "✅ <b>բլոկ ցուցակը դատարկ է</b>\n\n<i>դուք բլոկ չեք արել</i>",
        "blocked_user_row":  "🔒  անանուն #{n}",
        "pay_stars_3": (
            "⭐ <b>անվճար որոնումների լիմիտը սպառված է</b>\n\n"
            "💫 հաջորդ որոնման համար` <b>5 ⭐ Stars</b>\n"
            "🔒 <i>ապահով վճարում Telegram-ի միջոցով</i>"
        ),
        "pay_stars_edit": (
            "✏️ <b>պրֆիլը արդեն փոխվել է</b>\n\n"
            "💫 կրկին փոխելու համար` <b>100 ⭐ Stars</b>"
        ),
        "pay_success_connect": "✅ <b>վճարումն ընդունված է!</b>\n\n❤️ հարցումն ուղարկվել է...",
        "pay_success_edit":    "✅ <b>վճարումն ընդունված է!</b>\n\n✏️ փողեք ձեր պրոֆիլը",
        "invite_text": (
            f"🎁 <b>REFERRAL — հրավիրիր, վաստակիր!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 հրավիրիր ընկեր ➜ <u>երկուստ</u> կստանաք <b>+{REFERRAL_BONUS} ⭐ անվճար որոնում</b>\n\n"
            "📤 հրավիրիր քո հղումով ↓\n\n"
            "<code>{link}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 հռավիրված›  <code>{count}</code> հոգի\n"
            "⭐ ստացված բոնուս ›  <code>{bonus}</code> որոնում\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        "ref_bonus_inviter": f"🎉 <b>ընկերդ գրանցվեց!</b>\n\n⭐ +{REFERRAL_BONUS} անվճար որոնում — մնացել է <b>{{n}}</b>",
        "ref_bonus_invited": f"🎁 <b>հրավերի ,միջոցով վաստակիր բոնուս!</b>\n\n⭐ +{REFERRAL_BONUS} անվճար որոնում — մնացել է <b>{{n}}</b>",
        "share_btn":   "📤  ուղարկել ընկերներին",
        "daily_refill": f"🌅 <b>բարի լույս!</b>\n\n⭐ +{DAILY_FREE} անվճար որոնումը ավելացվեց —  մնացել է <b>{{n}}</b>",
    },

    # ─────────────────────────── ENGLISH ───────────────────────────────────
    "en": {
        "welcome_lang": (
            "💘 <b>DATE CHAT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌍 Choose your language\n"
            "<i>Ընտрек / Выберите</i>"
        ),
        "welcome": (
            "✨ <b>Welcome to DATE CHAT!</b> ✨\n\n"
            "💘 Meet people <b>anonymously</b>\n"
            "🔒 Your identity is never revealed\n"
            "💬 Chat, connect, make friends!\n"
            f"🎁 Get <b>{DAILY_FREE}</b> free searches every day\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⬇️ Tap the button to begin"
        ),
        "register": "🚀  Create my profile",
        "step_gender": "👤 <b>Step 1 — Your gender</b>\n{bar}\n\nI am ↓",
        "male":   "👨  Male",
        "female": "👩  Female",
        "other":  "🌈  Other",
        "step_age":    "{ack}🎂 <b>Step 2 — Age group</b>\n{bar}\n\nChoose ↓",
        "step_height": "{ack}📏 <b>Step 3 — Height</b>\n{bar}\n\nType in cm  <i>(e.g. <code>173</code>)</i>",
        "step_hair":   "{ack}💇 <b>Step 4 — Hair color</b>\n{bar}\n\nChoose ↓",
        "step_eyes":   "{ack}👁 <b>Step 5 — Eye color</b>\n{bar}\n\nChoose ↓",
        "step_flag":   "{ack}🌍 <b>Step 6 — Your country</b>\n{bar}\n\nSend a <b>flag emoji</b>  <i>(e.g. 🇺🇸 🇬🇧)</i>",
        "step_photo": (
            "{ack}📸 <b>Step 7 — Your best photo</b>\n{bar}\n\n"
            "🔒 <i>Shown <b>anonymously</b> — your name stays hidden</i>\n\n"
            "⬇️ Send a photo"
        ),
        "profile_card": (
            "👤 <b>ANONYMOUS PROFILE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "{gi}  <b>Gender</b>   ›  {g}\n"
            "🎂  <b>Age</b>      ›  {a}\n"
            "📏  <b>Height</b>   ›  {h} cm\n"
            "💇  <b>Hair</b>     ›  {hr}\n"
            "👁  <b>Eyes</b>     ›  {e}\n"
            "🌍  <b>Country</b>  ›  {f}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        "profile_ready": (
            "🎊 <b>Profile READY!</b> 🎊\n\n"
            "✨ Start finding friends now\n"
            f"⭐ <i>You get <b>{DAILY_FREE}</b> free searches every day!</i>"
        ),
        "find_friend":  "🔍  Find a Friend",
        "edit_profile": "✏️  Edit Profile",
        "invite_btn":   f"🎁  Invite Friend (+{REFERRAL_BONUS} ⭐)",
        "blocks":       "🚫  Blocklist",
        "back_menu":    "🏠  Home",
        "searching":    "🔍 <b>Searching...</b>\n<i>Finding the best profile for you</i> 💫",
        "found_profile":"💫 <b>New profile found!</b>",
        "like":         "❤️  Like",
        "block_btn":    "🚫  Block",
        "next_btn":     "⏭  Next",
        "no_users": (
            "😔 <b>Nobody here right now...</b>\n\n"
            "💡 <b>Tips</b>\n"
            f"• Invite friends 🎁  (+{REFERRAL_BONUS} searches each!)\n"
            "• Try again later 🕐\n"
            "• New people join every day! 🌟"
        ),
        "req_sent":     "💌 <b>Request sent!</b>\n\n⏳ <i>Waiting... they might see it any moment ✨</i>",
        "new_req":      "💘 <b>Someone liked you!</b>\n\n👇 Accept or decline",
        "accept":       "✅  Accept",
        "decline":      "❌  Decline",
        "match_screen": (
            "💥 <b>IT'S A MATCH!</b> 💥\n\n"
            "❤️‍🔥 You both liked each other!\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔐 Your identity is <b>fully hidden</b>\n"
            "💬 Chat freely — text, photos, stickers 📸\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⬇️ Tap below to end"
        ),
        "chat_end_btn": "🔚  End Chat",
        "chat_end": (
            "👋 <b>Chat ended</b>\n\n"
            "💘 <i>Hope it was a great connection!</i>\n"
            "🔍 <i>Want to find someone new?</i>"
        ),
        "partner_left": "⚠️ <b>Partner disconnected</b>\n\n🔍 Want to find someone new?",
        "unblock":           "🔓  Unblock",
        "blocked_ok":        "🚫 Blocked",
        "unblocked_ok":      "🔓 Unblocked",
        "blocks_empty":      "✅ <b>Blocklist is empty</b>\n\n<i>You haven't blocked anyone</i>",
        "blocked_user_row":  "🔒  Anonymous #{n}",
        "pay_stars_3": (
            "⭐ <b>Free searches used up</b>\n\n"
            "💫 Just <b>5 ⭐ Stars</b> to connect next\n"
            "🔒 <i>Secure payment via Telegram</i>"
        ),
        "pay_stars_edit": (
            "✏️ <b>Profile already edited once</b>\n\n"
            "💫 <b>100 ⭐ Stars</b> to edit again"
        ),
        "pay_success_connect": "✅ <b>Payment accepted!</b>\n\n❤️ Sending your request...",
        "pay_success_edit":    "✅ <b>Payment accepted!</b>\n\n✏️ Edit your profile now",
        "invite_text": (
            f"🎁 <b>REFERRAL — Invite & Earn!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Invite a friend ➜ <u>both</u> get <b>+{REFERRAL_BONUS} ⭐ free searches</b>\n\n"
            "📤 Your personal link ↓\n\n"
            "<code>{link}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 Invited  ›  <code>{count}</code> people\n"
            "⭐ Bonus earned  ›  <code>{bonus}</code> searches\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        "ref_bonus_inviter": f"🎉 <b>Your friend joined!</b>\n\n⭐ +{REFERRAL_BONUS} free searches — you now have <b>{{n}}</b>",
        "ref_bonus_invited": f"🎁 <b>Bonus for joining via invite!</b>\n\n⭐ +{REFERRAL_BONUS} free searches — you now have <b>{{n}}</b>",
        "share_btn":   "📤  Share with friends",
        "daily_refill": f"🌅 <b>Good morning!</b>\n\n⭐ +{DAILY_FREE} free searches added — you now have <b>{{n}}</b>",
    },

    # ─────────────────────────── RUSSIAN ───────────────────────────────────
    "ru": {
        "welcome_lang": (
            "💘 <b>DATE CHAT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌍 Выберите язык\n"
            "<i>Choose / Ընтрек</i>"
        ),
        "welcome": (
            "✨ <b>Добро пожаловать в DATE CHAT!</b> ✨\n\n"
            "💘 Знакомьтесь <b>анонимно</b>\n"
            "🔒 Ваша личность никогда не раскрывается\n"
            "💬 Общайтесь, дружите, открывайте!\n"
            f"🎁 Каждый день <b>{DAILY_FREE}</b> бесплатных поиска\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⬇️ Нажмите кнопку, чтобы начать"
        ),
        "register": "🚀  Создать профиль",
        "step_gender": "👤 <b>Шаг 1 — Пол</b>\n{bar}\n\nЯ ↓",
        "male":   "👨  Мужчина",
        "female": "👩  Женщина",
        "other":  "🌈  Другое",
        "step_age":    "{ack}🎂 <b>Шаг 2 — Возраст</b>\n{bar}\n\nВыберите ↓",
        "step_height": "{ack}📏 <b>Шаг 3 — Рост</b>\n{bar}\n\nВведите в см  <i>(напр. <code>173</code>)</i>",
        "step_hair":   "{ack}💇 <b>Шаг 4 — Цвет волос</b>\n{bar}\n\nВыберите ↓",
        "step_eyes":   "{ack}👁 <b>Шаг 5 — Цвет глаз</b>\n{bar}\n\nВыберите ↓",
        "step_flag":   "{ack}🌍 <b>Шаг 6 — Страна</b>\n{bar}\n\nОтправьте <b>флаг-эмодзи</b>  <i>(🇷🇺 🇺🇦)</i>",
        "step_photo": (
            "{ack}📸 <b>Шаг 7 — Лучшее фото</b>\n{bar}\n\n"
            "🔒 <i>Отображается <b>анонимно</b></i>\n\n"
            "⬇️ Отправьте фото"
        ),
        "profile_card": (
            "👤 <b>АНОНИМНЫЙ ПРОФИЛЬ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "{gi}  <b>Пол</b>      ›  {g}\n"
            "🎂  <b>Возраст</b>  ›  {a}\n"
            "📏  <b>Рост</b>     ›  {h} см\n"
            "💇  <b>Волосы</b>   ›  {hr}\n"
            "👁  <b>Глаза</b>    ›  {e}\n"
            "🌍  <b>Страна</b>   ›  {f}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        "profile_ready": (
            "🎊 <b>Профиль ГОТОВ!</b> 🎊\n\n"
            "✨ Начинайте искать друзей\n"
            f"⭐ <i>Каждый день <b>{DAILY_FREE}</b> бесплатных поиска!</i>"
        ),
        "find_friend":  "🔍  Найти друга",
        "edit_profile": "✏️  Изменить профиль",
        "invite_btn":   f"🎁  Пригласить (+{REFERRAL_BONUS} ⭐)",
        "blocks":       "🚫  Чёрный список",
        "back_menu":    "🏠  Главная",
        "searching":    "🔍 <b>Ищем...</b>\n<i>Подбираем лучший профиль для вас</i> 💫",
        "found_profile":"💫 <b>Найден новый профиль!</b>",
        "like":         "❤️  Лайк",
        "block_btn":    "🚫  Блок",
        "next_btn":     "⏭  Следующий",
        "no_users": (
            "😔 <b>Пока никого нет...</b>\n\n"
            "💡 <b>Советы</b>\n"
            f"• Пригласи друзей 🎁  (+{REFERRAL_BONUS} поиска!)\n"
            "• Попробуй позже 🕐\n"
            "• Каждый день приходят новые! 🌟"
        ),
        "req_sent":     "💌 <b>Запрос отправлен!</b>\n\n⏳ <i>Ждём... они могут увидеть прямо сейчас ✨</i>",
        "new_req":      "💘 <b>Вы понравились!</b>\n\n👇 Принять или отклонить",
        "accept":       "✅  Принять",
        "decline":      "❌  Отклонить",
        "match_screen": (
            "💥 <b>MATCH!</b> 💥\n\n"
            "❤️‍🔥 Вы оба понравились друг другу!\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔐 Личность <b>полностью скрыта</b>\n"
            "💬 Общайтесь — текст, фото, стикеры 📸\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⬇️ Нажмите ниже, чтобы завершить"
        ),
        "chat_end_btn": "🔚  Завершить чат",
        "chat_end": (
            "👋 <b>Чат завершён</b>\n\n"
            "💘 <i>Надеемся, знакомство было приятным!</i>\n"
            "🔍 <i>Хотите найти нового друга?</i>"
        ),
        "partner_left": "⚠️ <b>Собеседник отключился</b>\n\n🔍 Хотите найти кого-то нового?",
        "unblock":           "🔓  Разблокировать",
        "blocked_ok":        "🚫 Заблокирован",
        "unblocked_ok":      "🔓 Разблокирован",
        "blocks_empty":      "✅ <b>Чёрный список пуст</b>\n\n<i>Никого не заблокировали</i>",
        "blocked_user_row":  "🔒  Аноним #{n}",
        "pay_stars_3": (
            "⭐ <b>Бесплатные поиски исчерпаны</b>\n\n"
            "💫 Всего <b>5 ⭐ Stars</b> для следующего\n"
            "🔒 <i>Безопасно через Telegram</i>"
        ),
        "pay_stars_edit": "✏️ <b>Профиль уже редактировался</b>\n\n💫 <b>100 ⭐ Stars</b> для повтора",
        "pay_success_connect": "✅ <b>Оплата принята!</b>\n\n❤️ Отправляем запрос...",
        "pay_success_edit":    "✅ <b>Оплата принята!</b>\n\n✏️ Редактируйте профиль",
        "invite_text": (
            f"🎁 <b>REFERRAL — Приглашай и зарабатывай!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Пригласи друга ➜ <u>оба</u> получат <b>+{REFERRAL_BONUS} ⭐ бесплатных поиска</b>\n\n"
            "📤 Ваша личная ссылка ↓\n\n"
            "<code>{link}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 Приглашено  ›  <code>{count}</code> чел.\n"
            "⭐ Бонус  ›  <code>{bonus}</code> поиска\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        "ref_bonus_inviter": f"🎉 <b>Ваш друг зарегистрировался!</b>\n\n⭐ +{REFERRAL_BONUS} поиска — теперь у вас <b>{{n}}</b>",
        "ref_bonus_invited": f"🎁 <b>Бонус за приглашение!</b>\n\n⭐ +{REFERRAL_BONUS} поиска — теперь у вас <b>{{n}}</b>",
        "share_btn":   "📤  Поделиться",
        "daily_refill": f"🌅 <b>Доброе утро!</b>\n\n⭐ +{DAILY_FREE} поиска добавлены — теперь у вас <b>{{n}}</b>",
    },

    # ─────────────────────────── FRENCH ────────────────────────────────────
    "fr": {
        "welcome_lang": "💘 <b>DATE CHAT</b>\n━━━━━━━━━━━━━━━━━━━━\n🌍 Choisissez votre langue",
        "welcome": (
            "✨ <b>Bienvenue sur DATE CHAT!</b> ✨\n\n"
            "💘 Rencontrez des gens <b>anonymement</b>\n"
            "🔒 Identité cachée\n"
            "💬 Discutez, connectez, faites des amis!\n"
            f"🎁 <b>{DAILY_FREE}</b> recherches gratuites chaque jour\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n⬇️ Appuyez pour commencer"
        ),
        "register": "🚀  Créer mon profil",
        "step_gender": "👤 <b>Étape 1 — Genre</b>\n{bar}\n\nJe suis ↓",
        "male": "👨  Homme", "female": "👩  Femme", "other": "🌈  Autre",
        "step_age":    "{ack}🎂 <b>Étape 2 — Âge</b>\n{bar}\n\nChoisissez ↓",
        "step_height": "{ack}📏 <b>Étape 3 — Taille</b>\n{bar}\n\nEn cm <i>(ex: <code>173</code>)</i>",
        "step_hair":   "{ack}💇 <b>Étape 4 — Cheveux</b>\n{bar}\n\nChoisissez ↓",
        "step_eyes":   "{ack}👁 <b>Étape 5 — Yeux</b>\n{bar}\n\nChoisissez ↓",
        "step_flag":   "{ack}🌍 <b>Étape 6 — Pays</b>\n{bar}\n\nEnvoyez un <b>emoji drapeau</b>",
        "step_photo":  "{ack}📸 <b>Étape 7 — Photo</b>\n{bar}\n\n🔒 <i>Affichée anonymement</i>\n\n⬇️ Envoyez",
        "profile_card": (
            "👤 <b>PROFIL ANONYME</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "{gi}  <b>Genre</b> ›  {g}\n🎂  <b>Âge</b> ›  {a}\n"
            "📏  <b>Taille</b> ›  {h} cm\n💇  <b>Cheveux</b> ›  {hr}\n"
            "👁  <b>Yeux</b> ›  {e}\n🌍  <b>Pays</b> ›  {f}\n━━━━━━━━━━━━━━━━━━━━"
        ),
        "profile_ready": f"🎊 <b>Profil PRÊT!</b> 🎊\n\n✨ Commencez\n⭐ <i><b>{DAILY_FREE}</b> recherches/jour!</i>",
        "find_friend":  "🔍  Trouver un ami",
        "edit_profile": "✏️  Modifier le profil",
        "invite_btn":   f"🎁  Inviter (+{REFERRAL_BONUS} ⭐)",
        "blocks":       "🚫  Liste noire",
        "back_menu":    "🏠  Accueil",
        "searching":    "🔍 <b>Recherche...</b>\n<i>Trouver le meilleur profil</i> 💫",
        "found_profile":"💫 <b>Nouveau profil trouvé!</b>",
        "like": "❤️  Aimer", "block_btn": "🚫  Bloquer", "next_btn": "⏭  Suivant",
        "no_users": f"😔 <b>Personne pour l'instant...</b>\n\n💡\n• Invitez (+{REFERRAL_BONUS}!) 🎁\n• Réessayez 🕐\n• Nouvelles personnes chaque jour! 🌟",
        "req_sent":  "💌 <b>Demande envoyée!</b>\n\n⏳ <i>En attente... ✨</i>",
        "new_req":   "💘 <b>Quelqu'un vous a aimé!</b>\n\n👇 Accepter ou refuser",
        "accept": "✅  Accepter", "decline": "❌  Refuser",
        "match_screen": "💥 <b>C'EST UN MATCH!</b> 💥\n\n❤️‍🔥 Vous vous êtes mutuellement aimés!\n━━━━━━━━━━━━━━━━━━━━\n🔐 Identité <b>cachée</b>\n💬 Chattez — texte, photos, stickers 📸\n━━━━━━━━━━━━━━━━━━━━\n\n⬇️ Terminer ci-dessous",
        "chat_end_btn": "🔚  Terminer",
        "chat_end":     "👋 <b>Chat terminé</b>\n\n💘 <i>Bonne rencontre!</i>",
        "partner_left": "⚠️ <b>Votre partenaire s'est déconnecté</b>",
        "unblock": "🔓  Débloquer", "blocked_ok": "🚫 Bloqué",
        "unblocked_ok": "🔓 Débloqué", "blocks_empty": "✅ <b>Liste noire vide</b>",
        "blocked_user_row": "🔒  Anonyme #{n}",
        "pay_stars_3":    "⭐ <b>Recherches épuisées</b>\n\n💫 <b>5 ⭐ Stars</b>",
        "pay_stars_edit": "✏️ <b>Profil déjà modifié</b>\n\n💫 <b>100 ⭐ Stars</b>",
        "pay_success_connect": "✅ <b>Paiement accepté!</b>\n\n❤️ Envoi...",
        "pay_success_edit":    "✅ <b>Paiement accepté!</b>\n\n✏️ Modifiez",
        "invite_text": (
            f"🎁 <b>REFERRAL!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Invitez ➜ <u>vous deux</u> recevez <b>+{REFERRAL_BONUS} ⭐</b>\n\n"
            "📤 <code>{link}</code>\n\n━━━━━━━━━━━━━━━━━━━━\n"
            "👤 Invités ›  <code>{count}</code>\n⭐ Bonus ›  <code>{bonus}</code>\n━━━━━━━━━━━━━━━━━━━━"
        ),
        "ref_bonus_inviter": f"🎉 <b>Votre ami a rejoint!</b>\n\n⭐ +{REFERRAL_BONUS} — vous en avez <b>{{n}}</b>",
        "ref_bonus_invited": f"🎁 <b>Bonus reçu!</b>\n\n⭐ +{REFERRAL_BONUS} — vous en avez <b>{{n}}</b>",
        "share_btn":   "📤  Partager",
        "daily_refill": f"🌅 <b>Bonjour!</b>\n\n⭐ +{DAILY_FREE} — vous en avez <b>{{n}}</b>",
    },
}

for _flag, _code in LANG_MAP.items():
    if _code not in TEXTS:
        TEXTS[_code] = TEXTS["en"].copy()


def get_txt(uid: int, key: str) -> str:
    lang = USERS_DB.get(uid, {}).get("lang", "en")
    return TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))


# ════════════════════════════════════════════════════════════════════════════
#  FSM STATES
# ════════════════════════════════════════════════════════════════════════════
class RegStates(StatesGroup):
    lang   = State()
    gender = State()
    age    = State()
    height = State()
    hair   = State()
    eyes   = State()
    flag   = State()
    photo  = State()


# ════════════════════════════════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════════════════════════════════
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    global BOT_USERNAME
    uid = message.from_user.id
    await state.clear()
    if BOT_USERNAME is None:
        me = await bot.get_me()
        BOT_USERNAME = me.username
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            inviter_id = int(args[1][4:])
            if inviter_id != uid and uid not in REFERRALS and inviter_id in USERS_DB:
                REFERRALS[uid] = inviter_id
        except ValueError:
            pass
    init_user(uid, tg_user=message.from_user)
    buttons, row = [], []
    for flag, code in LANG_MAP.items():
        row.append(InlineKeyboardButton(text=f"{flag}  {LANG_NAMES.get(flag, code)}", callback_data=f"lang_{flag}"))
        if len(row) == 2:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    await message.answer(TEXTS["hy"]["welcome_lang"],
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await state.set_state(RegStates.lang)


# ════════════════════════════════════════════════════════════════════════════
#  LANGUAGE SELECTION
# ════════════════════════════════════════════════════════════════════════════
@dp.callback_query(F.data.startswith("lang_"), RegStates.lang)
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    flag      = callback.data[5:]
    lang_code = LANG_MAP.get(flag, "en")
    uid       = callback.from_user.id
    init_user(uid, tg_user=callback.from_user)
    USERS_DB[uid]["lang"] = lang_code
    reg_btn = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS[lang_code].get("register", "🚀  Create my profile"))]],
        resize_keyboard=True)
    await callback.answer(f"✅  {LANG_NAMES.get(flag, lang_code)}")
    await typing_action(uid, 0.5)
    await callback.message.answer(get_txt(uid, "welcome"), reply_markup=reg_btn, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════════════════
#  REGISTRATION
# ════════════════════════════════════════════════════════════════════════════
@dp.message(F.text.in_([TEXTS[l]["register"] for l in TEXTS]))
async def start_reg(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if USERS_DB.get(uid, {}).get("edit_count", 0) >= 1:
        await message.answer(get_txt(uid, "pay_stars_edit"), parse_mode="HTML")
        await bot.send_invoice(chat_id=uid, title="✏️ Edit Profile",
            description="Pay 100 Stars to edit your profile", payload="edit_profile_pay",
            provider_token=PROVIDER_TOKEN, currency="XTR",
            prices=[LabeledPrice(label="⭐ 100 Stars", amount=100)])
        return
    await ask_gender(message, state)


async def ask_gender(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    bar = progress_bar(1)
    kb  = ReplyKeyboardMarkup(keyboard=[[
        KeyboardButton(text=get_txt(uid, "male")),
        KeyboardButton(text=get_txt(uid, "female")),
        KeyboardButton(text=get_txt(uid, "other")),
    ]], resize_keyboard=True)
    await typing_action(uid, 0.5)
    await message.answer(get_txt(uid, "step_gender").format(bar=bar), reply_markup=kb, parse_mode="HTML")
    await state.set_state(RegStates.gender)


@dp.message(RegStates.gender)
async def process_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    uid = message.from_user.id
    ack = step_ack(1, gender_icon(message.text), message.text)
    bar = progress_bar(2)
    kb  = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🌱  12–15"), KeyboardButton(text="🌸  16–18")],
        [KeyboardButton(text="🌟  19–25"), KeyboardButton(text="🏆  25+")],
    ], resize_keyboard=True)
    await typing_action(uid, 0.4)
    await message.answer(get_txt(uid, "step_age").format(ack=ack, bar=bar), reply_markup=kb, parse_mode="HTML")
    await state.set_state(RegStates.age)


@dp.message(RegStates.age)
async def process_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    uid = message.from_user.id
    ack = step_ack(2, "🎂", message.text)
    bar = progress_bar(3)
    await typing_action(uid, 0.4)
    await message.answer(get_txt(uid, "step_height").format(ack=ack, bar=bar),
                         reply_markup=types.ReplyKeyboardRemove(), parse_mode="HTML")
    await state.set_state(RegStates.height)


@dp.message(RegStates.height)
async def process_height(message: types.Message, state: FSMContext):
    await state.update_data(height=message.text)
    uid = message.from_user.id
    ack = step_ack(3, "📏", message.text)
    bar = progress_bar(4)
    kb  = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚫️ Սև"),   KeyboardButton(text="🟤 Շագանակ"), KeyboardButton(text="🟡 Շիկ")],
        [KeyboardButton(text="🔴 Կարմիր"), KeyboardButton(text="⚪️ Սպիտակ"), KeyboardButton(text="🟣 Մանուշ")],
        [KeyboardButton(text="🔵 Կապույт"), KeyboardButton(text="🟢 Կանաչ"),  KeyboardButton(text="🟠 Նarnjaгuyn")],
    ], resize_keyboard=True)
    await typing_action(uid, 0.4)
    await message.answer(get_txt(uid, "step_hair").format(ack=ack, bar=bar), reply_markup=kb, parse_mode="HTML")
    await state.set_state(RegStates.hair)


@dp.message(RegStates.hair)
async def process_hair(message: types.Message, state: FSMContext):
    await state.update_data(hair=message.text)
    uid = message.from_user.id
    ack = step_ack(4, (message.text or " ").split()[0], "")
    bar = progress_bar(5)
    kb  = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚫️ Սև"),    KeyboardButton(text="🟤 Շag"),  KeyboardButton(text="🔵 Կaput")],
        [KeyboardButton(text="🟢 Կanach"), KeyboardButton(text="⚪️ Mokhr"), KeyboardButton(text="🟡 Deghja")],
        [KeyboardButton(text="🟣 Manush"), KeyboardButton(text="🟠 Bac shag")],
    ], resize_keyboard=True)
    await typing_action(uid, 0.4)
    await message.answer(get_txt(uid, "step_eyes").format(ack=ack, bar=bar), reply_markup=kb, parse_mode="HTML")
    await state.set_state(RegStates.eyes)


@dp.message(RegStates.eyes)
async def process_eyes(message: types.Message, state: FSMContext):
    await state.update_data(eyes=message.text)
    uid = message.from_user.id
    ack = step_ack(5, (message.text or " ").split()[0], "")
    bar = progress_bar(6)
    await typing_action(uid, 0.4)
    await message.answer(get_txt(uid, "step_flag").format(ack=ack, bar=bar),
                         reply_markup=types.ReplyKeyboardRemove(), parse_mode="HTML")
    await state.set_state(RegStates.flag)


@dp.message(RegStates.flag)
async def process_flag(message: types.Message, state: FSMContext):
    await state.update_data(flag=message.text)
    uid = message.from_user.id
    ack = step_ack(6, message.text or "🌍", "")
    bar = progress_bar(7)
    await typing_action(uid, 0.4)
    await message.answer(get_txt(uid, "step_photo").format(ack=ack, bar=bar), parse_mode="HTML")
    await state.set_state(RegStates.photo)


@dp.message(RegStates.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data     = await state.get_data()
    uid      = message.from_user.id
    USERS_DB[uid].update({"gender": data["gender"], "age": data["age"], "height": data["height"],
                          "hair": data["hair"], "eyes": data["eyes"], "flag": data["flag"], "photo": photo_id})
    USERS_DB[uid]["edit_count"] += 1
    await state.clear()
    await photo_action(uid, 0.8)
    await message.answer(get_txt(uid, "profile_ready"), parse_mode="HTML")
    if USERS_DB[uid]["edit_count"] == 1 and uid in REFERRALS:
        inviter_id = REFERRALS[uid]
        if inviter_id in USERS_DB:
            USERS_DB[uid]["free_chats"]   += REFERRAL_BONUS
            USERS_DB[uid]["ref_bonus"]    = USERS_DB[uid].get("ref_bonus", 0) + REFERRAL_BONUS
            await asyncio.sleep(0.4)
            await message.answer(get_txt(uid, "ref_bonus_invited").format(n=USERS_DB[uid]["free_chats"]), parse_mode="HTML")
            USERS_DB[inviter_id]["free_chats"] += REFERRAL_BONUS
            USERS_DB[inviter_id]["ref_count"]   = USERS_DB[inviter_id].get("ref_count", 0) + 1
            USERS_DB[inviter_id]["ref_bonus"]   = USERS_DB[inviter_id].get("ref_bonus", 0) + REFERRAL_BONUS
            try:
                await bot.send_message(inviter_id,
                    get_txt(inviter_id, "ref_bonus_inviter").format(n=USERS_DB[inviter_id]["free_chats"]),
                    parse_mode="HTML")
            except Exception:
                pass
    await asyncio.sleep(0.5)
    await show_main_menu(message.chat.id, uid)


# ════════════════════════════════════════════════════════════════════════════
#  MAIN MENU
# ════════════════════════════════════════════════════════════════════════════
async def show_main_menu(chat_id: int, uid: int):
    u         = USERS_DB[uid]
    free_left = u.get("free_chats", 0)
    caption   = build_profile_card(uid, u)
    footer    = f"\n\n⭐ <i>Mnacel e  <b>{free_left}</b>  anvachar knoum</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(uid, "find_friend"),  callback_data="menu_find")],
        [InlineKeyboardButton(text=get_txt(uid, "edit_profile"), callback_data="menu_edit")],
        [InlineKeyboardButton(text=get_txt(uid, "invite_btn"),   callback_data="menu_invite")],
        [InlineKeyboardButton(text=get_txt(uid, "blocks"),       callback_data="menu_blocks")],
    ])
    await photo_action(chat_id, 0.5)
    await bot.send_photo(chat_id, photo=u["photo"], caption=caption + footer, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.data == "menu_edit")
async def inline_edit_profile(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    if USERS_DB.get(uid, {}).get("edit_count", 0) >= 1:
        await callback.message.answer(get_txt(uid, "pay_stars_edit"), parse_mode="HTML")
        await bot.send_invoice(chat_id=uid, title="✏️ Edit Profile",
            description="Pay 100 Stars to edit your profile", payload="edit_profile")
from aiogram.filters import Command
from aiogram import types

# ⚠️ ԿԱՐԵՎՈՐ: Փոխիր սա քո իրական Telegram ID-ով
# Քո ID-ն կարող ես տեսնել Render-ի լոգերում (uid-ի արժեքը)
ADMIN_ID = 6614409372 

# ==========================================
# 1. ԱՆԱՆՈՒՆ ՆԱՄԱԿ ԱԴՄԻՆԻՆ (Օգտատիրոջ կողմից)
# ==========================================

@dp.message(Command("support"))
async def support_command(message: types.Message, state: FSMContext):
    """Օգտատերը գրում է /support, որպեսզի նամակ ուղարկի ադմինին"""
    await message.answer("✍️ Գրեք ձեր հարցը կամ բողոքը այս նամակին պատասխանելով (Reply), և ադմինը կստանա այն անանուն։")
    # Եթե ունես state-եր, կարող ես սահմանել state, բայց ավելի պարզ տարբերակը Reply-ով աշխատելն է։

@dp.message(lambda message: message.reply_to_message and "Գրեք ձեր հարցը" in message.reply_to_message.text)
async def forward_to_admin(message: types.Message):
    """Երբ օգտատերը reply է անում support նամակին, այն գնում է ադմինին"""
    uid = message.from_user.id
    
    # Նամակը ուղարկում ենք ադմինին՝ նշելով օգտատիրոջ ID-ն
    admin_text = (
        f"📩 Նոր նամակ օգտատիրոջից!\n"
        f"🆔 ID: {uid}\n"
        f"🔗 Էջի հղում: [Սեղմիր](tg://user?id={uid})\n\n"
        f"📝 Նամակ՝ {message.text}\n\n"
        f"📌 *Պատասխանելու համար արա REPLY այս նամակին։*"
    )
    
    await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
    await message.answer("✅ Ձեր նամակն ուղարկվեց ադմինիստրացիային։")


# ==========================================
# 2. ԱԴՄԻՆԻ ԱՆԱՆՈՒՆ ՊԱՏԱՍԽԱՆԸ ՕԳՏԱՏԻՐՈՋԻՆ
# ==========================================

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.reply_to_message)
async def admin_reply_handler(message: types.Message):
    """Երբ ադմինը REPLY է անում օգտատիրոջ նամակին, պատասխանը գնում է օգտատիրոջը"""
    try:
        # Լոգիկայով գտնում ենք օգտատիրոջ ID-ն ադմինին եկած նամակի տեքստից
        reply_text = message.reply_to_message.text
        if "🆔 ID:" in reply_text:
            # Վերցնում ենք ID-ն տեքստի միջից
            target_uid = int(reply_text.split("🆔 ID:")[1].split("\n")[0].strip())
            
            # Ուղարկում ենք պատասխանը օգտատիրոջը (Ադմինի տվյալները ՓԱԿ են մնում)
            user_msg = f"🔔 Պատասխան ադմինիստրատորից՝\n\n{message.text}"
            await bot.send_message(chat_id=target_uid, text=user_msg)
            await message.answer("✅ Պատասխանը հաջողությամբ ուղարկվեց օգտատիրոջը։")
    except Exception as e:
        await message.answer(f"❌ Սխալ՝ չհաջողվեց ուղարկել նամակը։ ({e})")


# ==========================================
# 3. ԱԴՄԻՆԻ ՀՐԱՄԱՆՆԵՐ (ԲԱԶԱՅԻ ԿԱՌԱՎԱՐՈՒՄ)
# ==========================================

@dp.message(Command("give_free"))
async def give_free_access(message: types.Message):
    """Անվճար խմբագրման հնարավորություն տալ. /give_free ID"""
    if message.from_user.id != ADMIN_ID:
        return

    try:
        target_uid = int(message.text.split()[1])
        if target_uid in USERS_DB:
            # Զրոյացնում ենք edit_count-ը, որ անցնի քո 796 տողի ստուգումը
            USERS_DB[target_uid]["edit_count"] = 0 
            await message.answer(f"✅ {target_uid} ID-ով օգտատիրոջը տրվեց անվճար հնարավորություն։")
            
            try:
                await bot.send_message(chat_id=target_uid, text="🎉 Ադմինիստրատորի կողմից ձեզ տրվեց պրոֆիլը անվճար խմբագրելու հնարավորություն։")
            except Exception:
                pass
        else:
            await message.answer("❌ Այսպիսի ID-ով օգտատեր չգտնվեց բազայում։")
    except (IndexError, ValueError):
        await message.answer("✍️ Գրիր այսպես՝ /give_free ՕԳՏԱՏԻՐՈՋ_ID")
@dp.message(Command("check_user"))
async def check_user_profile(message: types.Message):
    """Տեսնել օգտատիրոջ տվյալները բազայից. /check_user ID"""
    if message.from_user.id != ADMIN_ID:
        return

    try:
        target_uid = int(message.text.split()[1])
        if target_uid in USERS_DB:
            user_data = USERS_DB[target_uid]
            profile_link = f"tg://user?id={target_uid}"
            info_text = (
                f"📊 **Օգտատիրոջ անկետան բազայում:**\n\n"
                f"🆔 ID: `{target_uid}`\n"
                f"🔗 Տելեգրամ էջ: [Բացել էջը]({profile_link})\n"
                f"⚙️ Բոլոր տվյալները:\n`{user_data}`"
            )
            await message.answer(info_text, parse_mode="Markdown")
        else:
            await message.answer("❌ Օգտատերը չգտնվեց բազայում։")
    except (IndexError, ValueError):
        await message.answer("✍️ Գրիր այսպես՝ `/check_user ՕԳՏԱՏԻՐՈՋ_ID`")

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    """Բլոկել օգտատիրոջը. /ban ID"""
    if message.from_user.id != ADMIN_ID:
        return

    try:
        target_uid = int(message.text.split()[1])
        if target_uid in USERS_DB:
            USERS_DB[target_uid]["is_banned"] = True
            await message.answer(f"🚫 Օգտատեր {target_uid}-ը բլոկավորվեց։")
            try:
                await bot.send_message(chat_id=target_uid, text="🚫 Դուք բլոկավորվել եք ադմինիստրացիայի կողմից։")
            except Exception:
                pass
        else:
            await message.answer("❌ Օգտատերը չգտնվեց։")
    except (IndexError, ValueError):
        await message.answer("✍️ Գրիր այսպես՝ `/ban ՕԳՏԱՏԻՐՈՋ_ID`")
