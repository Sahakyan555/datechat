import logging
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery

# --- ՏՎՅԱԼՆԵՐԻ ԲԱԶԱՅԻ ՍՏԵՂԾՈՒՄ ---
conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    lang TEXT,
    flag TEXT,
    anon_name TEXT,
    gender TEXT,
    photo_id TEXT,
    money INTEGER DEFAULT 3,
    likes INTEGER DEFAULT 0,
    is_vip BOOLEAN DEFAULT 0,
    vip_until TEXT,
    free_until TEXT,
    referrer_id INTEGER,
    last_daily TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS likes (
    from_id INTEGER,
    to_id INTEGER,
    PRIMARY KEY (from_id, to_id)
)
''')
conn.commit()

# --- ԿՈՆՖԻԳՈՒՐԱՑԻԱ ---
BOT_TOKEN = "8834098974:AAG-O0bKfyMdLC45sy4H8axWNkyU9OHKkOw"
ADMIN_ID = 6614409372

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# --- ԼԵԶՈՒՆԵՐԻ ՏԵՔՍՏԵՐ ---
TEXTS = {
    'am': {
        'start': "👋 Բարև! Խնդրում եմ ընտրել քո լեզուն / Пожалуйста, выберите язык:",
        'main_menu': "⚙️ Ընտրեք գործողությունը. \n💰 Ձեր մոնեթները՝ {money}",
        'reg_btn': "📝 Գրանցվել", 'donate_btn': "⭐️ Դոնատ Ադմինին",
        'step1': "🇦🇲 Քայլ 1: Ուղարկեք Ձեր պետության դրոշի էմոջին (օր.՝ 🇦🇲):",
        'step2': "👤 Քայլ 2: Գրեք Ձեր անանուն մականունը բոտի համար.",
        'step3': "⚧ Քայլ 3: Ընտրեք Ձեր սեռը.",
        'step4': "📸 Քայլ 4: Ուղարկեք Ձեր նկարը պրոֆիլի համար.",
        'profile': "{vip_tag}👤 ՊՐՈՖԻԼ\n🌐 Լեզու: {flag}\n🎭 Անուն: {name}\n⚧ Սեռ: {gender}\n❤️ Լայքեր: {likes}\n💰 Մոնեթներ: {money}",
        'search': "🔍 Որոնել ընկեր", 'edit': "🔄 Փոխել պրոֆիլը", 'share': "🔗 Տարածել +5 bonus", 'game': "🎮 Mini Game",
        'anon_msg': "✉️ Գրել անանուն նամակ ադմինին"
    },
    'ru': {
        'start': "👋 Выберите язык / Choose language:",
        'main_menu': "⚙️ Выберите действие. \n💰 Ваши монеты: {money}",
        'reg_btn': "📝 Регистрация", 'donate_btn': "⭐️ Донат Админу",
        'step1': "🇷🇺 Шаг 1: Отправьте эмодзи флага вашей страны.",
        'step2': "👤 Шаг 2: Напишите анонимное имя для бота.",
        'step3': "⚧ Шаг 3: Выберите ваш пол.",
        'step4': "📸 Шаг 4: Отправьте фото для профиля.",
        'profile': "{vip_tag}👤 ПРОФИЛЬ\n🌐 Язык: {flag}\n🎭 Имя: {name}\n⚧ Пол: {gender}\n❤️ Лайки: {likes}\n💰 Монеты: {money}",
        'search': "🔍 Найти друга", 'edit': "🔄 Изменить профиль", 'share': "🔗 Поделиться +5 бонус", 'game': "🎮 Mini Game",
        'anon_msg': "✉️ Написать анонимно админу"
    },
    'en': {
        'start': "👋 Choose language:",
        'main_menu': "⚙️ Select action. \n💰 Your coins: {money}",
        'reg_btn': "📝 Register", 'donate_btn': "⭐️ Donate to Admin",
        'step1': "🇺🇸 Step 1: Send your country's flag emoji.",
        'step2': "👤 Step 2: Write your anonymous nickname.",
        'step3': "⚧ Step 3: Choose your gender.",
        'step4': "📸 Step 4: Send a photo for your profile.",
        'profile': "{vip_tag}👤 PROFILE\n🌐 Lang: {flag}\n🎭 Name: {name}\n⚧ Gender: {gender}\n❤️ Likes: {likes}\n💰 Coins: {money}",
        'search': "🔍 Search Friends", 'edit': "🔄 Edit Profile", 'share': "🔗 Share +5 bonus", 'game': "🎮 Mini Game",
        'anon_msg': "✉️ Message Admin Anonymously"
    },
    'de': {
        'start': "👋 Sprache wählen:",
        'main_menu': "⚙️ Option wählen. \n💰 Münzen: {money}",
'reg_btn': "📝 Registrieren", 'donate_btn': "⭐️ Admin spenden",
        'step1': "🇩🇪 Schritt 1: Senden Sie Ihr Länderflaggen-Emoji.",
        'step2': "👤 Schritt 2: Schreiben Sie Ihren Spitznamen.",
        'step3': "⚧ Schritt 3: Wählen Sie Ihr Geschlecht.",
        'step4': "📸 Schritt 4: Senden Sie ein Foto.",
        'profile': "{vip_tag}👤 PROFIL\n🌐 Flagge: {flag}\n🎭 Name: {name}\n⚧ Geschlecht: {gender}\n❤️ Likes: {likes}\n💰 Münzen: {money}",
        'search': "🔍 Freunde suchen", 'edit': "🔄 Profil ändern", 'share': "🔗 Teilen +5 Bonus", 'game': "🎮 Mini Game",
        'anon_msg': "✉️ Anonym an Admin schreiben"
    },
    'fr': {
        'start': "👋 Choisir la langue:",
        'main_menu': "⚙️ Choisir une option. \n💰 Pièces: {money}",
        'reg_btn': "📝 S'inscrire", 'donate_btn': "⭐️ Faire un don",
        'step1': "🇫🇷 Étape 1: Envoyez l'emoji du drapeau.",
        'step2': "👤 Étape 2: Érivez votre pseudo.",
        'step3': "⚧ Étape 3: Choisissez votre sexe.",
        'step4': "📸 Étape 4: Envoyez une photo.",
        'profile': "{vip_tag}👤 PROFIL\n🌐 Drapeau: {flag}\n🎭 Nom: {name}\n⚧ Sexe: {gender}\n❤️ J'aime: {likes}\n💰 Pièces: {money}",
        'search': "🔍 Chercher des amis", 'edit': "🔄 Modifier le profil", 'share': "🔗 Partager +5 bonus", 'game': "🎮 Mini Game",
        'anon_msg': "✉️ Écrire un message anonyme"
    }
}

# --- FSM STATES (ՌԵԺԻՄՆԵՐ) ---
class RegStates(StatesGroup):
    flag = State()
    name = State()
    gender = State()
    photo = State()

class DonateStates(StatesGroup):
    amount = State()

class AnonStates(StatesGroup):
    msg = State()

# --- ՀԻՄՆԱԿԱՆ ՖՈՒՆԿՑԻԱՆԵՐ ---
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def check_daily_money(user_id):
    user = get_user(user_id)
    if not user: return
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user[13] != today:
        new_money = user[7] + 3
        cursor.execute("UPDATE users SET money=?, last_daily=? WHERE user_id=?", (new_money, today, user_id))
        conn.commit()

# --- COMMAND /START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_id
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    user = get_user(user_id)
    if not user:
        cursor.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", 
                       (user_id, message.from_user.username, referrer_id))
        conn.commit()
    else:
        check_daily_money(user_id)

    # Լեզուների դրոշների կոճակները
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇦🇲 Հայերեն", callback_data="setlang_am"),
         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru")],
        [InlineKeyboardButton(text="🇺🇸 English", callback_data="setlang_en"),
         InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="setlang_de")],
        [InlineKeyboardButton(text="🇫🇷 Français", callback_data="setlang_fr")]
    ])
    await message.answer(TEXTS['am']['start'], reply_markup=keyboard)

@dp.callback_query(F.data.startswith("setlang_"))
async def set_language(call: types.CallbackQuery):
    lang = call.data.split("_")[1]
    flags = {'am': '🇦🇲', 'ru': '🇷🇺', 'en': '🇺🇸', 'de': '🇩🇪', 'fr': '🇫🇷'}
    cursor.execute("UPDATE users SET lang=?, flag=? WHERE user_id=?", (lang, flags[lang], call.from_user.id))
    conn.commit()
    
    await call.answer()
    
    # Գրանցվել և Դոնատ կոճակները
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=TEXTS[lang]['reg_btn']), KeyboardButton(text=TEXTS[lang]['donate_btn'])],
        [KeyboardButton(text=TEXTS[lang]['anon_msg'])]
    ], resize_keyboard=True)
    
    await call.message.answer(TEXTS[lang]['main_menu'].format(money=get_user(call.from_user.id)[7]), reply_markup=keyboard)
# --- ԴՈՆԱՏԻ ՀԱՏՎԱԾ (TELEGRAM STARS) ---
@dp.message(F.text.in_([TEXTS[l]['donate_btn'] for l in TEXTS]))
async def donate_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lang = user[2] if user[2] else 'am'
    await message.answer("Գրեք Stars-ի քանակը, որը ցանկանում եք դոնատ անել ադմինին (Օրինակ՝ 10):")
    await state.set_state(DonateStates.amount)

@dp.message(DonateStates.amount)
async def donate_invoice(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Խնդրում եմ գրել միայն թիվ։")
        return
    stars = int(message.text)
    await state.clear()
    
    await message.answer_invoice(
        title="Դոնատ Ադմինին",
        description=f"Աջակցություն նախագծի ադմինիստրատորին {stars} աստղով",
        payload=f"donate_{stars}",
        provider_token="", # Դատարկ է թողնվում Stars-ի համար
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=stars)]
    )

# --- ԳՐԱՆՑՄԱՆ ԳՈՐԾԸՆԹԱՑ (FSM) ---
@dp.message(F.text.in_([TEXTS[l]['reg_btn'] for l in TEXTS]))
async def reg_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lang = user[2] if user[2] else 'am'
    await message.answer(TEXTS[lang]['step1'])
    await state.set_state(RegStates.flag)

@dp.message(RegStates.flag)
async def reg_step1(message: types.Message, state: FSMContext):
    await state.update_data(flag=message.text)
    user = get_user(message.from_user.id)
    lang = user[2] if user[2] else 'am'
    await message.answer(TEXTS[lang]['step2'])
    await state.set_state(RegStates.name)

@dp.message(RegStates.name)
async def reg_step2(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    user = get_user(message.from_user.id)
    lang = user[2] if user[2] else 'am'
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Տղա"), KeyboardButton(text="Աղջիկ"), KeyboardButton(text="Այլ")]
    ], resize_keyboard=True)
    await message.answer(TEXTS[lang]['step3'], reply_markup=kb)
    await state.set_state(RegStates.gender)

@dp.message(RegStates.gender)
async def reg_step3(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    user = get_user(message.from_user.id)
    lang = user[2] if user[2] else 'am'
    await message.answer(TEXTS[lang]['step4'])
    await state.set_state(RegStates.photo)

@dp.message(RegStates.photo, F.photo)
async def reg_step4(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    await state.clear()
    
    # Պահպանում բազայում
    cursor.execute("UPDATE users SET flag=?, anon_name=?, gender=?, photo_id=? WHERE user_id=?",
                   (data['flag'], data['name'], data['gender'], photo_id, message.from_user.id))
    
    # Ռեֆերալի բոնուս (+5 Money)
    user_data = get_user(message.from_user.id)
    if user_data[12]: # If has referrer
        ref = get_user(user_data[12])
        if ref:
            cursor.execute("UPDATE users SET money = money + 5 WHERE user_id=?", (user_data[12],))
    
    conn.commit()
    await show_profile(message.from_user.id, message)

# --- ՊՐՈՖԻԼԻ ՑՈՒՑԱԴՐՈՒՄ ---
async def show_profile(user_id, message: types.Message):
    u = get_user(user_id)
    lang = u[2] if u[2] else 'am'
    
    vip_tag = "👑 VIP 👑\n" if u[9] else ""
    name_str = u[4].upper() if u[9] else u[4]
    
    profile_text = TEXTS[lang]['profile'].format(
        vip_tag=vip_tag, flag=u[3], name=name_str, gender=u[5], likes=u[8], money=u[7]
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['search'], callback_data="menu_search"),
         InlineKeyboardButton(text=TEXTS[lang]['edit'], callback_data="menu_edit")],
[InlineKeyboardButton(text=TEXTS[lang]['share'], callback_data="menu_share"),
         InlineKeyboardButton(text=TEXTS[lang]['game'], callback_data="menu_game")]
    ])
    
    await bot.send_photo(chat_id=user_id, photo=u[6], caption=profile_text, reply_markup=kb)

# --- ՊՐՈՖԻԼԻ ԳՈՐԾՈՂՈՒԹՅՈՒՆՆԵՐ ---
@dp.callback_query(F.data == "menu_share")
async def share_link(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={call.from_user.id}"
    await call.message.answer(f"🔄 Տարածիր այս հղումը ընկերներիդ շրջանում:\nԵրբ նրանք գրանցվեն, դու կստանաս 5 Money!\n\n👉 {link}")
    await call.answer()

@dp.callback_query(F.data == "menu_edit")
async def edit_profile_req(call: types.CallbackQuery):
    u = get_user(call.from_user.id)
    if u[9]: # VIP-ները անվճար են փոխում
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Փոխել (Անվճար VIP)", callback_data="pay_edit_free")]])
        await call.message.answer("Դուք ունեք VIP կարգավիճակ, կարող եք փոխել անվճար:", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Վճարել 100 ⭐️", callback_data="pay_edit_stars")],
            [InlineKeyboardButton(text="🔙 Հետ", callback_data="back_to_profile")]
        ])
        await call.message.answer("⚠️ Պրոֆիլը փոխելու համար անհրաժեշտ է վճարել 100 ⭐️ Stars:", reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data == "pay_edit_stars")
async def pay_edit_stars(call: types.CallbackQuery):
    await call.message.answer_invoice(
        title="Պրոֆիլի Փոփոխում",
        description="Ապահով վճարում տելեգրամի ներսում (100 Stars)",
        payload="edit_profile",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=100)]
    )
    await call.answer()

# --- ՈՐՈՆԵԼ ԸՆԿԵՐ (SEARCH) ---
@dp.callback_query(F.data == "menu_search")
async def search_friends(call: types.CallbackQuery):
    user_id = call.from_user.id
    u = get_user(user_id)
    
    # Գտնել պատահական գրանցված օգտատեր (բացի իրենից)
    cursor.execute("SELECT user_id FROM users WHERE user_id != ? AND photo_id IS NOT NULL", (user_id,))
    all_users = cursor.fetchall()
    
    if not all_users:
        await call.message.answer("Ցավոք դեռ գրանցված մարդիկ չկան։")
        await call.answer()
        return
        
    target_id = random.choice(all_users)[0]
    t = get_user(target_id)
    
    vip_tag = "👑 VIP 👑\n" if t[9] else ""
    text = f"{vip_tag}👤 Պրոֆիլ\n🎭 Անուն: {t[4]}\n⚧ Սեռ: {t[5]}\n❤️ Լայքեր: {t[8]}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Լայքել", callback_data=f"like_{target_id}"),
         InlineKeyboardButton(text="🤝 Ընկերանալ", callback_data=f"friend_{target_id}")],
        [InlineKeyboardButton(text="➡️ Հաջորդը", callback_data="menu_search")]
    ])
    
    await bot.send_photo(chat_id=user_id, photo=t[6], caption=text, reply_markup=kb)
    await call.answer()

# --- ԼԱՅՔԵԼ ԵՎ ԸՆԿԵՐԱՆԱԼ ---
@dp.callback_query(F.data.startswith("like_"))
async def like_user(call: types.CallbackQuery):
    target_id = int(call.data.split("_")[1])
    try:
        cursor.execute("INSERT INTO likes (from_id, to_id) VALUES (?, ?)", (call.from_user.id, target_id))
        cursor.execute("UPDATE users SET likes = likes + 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        await call.answer("❤️ Դուք լայքեցիք այս պրոֆիլը։")
    except sqlite3.IntegrityError:
        await call.answer("Դուք արդեն լայքել եք այս պրոֆիլին։", show_alert=True)

@dp.callback_query(F.data.startswith("friend_"))
async def friend_req(call: types.CallbackQuery):
    target_id = int(call.data.split("_")[1])
    u = get_user(call.from_user.id)
# Ուղարկել հարցումը թիրախին
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ընդունել", callback_data=f"accept_{call.from_user.id}"),
         InlineKeyboardButton(text="❌ Մերժել", callback_data="decline_req")]
    ])
    
    await bot.send_photo(chat_id=target_id, photo=u[6], caption=f"✨ Ձեզ ուզում են ընկերանալ!\nԼայքեր՝ {u[8]}", reply_markup=kb)
    await call.answer("🤝 Հարցումն ուղարկված է։")

@dp.callback_query(F.data.startswith("accept_"))
async def accept_friend(call: types.CallbackQuery):
    sender_id = int(call.data.split("_")[1])
    # Ստուգել Money
    u_accept = get_user(call.from_user.id)
    u_sender = get_user(sender_id)
    
    # Եթե VIP չէ, ապա ստուգում ենք Money
    if not u_accept[9] and u_accept[7] <= 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Բացել 5 ⭐️ Stars-ով", callback_data=f"pay_chat_{sender_id}")]])
        await call.message.answer("Չատը բացելու համար չունեք Money: Կարող եք բացել 5 Stars-ով.", reply_markup=kb)
        await call.answer()
        return

    if not u_accept[9]: # VIP-ից money չի տանում
        cursor.execute("UPDATE users SET money = money - 1 WHERE user_id=?", (call.from_user.id,))
    conn.commit()
    
    await bot.send_message(chat_id=sender_id, text="🎉 Ձեր հարցումն ընդունվել է: Չատը բաց է։")
    await call.message.answer("🎉 Դուք ընդունեցիք հարցումը: (Կարող եք խոսել բոտում):")
    await call.answer()

@dp.callback_query(F.data == "decline_req")
async def decline_friend(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Մերժված է։")

# --- MINI GAME (ՄԻՆԻ ԽԱՂ) ---
@dp.callback_query(F.data == "menu_game")
async def mini_game_start(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Դեմո (Անվճար)", callback_data="game_play_demo")],
        [InlineKeyboardButton(text="💸 Վճարովի (1 Star)", callback_data="game_pay_star")]
    ])
    await call.message.answer("🎮 Բարի գալուստ 16 Վանդակ խաղ։\nԿարող եք բացել 5 վանդակ։\n❌ - 70% | 💸 - 25% (+1 Money) | 💰 - 5% (+5 Money)", reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data == "game_pay_star")
async def game_pay(call: types.CallbackQuery):
    await call.message.answer_invoice(
        title="Մինի Խաղ", description="Մուտք խաղի մեջ (1 Star)", payload="play_game",
        provider_token="", currency="XTR", prices=[LabeledPrice(label="Star", amount=1)]
    )
    await call.answer()

@dp.callback_query(F.data.in_(["game_play_demo", "game_start_paid"]))
async def start_slots(call: types.CallbackQuery):
    # Ստեղծել 16 սպիտակ վանդակներով մատրիցա
    buttons = []
    for i in range(16):
        buttons.append(InlineKeyboardButton(text="⬜️", callback_data=f"grid_{i}_5")) # 5-ը մնացած քայլերն են
    
    # Դասավորել 4x4
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+4] for i in range(0, 16, 4)])
    await call.message.answer("🎯 Ընտրեք 5 վանդակներից որևէ մեկը.", reply_markup=keyboard)
    await call.answer()

@dp.callback_query(F.data.startswith("grid_"))
async def click_grid(call: types.CallbackQuery):
    data = call.data.split("_")
    index = int(data[1])
    clicks_left = int(data[2]) - 1
    
    # Հավանականության հաշվարկ
    rand = random.randint(1, 100)
    if rand <= 70:
        prize = "❌"
        msg = "Ոչինչ չշահեցիք"
    elif rand <= 95:
        prize = "💸"
        msg = "+1 Money 💸"
        cursor.execute("UPDATE users SET money = money + 1 WHERE user_id=?", (call.from_user.id,))
    else:
        prize = "💰"
        msg = "+5 Money 💰"
        cursor.execute("UPDATE users SET money = money + 5 WHERE user_id=?", (call.from_user.id,))
    conn.commit()
    
    await call.answer(msg, show_alert=True)
    
    # Թարմացնել կոճակները
    current_markup = call.message.reply_markup.inline_keyboard
    flat_list = [item for sublist in current_markup for item in sublist]
    
     if clicks_left > 0:
         flat_list[index] = InlineKeyboardButton(text=prize, callback_data="disabled")
         # Մնացած բոլոր սպիտակների click_left-ը թարմացնել
        for btn in flat_list:
            if btn.callback_data.startswith("grid_"):
                idx = btn.callback_data.split("_")[1]
                btn.callback_data = f"grid_{idx}_{clicks_left}"
        
        new_kb = InlineKeyboardMarkup(inline_keyboard=[flat_list[i:i+4] for i in range(0, 16, 4)])
        await call.message.edit_reply_markup(reply_markup=new_kb)
    else:
        await call.message.answer("🎮 Խաղն ավարտվեց։")
        await call.message.delete()

# --- ԱՆԱՆՈՒՆ ՆԱՄԱԿ ԱԴՄԻՆԻՆ ---
@dp.message(F.text.in_([TEXTS[l]['anon_msg'] for l in TEXTS]))
async def anon_msg_start(message: types.Message, state: FSMContext):
    await message.answer("Գրեք Ձեր նամակը, այն անանուն կուղարկվի ադմինին:")
    await state.set_state(AnonStates.msg)

@dp.message(AnonStates.msg)
async def anon_msg_send(message: types.Message, state: FSMContext):
    await state.clear()
    # Ադմինը տեսնում է ամեն ինչ
    admin_text = f"🚨 ԱՆԱՆՈՒՆ ՆԱՄԱԿ\n👤 User ID: {message.from_user.id}\n🎭 Username: @{message.from_user.username}\n\n📝 Նամակ՝ {message.text}"
    await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
    await message.answer("✅ Ձեր նամակը հաջողությամբ ուղարկվեց։")

# --- ԱԴՄԻՆԻ ՀՐԱՄԱՆՆԵՐ (ADMIN PANEL) ---
@dp.message(Command("free")) # /free [user_id] [days]
async def admin_free(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    
    target_id, days = int(args[1]), int(args[2])
    until_date = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute("UPDATE users SET free_until=? WHERE user_id=?", (until_date, target_id))
    conn.commit()
    
    await message.answer("✅ Ֆունկցիան ակտիվացված է:")
    await bot.send_message(chat_id=target_id, text=f"🎉 Շնորհավորում եմ! Դուք ադմինի կողմից {days} օր ստացաք անվճար ֆունկցիա։")

@dp.message(Command("addmoney")) # /addmoney [user_id] [amount]
async def admin_addmoney(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    
    target_id, amount = int(args[1]), int(args[2])
    cursor.execute("UPDATE users SET money = money + ? WHERE user_id=?", (amount, target_id))
    conn.commit()
    await message.answer(f"✅ {amount} money ուղարկվեց ID {target_id}-ին։")

@dp.message(Command("vip")) # /vip [user_id]
async def admin_vip(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    
    target_id = int(args[1])
    until_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute("UPDATE users SET is_vip=1, vip_until=? WHERE user_id=?", (until_date, target_id))
    conn.commit()
    await message.answer("✅ VIP-ը ակտիվացվեց։")

# --- ՎՃԱՐՄԱՆ ՍՏՈՒԳՈՒՄ (TELEGRAM STARS PRE-CHECKOUT) ---
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: types.Message, state: FSMContext):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    
    if payload.startswith("donate_"):
        await message.answer("❤️ Շնորհակալություն դոնատի համար։ Ադմինը ստացավ աստղերը։")
    elif payload == "edit_profile":
        await message.answer("✅ Վճարումը հաջողվեց։ Այժմ կարող եք զրոյից գրանցվել։")
await state.set_state(RegStates.flag)
        await message.answer(TEXTS['am']['step1'])
    elif payload == "play_game":
        # Ուղարկել խաղի դաշտը որպես վճարված
        buttons = [InlineKeyboardButton(text="⬜️", callback_data=f"grid_{i}_5") for i in range(16)]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+4] for i in range(0, 16, 4)])
        await message.answer("🎯 Վճարովի խաղը սկսվեց! Ընտրեք 5 վանդակ.", reply_markup=keyboard)

# --- ԲՈՏԻ ՄԻԱՑՈՒՄ ---
async def main():
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
