import asyncio
import logging

import pymongo
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.types.update import Update
from pymongo import ReturnDocument


# This function initializes the database connection and returns the collection object for further use.
def initDB():
    myclient = pymongo.MongoClient()
    mydb = myclient["papergardener_db"]

    mycol = mydb["catalogue"]
    mycol1 = mydb["orders"]

    myItems = [{"_id": "A111A1", "name": "Кеди converse оригінал", "size": "36.5 / 23 см", "price": "300",
                "availability": True},
               {"_id": "A111A2", "name": "Чорний кроп-топ", "size": "S", "price": "150",
                "availability": False},
               {"_id": "A111A3", "name": "Чорний кроп-топ", "size": "S", "price": "150",
                "availability": True}
               ]

    myOrders = [{"order_id": "1", "items_id": ["A111A2"], "customer_info": "Софія Боклан, Київ, 304",
                 "username": "sofiiaboklaan", "order_status": "Очікує підтвердження оплати.", "order_complete": False}]

    mycol.drop()
    mycol1.drop()
    if mycol.estimated_document_count() == 0:
        mycol.insert_many(myItems)

    if mycol1.estimated_document_count() == 0:
        mycol1.insert_many(myOrders)

    return mycol, mycol1


# creates and returns a custom keyboard
def init_keyboard():
    button_order = KeyboardButton(text="Зробити замовлення")
    button_track_order = KeyboardButton(text="Статус замовлення")
    button_admin = KeyboardButton(text="Звʼязатися з нами")
    button_cart = KeyboardButton(text="Мій кошик")
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


# initial command ("/start"), sends a greeting message to the user and initializes a custom keyboard
# @router.message(Command(commands=["start"]))
# async def command_start_handler(message: Message) -> None:
#     # Most event objects have aliases for API methods that can be called in events' context
#     # For example if you want to answer to incoming message you can use `message.answer(...)` alias
#     # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
#     # method automatically or call API method directly via
#     # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
#     keyboard = init_keyboard()
#     await message.answer(f"\U0001f90d \U0001f90d \U0001f90d \U0001f90d", reply_markup=keyboard)


class MyCallback(CallbackData, prefix="my"):
    code: str
    code = None
    state: str


# state is entering, ordering, menu


class Form(StatesGroup):
    put_code = State()
    put_personal_data = State()


@router.callback_query(MyCallback.filter(F.state == "cart"))
async def order_callback_foo(query: CallbackQuery, state: FSMContext):
    my_cart.append(query.data.split(':')[1])
    builder = InlineKeyboardBuilder()
    builder.button(text="Перейти до оплати", callback_data=MyCallback(state="ordering").pack())
    builder.button(text="Додати ще одну річ в кошик", callback_data=MyCallback(state="entering").pack())
    builder.adjust(1, 2)
    await query.message.answer("Річ додано в кошик!", reply_markup=builder.as_markup())


# це як блять каунтер нахуй
@router.callback_query(MyCallback.filter(F.state == "entering"))
async def my_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.set_state(Form.put_code)
    await query.message.answer("Введіть артикль речі")


@router.callback_query(MyCallback.filter(F.state == "menu"))
async def my_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await echo_handler(query.message)


@router.callback_query(MyCallback.filter(F.state == "ordering"))
async def order_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.set_state(Form.put_personal_data)
    # print(len(query.data.split(':')[1]))
    if len(query.data.split(':')[1]) != 0:
        await state.update_data(put_code=query.data.split(':')[1])
    await query.message.answer("<b>Реквізити для оплати:</b> \nОтримувач: Боклан Софія\nМонобанк: 4441 1144 2342 3837"
                               "\nПісля цього напишіть, будь ласка, свої <b>реквізити для відправки</b> у форматі:"
                               "\nПІБ, номер телефону, місто, номер відділення нової пошти.")


####################
@router.message(Form.put_personal_data)
async def put_personal_data_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    personal_info = message.text
    print(data.keys())
    if data.keys().__contains__("put_code"):
        item_id = data['put_code']
        items_id = [item_id]
        itemsCollection.find_one_and_update({'_id': item_id}, {'$set': {"availability": False}})
    else:
        print(my_cart)
        items_id = my_cart.copy()
        for item_id in my_cart:
            itemsCollection.find_one_and_update({'_id': item_id}, {'$set': {"availability": False}})
        my_cart.clear()
    # await state.update_data(put_personal_data=message.text)

    order = {"order_id": ordersCollection.estimated_document_count() + 1, "items_id": items_id,
             "customer_info": personal_info,
             "username": message.from_user.username, "order_status": "Очікує підтвердження оплати.",
             "order_complete": False}

    ordersCollection.insert_one(order)

    builder = InlineKeyboardBuilder()
    builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
    builder.adjust(1, 2)
    await message.answer("Дякуємо! Очікуйте на підтвердження замовлення протягом доби.",
                         reply_markup=builder.as_markup())

    await state.clear()


