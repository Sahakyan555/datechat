import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8834098974:AAG-O0bKfyMdLC45sy4H8axWNkyU9OHKkOw"
bot = Bot(token=TOKEN)
dp = Dispatcher()

class Registration(StatesGroup):
    flag = State()
    name = State()
    gender = State()
    photo = State()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇦🇲", callback_data="flag_am"), InlineKeyboardButton(text="🇷🇺", callback_data="flag_ru")],
        [InlineKeyboardButton(text="🇺🇸", callback_data="flag_us"), InlineKeyboardButton(text="🇩🇪", callback_data="flag_de")],
        [InlineKeyboardButton(text="🇫🇷", callback_data="flag_fr")]
    ])
    await message.answer("Ընտրեք ձեր դրոշը՝ լեզուն ընտրելու համար:", reply_markup=kb)
    await state.set_state(Registration.flag)

@dp.callback_query(Registration.flag, F.data.startswith("flag_"))
async def process_flag(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(flag=callback.data)
    await callback.message.answer("Գրանցման քայլ 2. Գրեք ձեր անունը:")
    await state.set_state(Registration.name)

@dp.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Տղա", callback_data="g_boy"), InlineKeyboardButton(text="Աղջիկ", callback_data="g_girl"), InlineKeyboardButton(text="Այլ", callback_data="g_other")]
    ])
    await message.answer("Գրանցման քայլ 3. Ընտրեք ձեր սեռը:", reply_markup=kb)
    await state.set_state(Registration.gender)

@dp.callback_query(Registration.gender, F.data.startswith("g_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(gender=callback.data)
    await callback.message.answer("Գրանցման քայլ 4. Ուղարկեք ձեր նկարը:")
    await state.set_state(Registration.photo)

@dp.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # Այստեղ տվյալները պետք է գրել տվյալների բազայում
    await message.answer(f"Շնորհավորում ենք! Դուք գրանցվեցիք:\nԱնուն՝ {data['name']}\nՍեռ՝ {data['gender']}")
    await state.clear()import aiosqlite

# Տվյալների բազայի ինիցիալիզացիա և պրոֆիլի տեսք
async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                gender TEXT,
                flag TEXT,
                photo_id TEXT,
                money INTEGER DEFAULT 0,
                stars INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_profile_text(user_id):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                vip_status = "👑 VIP" if user[7] else ""
                return f"{vip_status}\nԱնուն՝ {user[1]}\nՍեռ՝ {user[2]}\nԼայքեր՝ {user[8]}\nMoney՝ {user[5]}"
    return "Պրոֆիլը չի գտնվել"

# Գլխավոր մենյուի կոճակներ
def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="🔍 Որոնել ընկեր", callback_data="search_friend")],
        [InlineKeyboardButton(text="✏️ Փոխել պրոֆիլը", callback_data="edit_profile")],
        [InlineKeyboardButton(text="🔗 Տարածել +5 Bonus", callback_data="share_bot")],
        [InlineKeyboardButton(text="🎮 Mini Game", callback_data="mini_game")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)import random
# Մինի խաղի տրամաբանություն
async def play_mini_game(user_id):
    items = ["❌", "❌", "❌", "💸", "💰"] # 70% ❌, 25% 💸, 5% 💰
    results = [random.choice(items) for _ in range(5)]
    return results

# Ընկերների որոնում (պարզեցված)
@dp.callback_query(F.data == "search_friend")
async def search_friend(callback: types.CallbackQuery):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT user_id, name FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (callback.from_user.id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❤️ Լայքել", callback_data=f"like_{user[0]}")],
                    [InlineKeyboardButton(text="🤝 Ընկերանալ", callback_data=f"friend_{user[0]}")],
                    [InlineKeyboardButton(text="⏭ Հաջորդը", callback_data="search_friend")]
                ])
                await callback.message.answer(f"Գտնված է՝ {user[1]}", reply_markup=kb)
            else:
                await callback.message.answer("Այլ օգտատերեր չկան։")

# Անանուն նամակ ադմինին
@dp.message(Command("anon_to_admin"))
async def anon_admin(message: types.Message, state: FSMContext):
    await message.answer("Գրեք ձեր անանուն նամակը ադմինին:")
    await state.set_state("waiting_for_anon")

@dp.message(F.state == "waiting_for_anon")
async def send_anon(message: types.Message, state: FSMContext):
    await bot.send_message(6614409372, f"Անանուն նամակ:\nID: {message.from_user.id}\nՆամակ: {message.text}")
    await message.answer("Նամակը ուղարկված է։")
    await state.clear()# Ադմինի հրամաններ
@dp.message(Command("admin_give_money"))
async def admin_give_money(message: types.Message):
    if message.from_user.id != 6614409372: return
    args = message.text.split()
    if len(args) == 3:
        target_id, amount = args[1], args[2]
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, target_id))
            await db.commit()
        await message.answer(f"Օգտատեր {target_id}-ին փոխանցվեց {amount} մոնեյ։")

@dp.message(Command("admin_vip"))
async def admin_vip(message: types.Message):
    if message.from_user.id != 6614409372: return
    target_id = message.text.split()[1]
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (target_id,))
        await db.commit()
    await message.answer(f"Օգտատեր {target_id}-ը դարձավ VIP։")

# VIP առավելությունների տեքստ
VIP_BENEFITS = """
VIP ԳՆԵԼՈՒ ԱՌԱՎԵԼՈՒԹՅՈՒՆՆԵՐԸ.
1. VIP կարգավիճակ պրոֆիլում (👑)
2. Անսահմանափակ մոնեյներ (1 ամիս)
3. Պրոֆիլի անվճար փոփոխություն
4. VIP հատուկ հասանելիություն
Գինը՝ 500 Stars
"""
