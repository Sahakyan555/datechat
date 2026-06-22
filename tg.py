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
ADMIN_ID       = 661440932 

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
    "🇬🇪": "ქարթուլի",    "🇦🇷": "Español",   "🇯🇵": "日本語",
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
    try:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(delay)
    except Exception:
        pass

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
    "hy": {
        "welcome_lang": "💘 <b>DATE CHAT</b>\n━━━━━━━━━━━━━━━━━━━━\n🌍 Ընտրեք ձեր լեզուն\n<i>Choose / Выберите</i>",
        "welcome": "✨ <b>Բարի գալուստ DATE CHAT!</b> ✨\n\n💘 Ծանոթացեք <b>անանուն</b> կերպով\n🔒 Ձեր Telegram ID-ն երբեք չի բացահայտվի\n💬 Շփվեք, ընկերացեք, հայտնաբերեք!\n🎁 Ամեն օր <b>{DAILY_FREE}</b> անվճար որոնում\n\n━━━━━━━━━━━━━━━━━━━━\n⬇️ Սեղմեք կոճակը՝ սկսելու",
        "register": "🚀  Ստեղծել իմ պրոֆիլը",
        "step_gender": "👤 <b>Քայլ 1 — Ձեր սեռը</b>\n{bar}\n\nԵս եմ ↓",
        "male": "👨  Տղա", "female": "👩  Աղջիկ", "other": "🌈  Այլ",
        "step_age": "{ack}🎂 <b>Քայլ 2 — Տարիքային խումբ</b>\n{bar}\n\nԸնտրեք ↓",
        "step_height": "{ack}📏 <b>Քայլ 3 — Հասակ</b>\n{bar}\n\nԳրեք սմ-ով  <i>(օր. <code>173</code>)</i>",
        "step_hair": "{ack}💇 <b>Քայլ 4 — Մազերի գույն</b>\n{bar}\n\nԸնտրեք ↓",
        "step_eyes": "{ack}👁 <b>Քայլ 5 — Աչքերի գույն</b>\n{bar}\n\nԸնտրեք ↓",
        "step_flag": "{ack}🌍 <b>Քայլ 6 — Ձեր երկիրը</b>\n{bar}\n\nՈւղարկեք <b>դրոշ emoji</b>  <i>(🇦🇲 🇺🇸 🇷🇺)</i>",
        "step_photo": "{ack}📸 <b>Քայլ 7 — Ձեր լավագույն նկարը</b>\n{bar}\n\n🔒 <i>Ցուցադրվում է <b>անանուն</b> — Ձեր անունը թաքնված է մնալու</i>\n\n⬇️ ուղարկեք նկար",
        "profile_card": "👤 <b>Անանուն Պրոֆիլ</b>\n━━━━━━━━━━━━━━━━━━━━\n{gi}  <b>Սեռ</b>      ›  {g}\n🎂  <b>Տարիք</b>     ›  {a}\n📏  <b>Հասակ</b>     ›  {h} cm\n💇  <b>Մազեր</b>     ›  {hr}\n👁  <b>Աչքեր</b>     ›  {e}\n🌍  <b>Երկիր</b>     ›  {f}\n━━━━━━━━━━━━━━━━━━━━",
        "profile_ready": "🎊 <b>Պրոֆիլը ՊԱՏՐԱՍՏ Է!</b> 🎊\n\n✨ Արդեն կարող եք փնտրել ընկեր\n⭐ <i>Այսօր ունեք <b>{DAILY_FREE}</b> անվճար որոնում!</i>",
        "find_friend": "🔍  Փնտրել ընկեր", "edit_profile": "✏️  Փոխել պրոֆիլը",
        "invite_btn": f"🎁  Հրավիրել ընկեր (+{REFERRAL_BONUS} ⭐)", "blocks": "🚫  Բլոկ ցուցակ", "back_menu": "🏠  Գլխավոր",
        "searching": "🔍 <b>Փնտրում ենք...</b>\n<i>Փնտրում ենք լավագույն պրոֆիլը ձեր համար</i> 💫",
        "found_profile": "💫 <b>Նոր պրոֆիլ գտնվեց!</b>", "like": "❤️  Հավանել", "block_btn": "🚫  Մերժել", "next_btn": "⏭  Հաջորդ պրոֆիլը",
        "no_users": f"😔 <b>Դեռ ոչ ոք չկա...</b>\n\n💡 <b>Tips</b>\n• Հրավիրել ընկերներ 🎁 (+{REFERRAL_BONUS} որոնում!)\n• Փորձել ավելի ուշ 🕐\n• Ամենուր մարդիկ են գրանցվում! 🌟",
        "req_sent": "💌 <b>Հարցումն ուղարկվել է!</b>\n\n⏳ <i>Սպասեք արձագանքի...</i>",
        "new_req": "💘 <b>Ձեզ հավանեցին!</b>\n\n👇 Ընդունեք ծանոթության հրավերը", "accept": "✅  Ընդունել", "decline": "❌  Մերժել",
        "match_screen": "💥 <b>MATCH!</b> 💥\n\n❤️‍🔥 Երկուսդ էլ հավանեցիք միմյանց!\n━━━━━━━━━━━━━━━━━━━━\n🔐 Ձեր ինքնությունը <b>ամբողջովին թաքնված է</b>\n💬 Ազատ խոսեք — text, նկար, sticker 📸\n━━━━━━━━━━━━━━━━━━━━\n\n⬇️ Ավարտելու համար սեղմել ստորև",
        "chat_end_btn": "🔚  Ավարտել չատը", "chat_end": "👋 <b>Չատը ավարտվեց</b>\n\n💘 <i>Հուսով ենք հաճելի ծանոթություն էր!</i>\n🔍 <i>Ցանկանո՞ւմ եք գտնել նոր ընկեր:</i>",
        "partner_left": "⚠️ <b>Զրուցակիցը անջատվել է</b>\n\n🔍 Ցանկանո՞ւմ եք գտնել նոր ընկեր:",
        "unblock": "🔓  Ապաբլոկավորել", "blocked_ok": "🚫 Բլոկվեց", "unblocked_ok": "🔓 Ապաբլոկվեց",
        "blocks_empty": "✅ <b>Բլոկ ցուցակը դատարկ է</b>", "blocked_user_row": "🔒  Անանուն #{n}",
        "pay_stars_3": "⭐ <b>Անվճար որոնումների լիմիտը սպառված է</b>\n\n💫 Հաջորդ որոնման համար` <b>5 ⭐ Stars</b>\n🔒 <i>Ապահով վճարում Telegram-ի միջոցով</i>",
        "pay_stars_edit": "✏️ <b>Պրոֆիլը արդեն փոխվել է</b>\n\n💫 Կրկին փոխելու համար` <b>100 ⭐ Stars</b>",
        "pay_success_connect": "✅ <b>Վճարումն ընդունված է!</b>\n\n❤️ Հարցումն ուղարկվել է...",
        "pay_success_edit": "✅ <b>Վճարումն ընդունված է!</b>\n\n✏️ Փոխեք ձեր պրոֆիլը",
        "invite_text": f"🎁 <b>REFERRAL — Հրավիրիր, վաստակիր!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👥 Հրավիրիր ընկեր ➜ <u>երկուսդ էլ</u> կստանաք <b>+{REFERRAL_BONUS} ⭐ անվճար որոնում</b>\n\n📤 Հրավիրիր քո հղումով ↓\n\n<code>{{link}}</code>\n\n━━━━━━━━━━━━━━━━━━━━\n👤 Հրավիրված›  <code>{{count}}</code> հոգի\n⭐ Ստացված բոնուս ›  <code>{{bonus}}</code> որոնում\n━━━━━━━━━━━━━━━━━━━━",
        "ref_bonus_inviter": f"🎉 <b>Ընկերդ գրանցվեց!</b>\n\n⭐ +{REFERRAL_BONUS} անվճար որոնում",
        "ref_bonus_invited": f"🎁 <b>Հրավերի միջոցով վաստակիր բոնուս!</b>\n\n⭐ +{REFERRAL_BONUS} անվճար որոնում",
        "share_btn": "📤  Ուղարկել ընկերներին", "daily_refill": f"🌅 <b>Բարի լույս!</b>\n\n⭐ +{DAILY_FREE} անվճար որոնում ավելացվեց",
    },
    "en": {
        "welcome_lang": "💘 <b>DATE CHAT</b>\n━━━━━━━━━━━━━━━━━━━━\n🌍 Choose your language",
        "welcome": "✨ <b>Welcome to DATE CHAT!</b> ✨\n\n💘 Meet people <b>anonymously</b>\n🔒 Your identity is never revealed\n💬 Chat, connect, make friends!\n🎁 Get <b>{DAILY_FREE}</b> free searches every day\n\n━━━━━━━━━━━━━━━━━━━━\n⬇️ Tap the button to begin",
        "register": "🚀  Create my profile", "step_gender": "👤 <b>Step 1 — Your gender</b>\n{bar}\n\nI am ↓",
        "male": "👨  Male", "female": "👩  Female", "other": "🌈  Other",
        "step_age": "{ack}🎂 <b>Step 2 — Age group</b>\n{bar}\n\nChoose ↓",
        "step_height": "{ack}📏 <b>Step 3 — Height</b>\n{bar}\n\nType in cm  <i>(e.g. <code>173</code>)</i>",
        "step_hair": "{ack}💇 <b>Step 4 — Hair color</b>\n{bar}\n\nChoose ↓",
        "step_eyes": "{ack}👁 <b>Step 5 — Eye color</b>\n{bar}\n\nChoose ↓",
        "step_flag": "{ack}🌍 <b>Step 6 — Your country</b>\n{bar}\n\nSend a <b>flag emoji</b>",
        "step_photo": "{ack}📸 <b>Step 7 — Your best photo</b>\n{bar}\n\n🔒 <i>Shown anonymously</i>\n\n⬇️ Send a photo",
        "profile_card": "👤 <b>ANONYMOUS PROFILE</b>\n━━━━━━━━━━━━━━━━━━━━\n{gi}  <b>Gender</b>   ›  {g}\n🎂  <b>Age</b>      ›  {a}\n📏  <b>Height</b>   ›  {h} cm\n💇  <b>Hair</b>     ›  {hr}\n👁  <b>Eyes</b>     ›  {e}\n🌍  <b>Country</b>  ›  {f}\n━━━━━━━━━━━━━━━━━━━━",
        "profile_ready": f"🎊 <b>Profile READY!</b> 🎊\n\n✨ Start finding friends\n⭐ <i>Get <b>{DAILY_FREE}</b> free searches every day!</i>",
        "find_friend": "🔍  Find a Friend", "edit_profile": "✏️  Edit Profile",
        "invite_btn": f"🎁  Invite Friend (+{REFERRAL_BONUS} ⭐)", "blocks": "🚫  Blocklist", "back_menu": "🏠  Home",
        "searching": "🔍 <b>Searching...</b>\n<i>Finding the best profile for you</i> 💫",
        "found_profile": "💫 <b>New profile found!</b>", "like": "❤️  Like", "block_btn": "🚫  Block", "next_btn": "⏭  Next",
        "no_users": f"😔 <b>Nobody here right now...</b>\n\n💡 <b>Tips</b>\n• Invite friends 🎁 (+{REFERRAL_BONUS} searches!)\n• Try again later 🕐\n• New people join every day! 🌟",
        "req_sent": "💌 <b>Request sent!</b>\n\n⏳ <i>Waiting for response...</i>",
        "new_req": "💘 <b>Someone liked you!</b>\n\n👇 Accept or decline", "accept": "✅  Accept", "decline": "❌  Decline",
        "match_screen": "💥 <b>IT'S A MATCH!</b> 💥\n\n❤️‍🔥 You both liked each other!\n━━━━━━━━━━━━━━━━━━━━\n🔐 Your identity is <b>fully hidden</b>\n💬 Chat freely — text, photos, stickers 📸\n━━━━━━━━━━━━━━━━━━━━\n\n⬇️ Tap below to end",
        "chat_end_btn": "🔚  End Chat", "chat_end": "👋 <b>Chat ended</b>\n\n💘 <i>Hope it was a great connection!</i>",
        "partner_left": "⚠️ <b>Partner disconnected</b>\n\n🔍 Want to find someone new?",
        "unblock": "🔓  Unblock", "blocked_ok": "🚫 Blocked", "unblocked_ok": "🔓 Unblocked",
        "blocks_empty": "✅ <b>Blocklist is empty</b>", "blocked_user_row": "🔒  Anonymous #{n}",
        "pay_stars_3": "⭐ <b>Free searches used up</b>\n\n💫 Just <b>5 ⭐ Stars</b> to connect\n🔒 <i>Secure payment via Telegram</i>",
        "pay_stars_edit": "✏️ <b>Profile already edited once</b>\n\n💫 <b>100 ⭐ Stars</b> to edit again",
        "pay_success_connect": "✅ <b>Payment accepted!</b>\n\n❤️ Sending request...", "pay_success_edit": "✅ <b>Payment accepted!</b>\n\n✏️ Edit profile",
        "invite_text": f"🎁 <b>REFERRAL — Invite & Earn!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👥 Invite a friend ➜ <u>both</u> get <b>+{REFERRAL_BONUS} ⭐ free searches</b>\n\n📤 Your link ↓\n\n<code>{{link}}</code>\n\n━━━━━━━━━━━━━━━━━━━━\n👤 Invited  ›  <code>{{count}}</code> people\n⭐ Bonus  ›  <code>{{bonus}}</code>\n━━━━━━━━━━━━━━━━━━━━",
        "ref_bonus_inviter": f"🎉 <b>Your friend joined!</b>\n\n⭐ +{REFERRAL_BONUS} free searches",
        "ref_bonus_invited": f"🎁 <b>Bonus for joining!</b>\n\n⭐ +{REFERRAL_BONUS} free searches",
        "share_btn": "📤  Share", "daily_refill": f"🌅 <b>Good morning!</b>\n\n⭐ +{DAILY_FREE} free searches added",
    }
}