@router.message(Form.put_code)
async def put_code_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(put_code=message.text)
    code = message.text
    myquery = {"_id": code}
    item = itemsCollection.find_one(myquery)

    if item is None:
        await message.answer(f"Ми не знайшли речі за таким артиклем. Переконайтесь, що ввели його правильно, "
                             "наприклад <b>АА111А</b>")
    else:
        if item["availability"] is False:
            builder = InlineKeyboardBuilder()
            builder.button(text="Так", callback_data=MyCallback(state="entering").pack())
            builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
            builder.adjust(1, 2)
            await message.answer("Ця річ більше не в наявності :( \nБажаєте придбати іншу річ?",
                                 reply_markup=builder.as_markup())
        else:
            builder = InlineKeyboardBuilder()
            if not my_cart.__contains__(code):
                builder.button(text="Додати в кошик", callback_data=MyCallback(state="cart", code=code).pack())
            builder.button(text="Придбати зараз", callback_data=MyCallback(state="ordering", code=code).pack())
            builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
            builder.adjust(1, 2)
            await message.answer(item["name"] +
                                 "\n\n" +
                                 item["price"] +
                                 " грн" +
                                 "\n\n" +
                                 item["_id"], reply_markup=builder.as_markup())
            await state.clear()


# ПЕРША КОМАНДА "ЗРОБИТИ ЗАМОВЛЕННЯ"
@router.message(F.text == 'Зробити замовлення')
async def command_place_order_handler(message: Message) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="Ввести артикль речі", callback_data=MyCallback(state="entering").pack())
    builder.button(text="Головна сторінка", callback_data=MyCallback(state="menu").pack())
    builder.adjust(1, 2)
    await message.answer("\u2B07\uFE0F \u2B07\uFE0F \u2B07\uFE0F", reply_markup=builder.as_markup())


# ТРЕТЯ КОМАНДА "ЗВʼЯЗАТИСЯ З НАМИ"
@router.message(F.text == 'Звʼязатися з нами')
async def command_contact_handler(message: Message) -> None:
    await message.answer(text="Контакти адміністраторки:\n@sofiiaboklan / +380663343593. \nРобочі години:\n10:00-20:00")


@router.message(F.text == 'Статус замовлення')
async def command_status_handler(message: Message) -> None:
    myquery = {"username": message.from_user.username}
    orders = ordersCollection.find(myquery)
    response = ""
    try:
        while True:
            order = orders.next()
            response += f"Замовлення №{order['order_id']} \n{order['order_status']} + \n {order['items_id']}"
    except StopIteration:
        if response == "":
            response = "no orders on ya name"
        await message.answer(text=response)


# МІЙ КОШИК
@router.message(F.text == 'Мій кошик')
async def command_status_handler(message: Message) -> None:
    items = []
    for item_id in my_cart:
        myquery = {"_id": item_id}
        items.append(itemsCollection.find_one(myquery))

    response = ""

    for item in items:
        response += f"№{item['_id']} + name: {item['name']}"
    if response == "":
        await message.answer(text='nothing there')
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="Перейти до оплати", callback_data=MyCallback(state="ordering").pack())
        builder.button(text="Додати ще одну річ в кошик", callback_data=MyCallback(state="entering").pack())
        builder.adjust(1, 2)
        await message.answer(text=response, reply_markup=builder.as_markup())

    # print(items.next())
    # # while items.next()
    # #     response += f"Замовлення №{item['order_id']} \n{item['order_status']}"
    #
    # await message.answer(text=response)


# message here is a message, sent by user, overall message
# handler that echoes back any message received by sending a copy of the message
@router.message()
async def echo_handler(message: types.Message) -> None:
    keyboard = init_keyboard()
    await message.answer(f"\U0001f90d \U0001f90d \U0001f90d \U0001f90d", reply_markup=keyboard)


# do not touch
# creates a Dispatcher object, attaches the router, creates a Bot instance with the provided token
# and starts the event dispatching by calling dp.start_polling()
async def main() -> None:
    dp = Dispatcher()
    # Dispatcher is a root router
    # ... and all other routers should be attached to Dispatcher
    dp.include_router(router)

    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(TOKEN, parse_mode="HTML")
    # And the run events dispatching
    await dp.start_polling(bot)


# executed when the script is run directly (not imported as a module)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
