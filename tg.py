import os
import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton, PreCheckoutQuery, ContentType, LabeledPrice
)
from aiohttp import web

# ⚙️ ԼՈԳԵՐ ԵՎ ՏՈԿԵՆ
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = 123456789  # ՓՈԽԻՐ ՔՈ ՏԵԼԵԳՐԱՄ ID-ՈՎ

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 🗄️ ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ (SQLite)
DB_PATH = "date_chat.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT,
            gender TEXT,
            age TEXT,
            height INTEGER,
            hair TEXT,
            eyes TEXT,
            country TEXT,
            photo TEXT,
            stars INTEGER DEFAULT 3,
            is_banned INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            user_id INTEGER,
            blocked_id INTEGER,
            PRIMARY KEY (user_id, blocked_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 🎭 FSM ՎԻՃԱԿՆԵՐ
class Registration(StatesGroup):
    lang = State()
    gender = State()
    age = State()
    height = State()
    hair = State()
    eyes = State()
    country = State()
    photo = State()

class DonateStates(StatesGroup):
    waiting_for_amount = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_stars_add = State()

# ⌨️ ԿՈՃԱԿՆԵՐԻ ՄԵՆՅՈՒՆԵՐ
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Փնտրել ընկեր"), KeyboardButton(text="✏️ Փոխել պրոֆիլը")],
            [KeyboardButton(text="🎁 Հրավիրել ընկեր (+5 ⭐)"), KeyboardButton(text="🚫 Բլոկ ցուցակ")],
            [KeyboardButton(text="❤️ Դոնատ Ադմինին (Stars)")]
        ],
        resize_keyboard=True
    )

def get_admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Վիճակագրություն"), KeyboardButton(text="📢 Ուղարկել Ռեկլամ")],
            [KeyboardButton(text="💰 Ավելացնել Stars"), KeyboardButton(text="🔙 Դեպի Մենյու")]
        ],
        resize_keyboard=True
    )

# ==================== 🚀 START & ԴՈՆԱՏ ԱՌԱՆՑ ԳՐԱՆՑՎԵԼՈՒ ====================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    args = message.text.split()
    ref_id = args[1] if len(args) > 1 and args[1].isdigit() else None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, gender FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if user and user[1]: # Եթե արդեն լրիվ գրանցված է
        conn.close()
        await message.answer("✨ Բարի գալուստ հետ։ Դուք արդեն գրանցված եք ընդհանուր բազայում։", reply_markup=get_main_menu())
    else:
        if not user:
            if ref_id and int(ref_id) != message.from_user.id:
                cursor.execute("UPDATE users SET stars = stars + 5 WHERE user_id = ?", (int(ref_id),))
                try:
                    await bot.send_message(int(ref_id), "🎁 Ձեր հղումով նոր օգտատեր գրանցվեց։ Դուք ստացաք +5 ⭐!")
                except Exception:
                    pass
            
            cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (message.from_user.id, message.from_user.username))
            conn.commit()
        conn.close()

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇦🇲 Հայերեն", callback_data="setlang_hy"),
             InlineKeyboardButton(text="🇺🇸 English", callback_data="setlang_en")]
        ])
        await message.answer("🌍 Ընտրեք ձեր լեզուն / Choose your language:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, callback.from_user.id))
    conn.commit()
    conn.close()

    await callback.message.delete()
    
    welcome_btns = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Ստեղծել պրոֆիլը", callback_data="start_reg")],
        [InlineKeyboardButton(text="❤️ Աջակցել նախագծին (Դոնատ)", callback_data="donate_custom")]
    ])
    await callback.message.answer(
        "✨ **Բարի գալուստ DATE CHAT!** ✨\n\n🔒 Անանուն շփում\n🎁 Ամեն օր 3 անվճար որոնում\n\n💬 Դուք կարող եք դոնատ անել ադմինին նույնիսկ առանց գրանցվելու սկսելու։",
        reply_markup=welcome_btns, parse_mode="Markdown"
    )