# Ռուսերենն ու մյուս լեզուները ավտոմատ լրացվում են անգլերենով, եթե չկան
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
#  MAIN MENU KEYBOARD BUILDER
# ════════════════════════════════════════════════════════════════════════════
def get_main_menu(uid: int):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_txt(uid, "find_friend"))],
            [KeyboardButton(text=get_txt(uid, "edit_profile")), KeyboardButton(text=get_txt(uid, "invite_btn"))],
            [KeyboardButton(text=get_txt(uid, "blocks"))]
        ],
        resize_keyboard=True
    )

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
            if inviter_id != uid and uid not in REFERRALS:
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
#  REGISTRATION & TELEGRAM STARS FOR EDIT
# ════════════════════════════════════════════════════════════════════════════
@dp.message(lambda m: any(m.text == TEXTS[l].get("register") for l in TEXTS))
async def start_reg(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    init_user(uid, message.from_user)
    
    if USERS_DB[uid].get("edit_count", 0) >= 1:
        await message.answer(get_txt(uid, "pay_stars_edit"), parse_mode="HTML")
        await bot.send_invoice(
            chat_id=uid, 
            title="✏️ Edit Profile",
            description="Pay 100 Stars to edit your profile", 
            payload="edit_profile_pay",
            provider_token=PROVIDER_TOKEN, 
            currency="XTR",
            prices=[LabeledPrice(label="⭐ 100 Stars", amount=100)]
        )
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
        [KeyboardButton(text="🔵 Կապույտ"), KeyboardButton(text="🟢 Կանաչ"),  KeyboardButton(text="🟠 Նարնջագույն")],
    ], resize_keyboard=True)
    await typing_action(uid, 0.4)
    await message.answer(get_txt(uid, "step_hair").format(ack=ack, bar=bar), reply_markup=kb, parse_mode="HTML")
    await state.set_state(RegStates.hair)

