import asyncio
import logging
import os

import pymongo
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.types.input_media import InputMedia
from aiogram.types.update import Update
from pymongo import ReturnDocument


# This function initializes the database connection and returns the collection object for further use.
def initDB():
    myclient = pymongo.MongoClient()
    mydb = myclient["papergardener_db"]

    mycol = mydb["catalogue"]
    mycol1 = mydb["orders"]

    myItems = [{"_id": "A111A1", "name": "Кеди converse оригінал", "size": "36.5 / 23 см", "price": "300",
                "availability": False},
               {"_id": "A111A2", "name": "Шорти pull&bear", "size": "S/M", "price": "80",
                "availability": True},
               {"_id": "A111A3", "name": "Довгі скінні джинси в стилі y2k", "size": "XS", "price": "150",
                "availability": True},
               {"_id": "A111A4", "name": "Рожевий кроп топ", "size": "S", "price": "90",
                "availability": True},
               {"_id": "A111A5", "name": "Бежева панама", "size": "-", "price": "200",
                "availability": True},
               {"_id": "A111A6", "name": "Білий топ edc beach club", "size": "S", "price": "95",
                "availability": True},
               {"_id": "A111A7", "name": "Ніжно-рожева майка за мереживом", "size": "S/M", "price": "135",
                "availability": True},
               {"_id": "A111A8", "name": "Біле поло h&m", "size": "S", "price": "135",
                "availability": True},
               {"_id": "A111A9", "name": "Лавандовий топ з буфами", "size": "XS", "price": "210",
                "availability": True},
               {"_id": "A112A1", "name": "Червоний топ на завʼязках", "size": "S", "price": "130",
                "availability": True},
               {"_id": "A112A2", "name": "Молочний топ h&m новий", "size": "S", "price": "250",
                "availability": True},
               {"_id": "A112A3", "name": "Чорна кофтинка в рубчик monki", "size": "S", "price": "180",
                "availability": True},
               {"_id": "A112A4", "name": "Джинсова міді спідниця", "size": "S", "price": "180",
                "availability": True},
               {"_id": "A112A5", "name": "Зелена майка з мереживом", "size": "XS/S", "price": "165",
                "availability": True}
               ]

    myOrders = [{"order_id": "1", "items_id": ["A111A1"], "customer_info": "Софія Боклан, Київ, 304",
                 "username": "sofiiaboklan", "order_status": "Очікує підтвердження оплати.", "order_complete": False}]

    mycol.drop()
    mycol1.drop()
    if mycol.estimated_document_count() == 0:
        mycol.insert_many(myItems)

    if mycol1.estimated_document_count() == 0:
        mycol1.insert_many(myOrders)

    return mycol, mycol1


# creates and returns a custom keyboard
def init_keyboard():
    button_order = KeyboardButton(text="\U0001f6cd\uFE0FЗробити замовлення\U0001f6cd\uFE0F")
    button_track_order = KeyboardButton(text="\u23F3Статус замовлення\u23F3")
    button_admin = KeyboardButton(text="\U0001f4deЗвʼязатися з нами\U0001f4de")
    button_cart = KeyboardButton(text="\U0001f6d2Мій кошик\U0001f6d2")
    keyboard = ReplyKeyboardMarkup(keyboard=[[button_order], [button_cart], [button_track_order], [button_admin]],
                                   resize_keyboard=True, row_width=1, is_persistent=True)

    return keyboard


# Bot token can be obtained via https://t.me/BotFather
TOKEN = "6157897368:AAH00AiVBg7TJMmYEjXWqu_LyQ3rDnfbn5M"

# All handlers should be attached to the Router/Dispatcher. It creates an instance of the Router class from aiogram.
router = Router()

# a variable to initialize the database connection and returns the collection object for further use.
itemsCollection, ordersCollection = initDB()

my_cart = []


async def get_photos(code: str):
    directory_path = f'resources/{code}'

    photo_codes = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

    photos = []

    for photo in photo_codes:
        photos.append(InputMediaPhoto(media=FSInputFile(f"{directory_path}/{photo}")))

    return photos


class MyCallback(CallbackData, prefix="my"):
    code: str
    code = None
    state: str


# state is entering, ordering, menu
class Form(StatesGroup):
    put_code = State()
    put_personal_data = State()


@router.callback_query(MyCallback.filter(F.state == "cart"))
async def order_callback_foo(query: CallbackQuery):
    my_cart.append(query.data.split(':')[1])
    builder = InlineKeyboardBuilder()
    builder.button(text="Перейти до оплати", callback_data=MyCallback(state="ordering").pack())
    builder.button(text="Додати ще одну річ в кошик", callback_data=MyCallback(state="entering").pack())
    builder.adjust(1, 2)
    await query.message.answer("Річ додано в кошик! \U0001f90d", reply_markup=builder.as_markup())


@router.callback_query(MyCallback.filter(F.state == "entering"))
async def my_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.set_state(Form.put_code)
    await query.message.answer("Введіть артикль речі \u2B07\uFE0F")


@router.callback_query(MyCallback.filter(F.state == "menu"))
async def my_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await echo_handler(query.message)


@router.callback_query(MyCallback.filter(F.state == "ordering"))
async def order_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.set_state(Form.put_personal_data)
    if len(query.data.split(':')[1]) != 0:
        await state.update_data(put_code=query.data.split(':')[1])
    await query.message.answer("<b>Реквізити для оплати:</b> \nОтримувач: Боклан Софія\nМонобанк: 4441 1144 2342 3837"
                               "\n\n\U0001f90d\n\nПісля цього напишіть, будь ласка, "
                               "свої <b>реквізити для відправлення</b> у форматі:"
                               "\nПІБ, номер телефону, місто, номер відділення нової пошти.")


