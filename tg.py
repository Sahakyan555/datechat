import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
ReplyKeyboardMarkup, KeyboardButton,
InlineKeyboardMarkup, InlineKeyboardButton,
LabeledPrice, PreCheckoutQuery
)

--- ԲՈՏԻ ՏՎՅԱԼՆԵՐԸ ---
BOT_TOKEN = "8834098974:AAG-O0bKfyMdLC45sy4H8axWNkyU9OHKkOw" # Տեղադրիր BotFather-ից ստացված տոկենը
PROVIDER_TOKEN = "" # Telegram Stars-ի համար սա թողնում ենք դատարկ
ADMIN_ID = 6614409372

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

--- ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ (Ժամանակավոր՝ հիշողության մեջ) ---
USERS_DB = {} # user_id: {profile_data}
CHATS = {} # user_id: active_chat_partner_id
REQUESTS = {} # user_id: pending_request_from_id

--- 15 ԼԵԶՈՒՆԵՐԻ ԹԱՐԳՄԱՆՈՒԹՅՈՒՆՆԵՐԸ ---
LANG_MAP = {
"🇦🇲": "hy", "🇨🇮": "fr_ci", "🇫🇷": "fr", "🇷🇺": "ru", "🇺🇲": "en",
"🇮🇷": "fa", "🇪🇪": "et", "🇦🇫": "ps", "🇦🇷": "es", "🇬🇪": "ka",
"🇮🇳": "hi", "🇸🇦": "ar", "🇹🇷": "tr", "🇵🇦": "es_pa", "🇳🇵": "ne"
}