@dp.message(RegStates.hair)
async def process_hair(message: types.Message, state: FSMContext):
    await state.update_data(hair=message.text)
    uid = message.from_user.id
    ack = step_ack(4, "💇", message.text)
    bar = progress_bar(5)
    kb  = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🟤 Շագանակագույն"), KeyboardButton(text="🔵 Կապույտ"), KeyboardButton(text="🟢 Կանաչ")],
        [KeyboardButton(text="⚫️ Սև"), KeyboardButton(text="🔘 Մոխրագույն"), KeyboardButton(text="🟡 Դեղին")],
    ], resize_keyboard=True)
    await message.answer(get_txt(uid, "step_eyes").format(ack=ack, bar=bar), reply_markup=kb, parse_mode="HTML")
    await state.set_state(RegStates.eyes)

@dp.message(RegStates.eyes)
async def process_eyes(message: types.Message, state: FSMContext):
    await state.update_data(eyes=message.text)
    uid = message.from_user.id
    ack = step_ack(5, "👁", message.text)
    bar = progress_bar(6)
    await message.answer(get_txt(uid, "step_flag").format(ack=ack, bar=bar), reply_markup=types.ReplyKeyboardRemove(), parse_mode="HTML")
    await state.set_state(RegStates.flag)

@dp.message(RegStates.flag)
async def process_flag(message: types.Message, state: FSMContext):
    await state.update_data(flag=message.text)
    uid = message.from_user.id
    ack = step_ack(6, "🌍", message.text)
    bar = progress_bar(7)
    await message.answer(get_txt(uid, "step_photo").format(ack=ack, bar=bar), parse_mode="HTML")
    await state.set_state(RegStates.photo)