# 🍩 ԱԶԱՏ ՉԱՓԻ ԴՈՆԱՏԻ ՄԵԿՆԱՐԿ (ԿՈՃԱԿՆԵՐԻՑ)
@dp.callback_query(F.data == "donate_custom")
async def donate_custom_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("❤️ **Գրեք, թե քանի՞ Telegram Stars եք ցանկանում նվիրաբերել (միայն թիվ).**")
    await state.set_state(DonateStates.waiting_for_amount)

@dp.message(F.text == "❤️ Դոնատ Ադմինին (Stars)")
async def donate_from_menu(message: types.Message, state: FSMContext):
    await message.answer("❤️ **Գրեք, թե քանի՞ Telegram Stars եք ցանկանում նվիրաբերել (միայն թիվ).**")
    await state.set_state(DonateStates.waiting_for_amount)

# 💳 ՕԳՏԱՏՐՈՋ ԳՐԱԾ ԹՎՈՎ ԻՆՎՈՅՍԻ ՍՏԵՂԾՈՒՄ
@dp.message(DonateStates.waiting_for_amount)
async def process_custom_donate_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("🔢 Խնդրում եմ մուտքագրել միայն թիվ (օրինակ՝ 25, 100, 500)։")
    
    stars_amount = int(message.text)
    if stars_amount <= 0:
        return await message.answer("❌ Դոնատի չափը պետք է մեծ լինի 0-ից։")
    
    await state.clear()
    prices = [LabeledPrice(label="XTR", amount=stars_amount)]
    
    # Ուղարկում ենք ինվոյսը՝ ըստ օգտատիրոջ գրած թվի
    await message.answer_invoice(
        title="❤️ Աջակցություն Ադմինին",
        description=f"Կամավոր նվիրատվություն բոտի զարգացման համար՝ {stars_amount} Stars:",
        prices=prices,
        provider_token="",
        payload=f"donate_{stars_amount}",
        currency="XTR",
        reply_markup=get_main_menu() if message.text else None # Վերադարձնում է մենյուն, եթե գրանցված էր
    )

# ==================== 📝 7-ՔԱՅԼԱՆԻ ԳՐԱՆՑՈՒՄ ====================