TEXTS = {
"hy": {
"welcome": "Ողջույն! Խնդրում եմ ընտրել լեզուն:", "register": "Գրանցվել", "gender": "Ընտրեք ձեր սեռը:",
"male": "Տղա", "female": "Աղջիկ", "other": "Այլ", "age": "Ընտրեք ձեր տարիքը:",
"height": "Գրեք ձեր հասակը (ձեռքով):", "hair": "Ընտրեք մազերի գույնը:", "eyes": "Ընտրեք աչքերի գույնը:",
"flag": "Ուղարկեք ձեր երկրի դրոշը (ձեռքով):", "photo": "Ուղարկեք նկար անանուն էջի համար:",
"main_menu": "Գլխավոր Մենյու", "edit_profile": "Փոխել էջը", "find_friend": "Փնտրել ընկեր",
"blocks": "Բլոկների ցուցակ", "profile_view": "Էջը հաջողությամբ ստեղծվեց!\n\nՍեռ: {g}\nՏարիք: {a}\nՀասակ: {h}\nՄազեր: {hr}\nԱչքեր: {e}\nԴրոշ: {f}",
"no_users": "Առայժմ այլ օգտատերեր չկան:", "like": "👍 Հավանել", "block_btn": "🚫 Բլոկել",
"req_sent": "Հարցումն ուղարկված է:", "new_req": "Ձեզ հավանել են! Ընդունո՞ւմ եք:",
"accept": "✅ Ընդունել", "decline": "❌ Մերժել", "chat_start": "Չատը սկսվեց! Գրեք հաղորդագրություն...",
"chat_end": "Չատն ավարտվեց:", "unblock": "Հանել բլոկից", "pay_stars_3": "3 անվճար լիմիտը սպառվել է: Մեկ հոգու հետ ծանոթանալու համար վճարեք 5 Stars:",
"pay_stars_edit": "Էջը երկրորդ անգամ փոխելու համար անհրաժեշտ է վճարել 100 Stars:"
},
"en": {
"welcome": "Welcome! Please choose your language:", "register": "Register", "gender": "Choose your gender:",
"male": "Male", "female": "Female", "other": "Other", "age": "Choose your age:",
"height": "Type your height:", "hair": "Choose hair color:", "eyes": "Choose eye color:",
"flag": "Send your country flag:", "photo": "Send a photo for your anonymous profile:",
"main_menu": "Main Menu", "edit_profile": "Change profile", "find_friend": "Find a friend",
"blocks": "Blocklist", "profile_view": "Profile created!\n\nGender: {g}\nAge: {a}\nHeight: {h}\nHair: {hr}\nEyes: {e}\nFlag: {f}",
"no_users": "No other users found.", "like": "👍 Like", "block_btn": "🚫 Block",
"req_sent": "Request sent!", "new_req": "Someone liked you! Accept?",
"accept": "✅ Accept", "decline": "❌ Decline", "chat_start": "Chat started! Type a message...",
"chat_end": "Chat ended.", "unblock": "Unblock", "pay_stars_3": "Free limit reached. Pay 5 Stars to connect:",
"pay_stars_edit": "To change profile again, pay 100 Stars:"
},
"ru": {
"welcome": "Добро пожаловать! Выберите язык:", "register": "Зарегистрироваться", "gender": "Выберите пол:",
"male": "Мужчина", "female": "Женщина", "other": "Другое", "age": "Выберите возраст:",
"height": "Введите ваш рост:", "hair": "Выберите цвет волос:", "eyes": "Выберите цвет глаз:",
"flag": "Отправьте флаг вашей страны:", "photo": "Отправьте фото для анонимного профиля:",
"main_menu": "Главное меню", "edit_profile": "Изменить профиль", "find_friend": "Найти друга",
"blocks": "Черный список", "profile_view": "Профиль создан!\n\nПол: {g}\nВозраст: {a}\nРост: {h}\nВолосы: {hr}\nГлаза: {e}\nФлаг: {f}",
"no_users": "Других пользователей пока нет.", "like": "👍 Лайк", "block_btn": "🚫 Блок",
"req_sent": "Запрос отправлен!", "new_req": "Вы понравились кому-то! Принять?",
"accept": "✅ Принять", "decline": "❌ Отклонить", "chat_start": "Чат начат! Напишите сообщение...",
"chat_end": "Чат окончен.", "unblock": "Разблокировать", "pay_stars_3": "Лимит исчерпан. Платите 5 Stars за знакомство:",
"pay_stars_edit": "Для повторного изменения профиля оплатите 100 Stars:"
},
"fr": {
"welcome": "Bienvenue! Choisissez votre langue:", "register": "S'inscrire", "gender": "Choisissez votre genre:",
"male": "Homme", "female": "Femme", "other": "Autre", "age": "Choisissez votre âge:",
"height": "Entrez votre taille:", "hair": "Couleur des cheveux:", "eyes": "Couleur des yeux:",
"flag": "Envoyez votre drapeau:", "photo": "Envoyez une photo:",
"main_menu": "Menu Principal", "edit_profile": "Modifier le profil", "find_friend": "Trouver un ami",
"blocks": "Liste noire", "profile_view": "Profil créé!", "no_users": "Aucun utilisateur trouvé.",
"like": "👍 Liker", "block_btn": "🚫 Bloquer", "req_sent": "Demande envoyée!", "new_req": "Quelqu'un vous aime! Accepter?",
"accept": "✅ Accepter", "decline": "❌ Décliner", "chat_start": "Chat commencé...", "chat_end": "Chat terminé.",
"unblock": "Débloquer", "pay_stars_3": "Payez 5 Stars:", "pay_stars_edit": "Payez 100 Stars:"
}
}

Լրացնենք մնացած լեզուները անգլերենով որպես դեֆոլտ, որպեսզի կոդը հսկայական չլինի, բայց բոլոր 15-ն էլ աշխատեն
for l_flag, l_code in LANG_MAP.items():
if l_code not in TEXTS:
TEXTS[l_code] = TEXTS["en"].copy()

def get_txt(uid, key):
lang = USERS_DB.get(uid, {}).get("lang", "en")
return TEXTS.get(lang, TEXTS["en"]).get(key, key)

--- FSM STATES ---
class RegStates(StatesGroup):
lang = State()
gender = State()
age = State()
height = State()
hair = State()
eyes = State()
flag = State()
photo = State()

--- START & ԼԵԶՎԻ ԸՆՏՐՈՒԹՅՈՒՆ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
buttons = [[InlineKeyboardButton(text=flag, callback_data=f"lang_{flag}")] for flag in LANG_MAP.keys()]
keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
await message.answer("🇦🇲 Ընտրեք լեզուն / Choose language / Выберите язык:", reply_markup=keyboard)
await state.set_state(RegStates.lang)