@dp.message(RegStates.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    
    USERS_DB[uid]["gender"] = data.get("gender")
    USERS_DB[uid]["age"] = data.get("age")
    USERS_DB[uid]["height"] = data.get("height")
    USERS_DB[uid]["hair"] = data.get("hair")
    USERS_DB[uid]["eyes"] = data.get("eyes")
    USERS_DB[uid]["flag"] = data.get("flag")
    USERS_DB[uid]["photo"] = message.photo[-1].file_id
    USERS_DB[uid]["edit_count"] = USERS_DB[uid].get("edit_count", 0) + 1
    
    await state.clear()
    
    # Ռեֆերալի բոնուսների հաշվարկ
    if uid in REFERRALS:
        inviter = REFERRALS[uid]
        if inviter in USERS_DB:
            USERS_DB[inviter]["free_chats"] += REFERRAL_BONUS
            USERS_DB[inviter]["ref_count"] += 1
            USERS_DB[inviter]["ref_bonus"] += REFERRAL_BONUS
            try:
                await bot.send_message(inviter, get_txt(inviter, "ref_bonus_inviter").format(n=USERS_DB[inviter]["free_chats"]), parse_mode="HTML")
            except Exception:
                pass
        USERS_DB[uid]["free_chats"] += REFERRAL_BONUS
        del REFERRALS[uid]
        
    await message.answer(get_txt(uid, "profile_ready"), reply_markup=get_main_menu(uid), parse_mode="HTML")

# ════════════════════════════════════════════════════════════════════════════
#  TELEGRAM STARS HANDLERS (PRE-CHECKOUT & SUCCESS)
# ════════════════════════════════════════════════════════════════════════════
@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    payload = message.successful_payment.invoice_payload
    if payload == "edit_profile_pay":
        USERS_DB[uid]["edit_count"] = 0  # Զրոյացնում ենք, որ թողնի խմբագրել
        await message.answer(get_txt(uid, "pay_success_edit"), parse_mode="HTML")
        await ask_gender(message, state)

# ════════════════════════════════════════════════════════════════════════════
#  GLOBAL TEXT BUTTONS FILTERS (ՀՍՏԱԿ ԱՇԽԱՏԱՆՔԻ ՀԱՄԱՐ)
# ════════════════════════════════════════════════════════════════════════════

# 1. ՓՈԽԵԼ ՊՐՈՖԻԼԸ
@dp.message(lambda m: any(m.text == TEXTS[l].get("edit_profile") for l in TEXTS))
async def menu_edit_profile(message: types.Message, state: FSMContext):
    await start_reg(message, state)

# 2. ԲԼՈԿ ՑՈՒՑԱԿ
@dp.message(lambda m: any(m.text == TEXTS[l].get("blocks") for l in TEXTS))
async def menu_blocks(message: types.Message):
    uid = message.from_user.id
    init_user(uid, message.from_user)
    await message.answer(get_txt(uid, "blocks_empty"), parse_mode="HTML")

# 3. ՀՐԱՎԻՐԵԼ ԸՆԿԵՐ
@dp.message(lambda m: any(m.text == TEXTS[l].get("invite_btn") for l in TEXTS))
async def menu_invite(message: types.Message):
    uid = message.from_user.id
    init_user(uid, message.from_user)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    txt = get_txt(uid, "invite_text").format(
        link=link,
        count=USERS_DB[uid].get("ref_count", 0),
        bonus=USERS_DB[uid].get("ref_bonus", 0)
    )
    await message.answer(txt, parse_mode="HTML")

# 4. ՓՆՏՐԵԼ ԸՆԿԵՐ
@dp.message(lambda m: any(m.text == TEXTS[l].get("find_friend") for l in TEXTS))
async def menu_find_friend(message: types.Message):
    uid = message.from_user.id
    init_user(uid, message.from_user)
    daily_refill(uid)
    
    # Ստուգում ենք լիմիտը
    if USERS_DB[uid]["free_chats"] <= 0:
        await message.answer(get_txt(uid, "pay_stars_3"), parse_mode="HTML")
        return
        
    await message.answer(get_txt(uid, "searching"), parse_mode="HTML")
    await asyncio.sleep(1.5)
    await message.answer(get_txt(uid, "no_users"), parse_mode="HTML")

# ════════════════════════════════════════════════════════════════════════════
#  WEB SERVER FOR RENDER (ԱՆԸՆԴՀԱՏ ԱՇԽԱՏԵԼՈՒ ՀԱՄԱՐ)
# ════════════════════════════════════════════════════════════════════════════
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 10000)))
    await site.start()
    
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