@dp.callback_query(F.data == "start_reg")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👨 Տղա"), KeyboardButton(text="👩 Աղջիկ")]
    ], resize_keyboard=True)
    await callback.message.answer("👤 Քայլ 1/7: Ընտրեք ձեր սեռը. `▓░░░░░░ 14%`", reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(Registration.gender)

@dp.message(Registration.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🌱 12–15"), KeyboardButton(text="🌸 16–18")],
        [KeyboardButton(text="🌟 19–25"), KeyboardButton(text="🏆 25+")]
    ], resize_keyboard=True)
    await message.answer("🎂 Քայլ 2/7: Ընտրեք տարիքային խումբը. `▓▓░░░░░ 28%`", reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(Registration.age)

@dp.message(Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("📏 Քայլ 3/7: Գրեք ձեր հասակը (օրինակ՝ 175). `▓▓▓░░░░ 42%`", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.set_state(Registration.height)

@dp.message(Registration.height)
async def reg_height(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("🔢 Խնդրում եմ գրել միայն թվերով (օրինակ՝ 170):")
    await state.update_data(height=int(message.text))
    
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚫ Սև"), KeyboardButton(text="🟤 Շագանակագույն")],
        [KeyboardButton(text="🟡 Շիկահեր"), KeyboardButton(text="🔴 Շեկ")]
    ], resize_keyboard=True)
    await message.answer("💇 Քայլ 4/7: Մազերի գույնը. `▓▓▓▓░░░ 57%`", reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(Registration.hair)

@dp.message(Registration.hair)
async def reg_hair(message: types.Message, state: FSMContext):
    await state.update_data(hair=message.text)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🟤 Շագանակագույն"), KeyboardButton(text="🔵 Կապույտ")],
        [KeyboardButton(text="🟢 Կանաչ"), KeyboardButton(text="⚫ Սև")]
    ], resize_keyboard=True)
    await message.answer("👁️ Քայլ 5/7: Աչքերի գույնը. `▓▓▓▓▓░░ 71%`", reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(Registration.eyes)

@dp.message(Registration.eyes)
async def reg_eyes(message: types.Message, state: FSMContext):
    await state.update_data(eyes=message.text)
    await message.answer("🌍 Քայլ 6/7: Ո՞ր երկրում/քաղաքում եք ապրում. `▓▓▓▓▓▓░ 85%`", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.set_state(Registration.country)

@dp.message(Registration.country)
async def reg_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("📸 Քայլ 7/7: Ուղարկեք 1 լուսանկար ձեր պրոֆիլի համար. `▓▓▓▓▓▓▓ 100%`", parse_mode="Markdown")
    await state.set_state(Registration.photo)

@dp.message(Registration.photo, F.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET 
        gender = ?, age = ?, height = ?, hair = ?, eyes = ?, country = ?, photo = ?
        WHERE user_id = ?
    """, (data['gender'], data['age'], data['height'], data['hair'], data['eyes'], data['country'], photo_id, message.from_user.id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("🎊 **Շնորհավորում ենք! Ձեր պրոֆիլը պատրաստ է:**", reply_markup=get_main_menu(), parse_mode="Markdown")

# ==================== 🔍 ՈՐՈՆՄԱՆ ՏՐԱՄԱԲԱՆՈՒԹՅՈՒՆ ====================

@dp.message(F.text == "🔍 Փնտրել ընկեր")
async def search_partner(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT gender, stars FROM users WHERE user_id = ?", (user_id,))
    my_info = cursor.fetchone()
    
    if not my_info or not my_info[0]:
        conn.close()
        return await message.answer("❌ Դուք դեռ չեք լրացրել պրոֆիլը: Սեղմեք /start")
        
    my_gender, my_stars = my_info
    
    if my_stars <= 0:
        conn.close()
        return await message.answer("😢 Ձեր օրական անվճար լիմիտները սպառվել են։ Դոնատ արեք կամ հրավիրեք ընկերների՝ Stars ստանալու համար։")

    target_gender = "👩 Աղջիկ" if "Տղա" in my_gender else "👨 Տղա"
    
    cursor.execute("""
        SELECT user_id, gender, age, height, hair, eyes, country, photo FROM users
        WHERE user_id != ? 
          AND gender = ? 
          AND photo IS NOT NULL
          AND user_id NOT IN (SELECT blocked_id FROM blocks WHERE user_id = ?)
          AND user_id NOT IN (SELECT user_id FROM blocks WHERE blocked_id = ?)
        ORDER BY RANDOM() LIMIT 1
    """, (user_id, target_gender, user_id, user_id))
    
    partner = cursor.fetchone()
    
    if not partner: 
        cursor.execute("""
            SELECT user_id, gender, age, height, hair, eyes, country, photo FROM users
            WHERE user_id != ? 
              AND photo IS NOT NULL
              AND user_id NOT IN (SELECT blocked_id FROM blocks WHERE user_id = ?)
              AND user_id NOT IN (SELECT user_id FROM blocks WHERE blocked_id = ?)
            ORDER BY RANDOM() LIMIT 1
        """, (user_id, user_id, user_id))
        partner = cursor.fetchone()

    if partner:
        p_id, p_gen, p_age, p_height, p_hair, p_eyes, p_country, p_photo = partner
        cursor.execute("UPDATE users SET stars = stars - 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Գրել անանուն", callback_data=f"chat_{p_id}")],
            [InlineKeyboardButton(text="🚫 Բլոկել", callback_data=f"block_{p_id}")]
        ])
        
        profile_text = (
            f"💘 **Գտնվել է զույգ!**\n\n👤 Սեռ: {p_gen}\n🎂 Տարիք: {p_age}\n"
            f"📏 Հասակ: {p_height} սմ\n💇 Մազեր: {p_hair}\n👁️ Աչքեր: {p_eyes}\n"
            f"🌍 Երկիր: {p_country}\n\n⭐ Մնացած որոնումներդ: {my_stars - 1}"
        )
        await message.answer_photo(photo=p_photo, caption=profile_text, reply_markup=buttons, parse_mode="Markdown")
    else:
        await message.answer("😔 Ցավոք, այս պահին համակարգում ակտիվ նոր մարդ չգտնվեց։ Փորձեք մի փոքր ուշ։")
        
    conn.close()

# ==================== 💳 TELEGRAM STARS ՀԵՆԴԼԵՐՆԵՐ ====================

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    
    if payload.startswith("donate_"):
        amount = payload.split("_")[1]
        await message.answer(f"❤️ **Շնորհակալություն!** Ձեր կողմից մուտքագրված {amount} ⭐ Stars-ի դոնատը հաջողությամբ հասավ ադմինին։")
        
        try:
            await bot.send_message(ADMIN_ID, f"💰 **ՆՈՐ ԱԶԱՏ ԴՈՆԱՏ!**\n👤 Օգտատեր՝ @{message.from_user.username} (ID: {message.from_user.id})\n💸 Չափսը՝ {amount} ⭐ Stars")
        except Exception:
            pass

# ==================== 👑 ԱԴՄԻՆ ՊԱՆԵԼ ====================

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Այս հրամանը հասանելի է միայն ադմինիստրատորին։")
    await message.answer("👑 Բարի գալուստ Ադմին Պանել։", reply_markup=get_admin_menu())

@dp.message(F.text == "📊 Վիճակագրություն")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE gender IS NOT NULL")
    active = cursor.fetchone()[0]
    conn.close()
    await message.answer(f"📊 **Վիճակագրություն:**\n\n👥 Ընդհանուր բազա: {total}\n📝 Լրացված պրոֆիլներ: {active}", parse_mode="Markdown")

@dp.message(F.text == "📢 Ուղարկել Ռեկլամ")
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📝 Ուղարկեք տեքստ կամ նկար (կամ գրեք 'cancel')՝")
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    if message.text == "cancel":
        await state.clear()
        return await message.answer("❌ Չեղարկվեց։", reply_markup=get_admin_menu())

    await state.clear()
    await message.answer("⏳ Ուղարկվում է...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success, fail = 0, 0
    for u in users:
        try:
            if message.content_type == ContentType.TEXT:
                await bot.send_message(u[0], message.text)
            elif message.content_type == ContentType.PHOTO:
                await bot.send_photo(u[0], message.photo[-1].file_id, caption=message.caption)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1

    await message.answer(f"✅ Հասավ: {success}\n🔴 Չհասավ: {fail}", reply_markup=get_admin_menu())

@dp.message(F.text == "💰 Ավելացնել Stars")
async def admin_add_stars_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("✍️ Ձևաչափը՝ `ID ՔԱՆԱԿ`", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_stars_add)

@dp.message(AdminStates.waiting_for_stars_add)
async def admin_add_stars_save(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    try:
        target_id, count = map(int, message.text.split())
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (count, target_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Ավելացվեց {count} ⭐", reply_markup=get_admin_menu())
    except Exception:
        await message.answer("❌ Սխալ ձևաչափ։", reply_markup=get_admin_menu())

@dp.message(F.text == "🔙 Դեպի Մենյու")
async def back_to_menu(message: types.Message):
    await message.answer("🔙 Վերադարձաք գլխավոր մենյու", reply_markup=get_main_menu())

# ==================== WEB SERVER 24/7 (RENDER) ====================

async def handle(request):
    return web.Response(text="Bot is running live 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
    await site.start()

async def main():
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