@dp.callback_query(F.data.startswith("lang_"), RegStates.lang)
async def set_language(callback: types.CallbackQuery, state: FSMContext):
flag = callback.data.split("_")[1]
lang_code = LANG_MAP[flag]

if callback.from_user.id not in USERS_DB:
    USERS_DB[callback.from_user.id] = {"free_chats": 3, "edit_count": 0, "blocks": [], "liked_by": []}
USERS_DB[callback.from_user.id]["lang"] = lang_code
reg_btn = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=get_txt(callback.from_user.id, "register"))]], resize_keyboard=True)
await callback.message.answer(get_txt(callback.from_user.id, "welcome"), reply_markup=reg_btn)
await callback.answer()
--- ԳՐԱՆՑՄԱՆ ՓՈՒԼԵՐ ---
@dp.message(F.text.in_([TEXTS[l]["register"] for l in TEXTS]))
async def start_reg(message: types.Message, state: FSMContext):
uid = message.from_user.id
# Ստուգում ենք՝ արդեն երկրորդ անգամ է փոխում, թե ոչ
if USERS_DB.get(uid, {}).get("edit_count", 0) >= 1:
# Պահանջել 100 Stars
await message.answer(get_txt(uid, "pay_stars_edit"))
await bot.send_invoice(
chat_id=uid, title="Change Profile", description="Pay 100 Stars to edit your profile",
payload="edit_profile_pay", provider_token=PROVIDER_TOKEN, currency="XTR",
prices=[LabeledPrice(label="100 Stars", amount=100)]
)
return

await ask_gender(message, state)
async def ask_gender(message: types.Message, state: FSMContext):
uid = message.from_user.id
kb = ReplyKeyboardMarkup(keyboard=[
[KeyboardButton(text=get_txt(uid, "male")), KeyboardButton(text=get_txt(uid, "female")), KeyboardButton(text=get_txt(uid, "other"))]
], resize_keyboard=True)
await message.answer(get_txt(uid, "gender"), reply_markup=kb)
await state.set_state(RegStates.gender)

@dp.message(RegStates.gender)
async def process_gender(message: types.Message, state: FSMContext):
await state.update_data(gender=message.text)
uid = message.from_user.id
kb = ReplyKeyboardMarkup(keyboard=[
[KeyboardButton(text="12-15"), KeyboardButton(text="16-18")],
[KeyboardButton(text="19-25"), KeyboardButton(text="25+")]
], resize_keyboard=True)
await message.answer(get_txt(uid, "age"), reply_markup=kb)
await state.set_state(RegStates.age)

@dp.message(RegStates.age)
async def process_age(message: types.Message, state: FSMContext):
await state.update_data(age=message.text)
await message.answer(get_txt(message.from_user.id, "height"), reply_markup=types.ReplyKeyboardRemove())
await state.set_state(RegStates.height)

@dp.message(RegStates.height)
async def process_height(message: types.Message, state: FSMContext):
await state.update_data(height=message.text)
uid = message.from_user.id
kb = ReplyKeyboardMarkup(keyboard=[
[KeyboardButton(text="🔴"), KeyboardButton(text="🟠"), KeyboardButton(text="🟡"), KeyboardButton(text="🟢")],
[KeyboardButton(text="🔵"), KeyboardButton(text="🟣"), KeyboardButton(text="🟤"), KeyboardButton(text="⚪️"), KeyboardButton(text="⚫️")]
], resize_keyboard=True)
await message.answer(get_txt(uid, "hair"), reply_markup=kb)
await state.set_state(RegStates.hair)

@dp.message(RegStates.hair)
async def process_hair(message: types.Message, state: FSMContext):
await state.update_data(hair=message.text)
uid = message.from_user.id
kb = ReplyKeyboardMarkup(keyboard=[
[KeyboardButton(text="⚪️"), KeyboardButton(text="⚫️"), KeyboardButton(text="🟤"), KeyboardButton(text="🟣")],
[KeyboardButton(text="🔵"), KeyboardButton(text="🟢"), KeyboardButton(text="🟡"), KeyboardButton(text="🟠"), KeyboardButton(text="🔴")]
], resize_keyboard=True)
await message.answer(get_txt(uid, "eyes"), reply_markup=kb)
await state.set_state(RegStates.eyes)

