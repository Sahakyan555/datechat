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
    LabeledPrice, PreCheckoutQuery
)

# ── Կոնֆիգ ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]
PROVIDER_TOKEN = ""
ADMIN_ID = 661440932 

DAILY_FREE = 3
REFERRAL_BONUS = 5

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ՔՈ ՕՐԻԳԻՆԱԼ ՏՎՅԱԼՆԵՐԸ (Սկիզբ) ---
USERS_DB = {}
CHATS = {}
REQUESTS = {}
REFERRALS = {}
BOT_USERNAME = None

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

# (Այստեղ պետք է լինեն քո TEXTS dictionary-ն և helper ֆունկցիաները)
# ... [Քո օրիգինալ ֆունկցիաները՝ progress_bar, step_ack, gender_icon և այլն] ...

# --- ՔՈ ՕՐԻԳԻՆԱԼ ՏՎՅԱԼՆԵՐԸ (Վերջ) ---

# ════════════════════════════════════════════════════════════════════════════
# 🆕 ԱԴՄԻՆ ԵՎ ԴՈՆԱՏԻ ՆՈՐ ՖՈՒՆԿՑԻԱՆԵՐ
# ════════════════════════════════════════════════════════════════════════════

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

class DonateStates(StatesGroup):
    waiting_for_amount = State()

# 1. Ադմին պանել
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Վիճակագրություն"), KeyboardButton(text="📢 Ռեկլամ")],
        [KeyboardButton(text="🔙 Գլխավոր")]
    ], resize_keyboard=True)
    await message.answer("👑 Ադմին պանել", reply_markup=kb)

@dp.message(F.text == "📊 Վիճակագրություն")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"👥 Օգտատերերի ընդհանուր քանակը՝ {len(USERS_DB)}")

@dp.message(F.text == "📢 Ռեկլամ")
async def broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Ուղարկեք ռեկլամի տեքստը՝")
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def broadcast_send(message: types.Message, state: FSMContext):
    count = 0
    for uid in USERS_DB:
        try: 
            await bot.send_message(uid, message.text)
            count += 1
        except: pass
    await state.clear()
    await message.answer(f"✅ Ռեկլամը հաջողությամբ ուղարկվեց {count} օգտատիրոջ։")

# 2. Ազատ դոնատի տրամաբանություն
@dp.message(F.text == "❤️ Դոնատ")
async def start_donate(message: types.Message, state: FSMContext):
    await message.answer("Գրեք քանի՞ Telegram Stars եք ցանկանում նվիրաբերել (միայն թիվ):")
    await state.set_state(DonateStates.waiting_for_amount)

@dp.message(DonateStates.waiting_for_amount)
async def process_donate_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): 
        return await message.answer("Խնդրում եմ գրել միայն թիվ!")
    amount = int(message.text)
    await state.clear()
    
    await bot.send_invoice(
        chat_id=message.from_user.id,
        title="Դոնատ բոտի համար",
        description=f"Աջակցություն բոտի զարգացմանը՝ {amount} Stars",
        payload="donate_stars",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=amount)],
        provider_token=""
    )

@dp.pre_checkout_query()
async def checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

# ════════════════════════════════════════════════════════════════════════════
# 🚀 ԾՐԱԳՐԻ ՄԵԿՆԱՐԿ
# ════════════════════════════════════════════════════════════════════════════

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
