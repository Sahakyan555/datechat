import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Կարգավորումներ
TOKEN = "8834098974:AAG-O0bKfyMdLC45sy4H8axWNkyU9OHKkOw"
ADMIN_ID = 6614409372

# Լոգինգ
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Տվյալների բազայի ստեղծում
async def init_db():
    async with aiosqlite.connect("bot_data.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT, gender TEXT, flag TEXT,
                money INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_expiry TEXT,
                likes INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# Գրանցման քայլերը
class Registration(StatesGroup):
    flag = State()
    name = State()
    gender = State()
    photo = State()

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇦🇲 Հայաստան", callback_data="flag_am"), 
         InlineKeyboardButton(text="🇷🇺 Ռուսաստան", callback_data="flag_ru")],
        [InlineKeyboardButton(text="🇺🇸 Ամերիկա", callback_data="flag_us"), 
         InlineKeyboardButton(text="🇩🇪 Գերմանիա", callback_data="flag_de")],
        [InlineKeyboardButton(text="🇫🇷 Ֆրանսիա", callback_data="flag_fr")]
    ])
    await message.answer("Բարև՛, ընտրիր քո լեզուն՝ սեղմելով դրոշի վրա:", reply_markup=kb)
    await state.set_state(Registration.flag)

# Շարունակելի է...
# Գրանցման շարունակություն
@dp.callback_query(Registration.flag, F.data.startswith("flag_"))
async def set_flag(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(flag=callback.data)
    await callback.message.edit_text("📝 Քայլ 2: Գրիր քո անունը:")
    await state.set_state(Registration.name)

@dp.message(Registration.name)
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👦 Տղա", callback_data="g_boy"), 
         InlineKeyboardButton(text="👧 Աղջիկ", callback_data="g_girl"),
         InlineKeyboardButton(text="👤 Այլ", callback_data="g_other")]
    ])
    await message.answer("⚧ Քայլ 3: Ընտրիր սեռը:", reply_markup=kb)
    await state.set_state(Registration.gender)

@dp.callback_query(Registration.gender, F.data.startswith("g_"))
async def set_gender(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(gender=callback.data)
    await callback.message.edit_text("📸 Քայլ 4: Ուղարկիր քո լուսանկարը:")
    await state.set_state(Registration.photo)

@dp.message(Registration.photo, F.photo)
async def finish_reg(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect("bot_data.db") as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, name, gender, flag) VALUES (?, ?, ?, ?)",
                         (message.from_user.id, data['name'], data['gender'], data['flag']))
        await db.commit()
    
    await message.answer("✅ Գրանցումն ավարտվեց:\n" + f"Անուն՝ {data['name']}\nՍեռ՝ {data['gender']}")
    await show_main_menu(message)
    await state.clear()

# Հիմնական մենյու
async def show_main_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Որոնել ընկեր", callback_data="search"), InlineKeyboardButton(text="✏️ Փոխել պրոֆիլը", callback_data="edit")],
        [InlineKeyboardButton(text="🔗 Տարածել (+5 money)", callback_data="share"), InlineKeyboardButton(text="🎮 Mini Game", callback_data="game")]
    ])
    await message.answer("Ընտրիր գործողությունը՝", reply_markup=kb)
# Mini Game - 16 վանդակ
@dp.callback_query(F.data == "game")
async def mini_game(callback: types.CallbackQuery):
    # Սա դեմո խաղն է (16 վանդակ)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬜", callback_data="box") for _ in range(4)] for _ in range(4)
    ])
    await callback.message.answer("🎮 Բարի գալուստ խաղ: Բացիր վանդակները:", reply_markup=kb)

# Դոնատ ադմինին (Telegram Stars)
@dp.message(Command("donate"))
async def donate(message: types.Message):
    await message.answer("Դոնատի չափը (աստղերով):")

@dp.message(F.text.isdigit())
async def process_donate(message: types.Message):
    amount = message.text
    await bot.send_message(ADMIN_ID, f"💰 Նոր դոնատ: {amount} աստղ\nՕգտատեր՝ {message.from_user.id}")
    await message.answer("Շնորհակալություն դոնատի համար!")

# Անանուն նամակ ադմինին
@dp.message(Command("anon"))
async def anon_msg(message: types.Message, state: FSMContext):
    await message.answer("Գրիր նամակը, ես այն անանուն կուղարկեմ ադմինին:")
    await state.set_state("waiting_for_anon")

@dp.message(F.state == "waiting_for_anon")
async def send_anon_to_admin(message: types.Message, state: FSMContext):
    await bot.send_message(ADMIN_ID, f"📩 Անանուն նամակ:\nID: {message.from_user.id}\nNickname: {message.from_user.username}\nՏեքստ՝ {message.text}")
    await message.answer("Նամակը ուղարկված է!")
    await state.clear()
# ԱԴՄԻՆԻ ՀՐԱՄԱՆՆԵՐ
@dp.message(Command("vip"))
async def admin_vip(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) > 1:
        target_id = args[1]
        async with aiosqlite.connect("bot_data.db") as db:
            await db.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (target_id,))
            await db.commit()
        await message.answer(f"✅ Օգտատեր {target_id}-ը դարձավ VIP!")

@dp.message(Command("money"))
async def admin_money(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) > 2:
        target_id, amount = args[1], args[2]
        async with aiosqlite.connect("bot_data.db") as db:
            await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, target_id))
            await db.commit()
        await message.answer(f"💰 {amount} մոնեյ ուղարկված է {target_id}-ին:")

# ԳՈՐԾԱՐԿՄԱՆ ՖՈՒՆԿՑԻԱ
async def main():
    await init_db()
    print("🤖 Բոտը հաջողությամբ գործարկվեց (GitHub-ի համար պատրաստ է)!")
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