@dp.message(RegStates.eyes)
async def process_eyes(message: types.Message, state: FSMContext):
await state.update_data(eyes=message.text)
await message.answer(get_txt(message.from_user.id, "flag"), reply_markup=types.ReplyKeyboardRemove())
await state.set_state(RegStates.flag)

@dp.message(RegStates.flag)
async def process_flag(message: types.Message, state: FSMContext):
await state.update_data(flag=message.text)
await message.answer(get_txt(message.from_user.id, "photo"))
await state.set_state(RegStates.photo)

@dp.message(RegStates.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
photo_id = message.photo[-1].file_id
data = await state.get_data()
uid = message.from_user.id

USERS_DB[uid].update({
    "gender": data["gender"], "age": data["age"], "height": data["height"],
    "hair": data["hair"], "eyes": data["eyes"], "flag": data["flag"], "photo": photo_id
})
USERS_DB[uid]["edit_count"] += 1
await state.clear()
await show_main_menu(message.chat.id, uid)
--- ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ ---
async def show_main_menu(chat_id, uid):
kb = InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=get_txt(uid, "edit_profile"), callback_data="menu_edit")],
[InlineKeyboardButton(text=get_txt(uid, "find_friend"), callback_data="menu_find")],
[InlineKeyboardButton(text=get_txt(uid, "blocks"), callback_data="menu_blocks")]
])
u = USERS_DB[uid]
text = get_txt(uid, "profile_view").format(g=u['gender'], a=u['age'], h=u['height'], hr=u['hair'], e=u['eyes'], f=u['flag'])
await bot.send_photo(chat_id, photo=u["photo"], caption=text, reply_markup=kb)

@dp.callback_query(F.data == "menu_edit")
async def inline_edit_profile(callback: types.CallbackQuery, state: FSMContext):
await callback.answer()
await ask_gender(callback.message, state)
--- ՓՆՏՐԵԼ ԸՆԿԵՐ ---
@dp.callback_query(F.data == "menu_find")
async def inline_find_friend(callback: types.CallbackQuery):
uid = callback.from_user.id
found = False

for target_id, data in USERS_DB.items():
    if target_id != uid and "photo" in data:
        if target_id in USERS_DB[uid].get("blocks", []) or uid in USERS_DB[target_id].get("blocks", []):
            continue
        
        found = True
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_txt(uid, "like"), callback_data=f"like_{target_id}")],
            [InlineKeyboardButton(text=get_txt(uid, "block_btn"), callback_data=f"block_{target_id}")]
        ])
        text = get_txt(uid, "profile_view").format(g=data['gender'], a=data['age'], h=data['height'], hr=data['hair'], e=data['eyes'], f=data['flag'])
        await bot.send_photo(uid, photo=data["photo"], caption=text, reply_markup=kb)
        break
        
if not found:
    await callback.message.answer(get_txt(uid, "no_users"))
await callback.answer()
--- ԼԱՅՔ ԵՎ ԲԼՈԿ ---
@dp.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery):
uid = callback.from_user.id
target_id = int(callback.data.split("_")[1])

# Ստուգում ենք վճարովի լիմիտը (3 անվճար հոգի)
if USERS_DB[uid]["free_chats"] <= 0:
    await callback.message.answer(get_txt(uid, "pay_stars_3"))
    await bot.send_invoice(
        chat_id=uid, title="Connect Friend", description="Pay 5 Stars to connect with this user",
        payload=f"pay_connect_{target_id}", provider_token=PROVIDER_TOKEN, currency="XTR",
        prices=[LabeledPrice(label="5 Stars", amount=5)]
    )
    await callback.answer()
    return