@router.message(Form.put_personal_data)
async def put_personal_data_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    personal_info = message.text
    if data.keys().__contains__("put_code"):
        item_id = data['put_code']
        items_id = [item_id]
        itemsCollection.find_one_and_update({'_id': item_id}, {'$set': {"availability": False}})
        if my_cart.__contains__(item_id):
            my_cart.remove(item_id)
    else:
        items_id = my_cart.copy()
        for item_id in my_cart:
            itemsCollection.find_one_and_update({'_id': item_id}, {'$set': {"availability": False}})
        my_cart.clear()

    order = {"order_id": ordersCollection.estimated_document_count() + 1, "items_id": items_id,
             "customer_info": personal_info,
             "username": message.from_user.username, "order_status": "Очікує підтвердження оплати.",
             "order_complete": False}

    ordersCollection.insert_one(order)

    builder = InlineKeyboardBuilder()
    builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
    builder.adjust(1, 2)
    await message.answer("Дякуємо! Очікуйте на підтвердження замовлення протягом доби \U0001f90d",
                         reply_markup=builder.as_markup())

    await state.clear()


@router.message(Form.put_code)
async def put_code_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(put_code=message.text)
    code = message.text
    myquery = {"_id": code}
    item = itemsCollection.find_one(myquery)

    if item is None:
        await message.answer(f"Ми не знайшли речі за таким артиклем \U0001f494 \nПереконайтесь, що ввели "
                             f"його правильно, наприклад <b>А111А1</b>")
    else:
        if item["availability"] is False:
            builder = InlineKeyboardBuilder()
            builder.button(text="Так", callback_data=MyCallback(state="entering").pack())
            builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
            builder.adjust(1, 2)
            await message.answer("Ця річ більше не в наявності \U0001f494\nБажаєте придбати іншу річ?",
                                 reply_markup=builder.as_markup())
        else:
            builder = InlineKeyboardBuilder()
            if not my_cart.__contains__(code):
                builder.button(text="Додати в кошик", callback_data=MyCallback(state="cart", code=code).pack())
            builder.button(text="Придбати зараз", callback_data=MyCallback(state="ordering", code=code).pack())
            builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
            builder.adjust(1, 2)

            photos = await get_photos(code)
            await message.answer_media_group(media=photos)
            # await message.answer_photo(photo=FSInputFile('resources/A111A1'), caption="Here is a photo!")
            await message.answer(item["name"] +
                                 "\n\n" +
                                 item["price"] +
                                 " грн" +
                                 "\n\n" +
                                 item["_id"], reply_markup=builder.as_markup())
            await state.clear()


@router.message(F.text == '\U0001f6cd\uFE0FЗробити замовлення\U0001f6cd\uFE0F')
async def command_place_order_handler(message: Message) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="Ввести артикль речі", callback_data=MyCallback(state="entering").pack())
    builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
    builder.adjust(1, 2)
    await message.answer("\u2B07\uFE0F \u2B07\uFE0F \u2B07\uFE0F", reply_markup=builder.as_markup())


@router.message(F.text == '\U0001f4deЗвʼязатися з нами\U0001f4de')
async def command_contact_handler(message: Message) -> None:
    await message.answer(text="<b>Контакти адміністраторки:</b>\n@sofiiaboklan / +380663343593. "
                              "\n\n<b>Робочі години</b>:\n10:00-20:00"
                              "\n\n\U0001f90d")


@router.message(F.text == '\u23F3Статус замовлення\u23F3')
async def command_status_handler(message: Message) -> None:
    myquery = {"username": message.from_user.username}
    orders = ordersCollection.find(myquery)
    response = ""
    try:
        while True:
            order = orders.next()
            order_items = ', '.join(order['items_id'])
            response += f"<b>Номер замовлення: {order['order_id']}</b>. \n<b>Статус:</b> {order['order_status']}" \
                        f"\n<b>Замовлення:</b> {order_items}\n" \
                        f"<b>Реквізити для відправки:</b> {order['customer_info']}.\n\n"
    except StopIteration:
        if response == "":
            response = "Ви ще не зробили жодного замовлення \U0001f494"
        await message.answer(text=response)


@router.message(F.text == '\U0001f6d2Мій кошик\U0001f6d2')
async def command_status_handler(message: Message) -> None:
    items = []
    for item_id in my_cart:
        myquery = {"_id": item_id}
        items.append(itemsCollection.find_one(myquery))

    response = ""

    for item in items:
        response += f"Артикль: {item['_id']}, {item['name']}\n\n"
    if response == "":
        await message.answer(text='Ваш кошик пустий \U0001f494')
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="Перейти до оплати", callback_data=MyCallback(state="ordering").pack())
        builder.button(text="Додати ще одну річ в кошик", callback_data=MyCallback(state="entering").pack())
        builder.adjust(1, 2)
        await message.answer(text=response, reply_markup=builder.as_markup())


# message here is a message, sent by user, overall message
@router.message()
async def echo_handler(message: types.Message) -> None:
    keyboard = init_keyboard()
    await message.answer(f"\U0001f90d \U0001f90d \U0001f90d \U0001f90d", reply_markup=keyboard)


# do not touch
async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)

    bot = Bot(TOKEN, parse_mode="HTML")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