await send_chat_request(uid, target_id)
await callback.message.answer(get_txt(uid, "req_sent"))
await callback.answer()
async def send_chat_request(from_uid, to_uid):
REQUESTS[to_uid] = from_uid
kb = InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=get_txt(to_uid, "accept"), callback_data="chat_accept"),
InlineKeyboardButton(text=get_txt(to_uid, "decline"), callback_data="chat_decline")]
])
await bot.send_message(to_uid, get_txt(to_uid, "new_req"), reply_markup=kb)

--- ՉԱՏԻ ԸՆԴՈՒՆՈՒՄ / ՄԵՐԺՈՒՄ ---
@dp.callback_query(F.data == "chat_accept")
async def chat_accept(callback: types.CallbackQuery):
uid = callback.from_user.id
sender_id = REQUESTS.get(uid)
if sender_id:
CHATS[uid] = sender_id
CHATS[sender_id] = uid
USERS_DB[sender_id]["free_chats"] -= 1 # Պակասեցնում ենք լիմիտը

    await bot.send_message(uid, get_txt(uid, "chat_start"))
    await bot.send_message(sender_id, get_txt(sender_id, "chat_start"))
    del REQUESTS[uid]
await callback.answer()
@dp.callback_query(F.data == "chat_decline")
async def chat_decline(callback: types.CallbackQuery):
uid = callback.from_user.id
if uid in REQUESTS:
del REQUESTS[uid]
await callback.message.delete()
await callback.answer()

--- ՉԱՏԱՎՈՐՈՒՄ (ՄԵՍԻՋՆԵՐԻ ՓՈԽԱՆՑՈՒՄ) ---
@dp.message(F.text & ~F.text.startswith("/"))
async def text_chat_router(message: types.Message):
uid = message.from_user.id
if uid in CHATS:
partner_id = CHATS[uid]
await bot.send_message(partner_id, message.text)

--- ԲԼՈԿԱՎՈՐՈՒՄ ---
@dp.callback_query(F.data.startswith("block_"))
async def block_user(callback: types.CallbackQuery):
uid = callback.from_user.id
target_id = int(callback.data.split("_")[1])
if target_id not in USERS_DB[uid]["blocks"]:
USERS_DB[uid]["blocks"].append(target_id)
# Կտրել չատը եթե կա
if CHATS.get(uid) == target_id or CHATS.get(target_id) == uid:
CHATS.pop(uid, None)
CHATS.pop(target_id, None)
await callback.answer("Blocked")

@dp.callback_query(F.data == "menu_blocks")
async def show_blocks(callback: types.CallbackQuery):
uid = callback.from_user.id
blocks = USERS_DB[uid].get("blocks", [])
if not blocks:
await callback.message.answer("Ձեր բլոկ լիստը դատարկ է:")
await callback.answer()
return
for b_id in blocks:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_txt(uid, "unblock"), callback_data=f"unblock_{b_id}")]
    ])
    await callback.message.answer(f"Օգտատեր ID: {b_id}", reply_markup=kb)
await callback.answer()
@dp.callback_query(F.data.startswith("unblock_"))
async def unblock_user(callback: types.CallbackQuery):
uid = callback.from_user.id
target_id = int(callback.data.split("_")[1])
if target_id in USERS_DB[uid]["blocks"]:
USERS_DB[uid]["blocks"].remove(target_id)
await callback.message.delete()
await callback.answer("Unblocked")

--- TELEGRAM STARS ՎՃԱՐՈՒՄՆԵՐԻ ՄՇԱԿՈՒՄ ---
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: types.Message, state: FSMContext):
uid = message.from_user.id
payload = message.successful_payment.invoice_payload

if payload == "edit_profile_pay":
    USERS_DB[uid]["edit_count"] = 0 # Զրոյացնում ենք, որ թույլ տա փոխել
    await ask_gender(message, state)
elif payload.startswith("pay_connect_"):
    target_id = int(payload.split("_")[2])
    await send_chat_request(uid, target_id)
    await message.answer(get_txt(uid, "req_sent"))
--- ԱՇԽԱՏԵՑՆԵԼ ԲՈՏԸ ---
async def main():
await dp.start_polling(bot)

if name == "main":
import asyncio
asyncio.run(main())։
Այս կոդը ավելացրու տելեգևամ բոտին գեղեցիկ էմոջիներով
