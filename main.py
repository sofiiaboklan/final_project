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


# This function initializes the database connection and returns the collection object for further use.
def initDB():
    myclient = pymongo.MongoClient()
    mydb = myclient["papergardener_db"]

    mycol = mydb["catalogue"]
    mycol1 = mydb["orders"]

    myItems = [{"_id": "A111A1", "name": "Кеди converse оригінал", "size": "36.5 / 23 см", "price": "300",
                "availability": True},
               {"_id": "A111A2", "name": "Чорний кроп-топ", "size": "S", "price": "150",
                "availability": False}]

    myOrders = [{"order_id": "1", "item_id": "A111A2", "customer_info": "Софія Боклан, Київ, 304",
                 "username": "sofiiaboklan", "order_status": "awaiting for confirmation", "order_complete": False}]

    if mycol.find(myItems[0]) is None:
        mycol.insert_many(myItems)

    if mycol1.find(myOrders[0]) is None:
        mycol.insert_many(myOrders)

    return mycol, mycol1


# creates and returns a custom keyboard
def init_keyboard():
    button_order = KeyboardButton(text="Зробити замовлення")
    button_track_order = KeyboardButton(text="Статус замовлення")
    button_admin = KeyboardButton(text="Звʼязатися з нами")
    keyboard = ReplyKeyboardMarkup(keyboard=[[button_order], [button_track_order], [button_admin]],
                                   resize_keyboard=True, row_width=1, is_persistent=True)

    return keyboard


# Bot token can be obtained via https://t.me/BotFather
TOKEN = "6157897368:AAH00AiVBg7TJMmYEjXWqu_LyQ3rDnfbn5M"

# All handlers should be attached to the Router/Dispatcher. It creates an instance of the Router class from aiogram.
router = Router()

# a variable to initialize the database connection and returns the collection object for further use.
itemsCollection, ordersCollection = initDB()


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
    entering: bool


class Form(StatesGroup):
    put_code = State()


# це як блять каунтер нахуй
@router.callback_query(MyCallback.filter(F.entering == True))
async def my_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.set_state(Form.put_code)
    await query.message.answer("Введіть артикль речі")


@router.callback_query(MyCallback.filter(F.entering == False))
async def my_callback_foo(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await echo_handler(query.message)


@router.message(Form.put_code)
async def put_code_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(put_code=message.text)
    code = message.text
    myquery = {"_id": code}
    item = itemsCollection.find_one(myquery)
    if item is None:
        await message.answer("Ми не знайшли речі за таким артиклем. Переконайтесь, що ввели його правильно, "
                             "наприклад АА111А")
    else:
        if item["availability"] is False:
            builder = InlineKeyboardBuilder()
            builder.button(text="Так", callback_data=MyCallback(entering=True).pack())
            builder.button(text="Головна сторінка", callback_data=MyCallback(entering=False).pack())
            builder.adjust(1, 2)
            await message.answer("Ця річ більше не в наявності :( \nБажаєте придбати іншу річ?",
                                 reply_markup=builder.as_markup())
        else:
            # print(message.from_user.username)
            await message.answer(item["name"])
            await state.clear()


# ПЕРША КОМАНДА "ЗРОБИТИ ЗАМОВЛЕННЯ"
@router.message(F.text == 'Зробити замовлення')
async def command_place_order_handler(message: Message) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="Ввести артикль речі", callback_data=MyCallback(entering=True).pack())
    builder.button(text="Головна сторінка", callback_data=MyCallback(entering=False).pack())
    builder.adjust(1, 2)
    await message.answer("\u2B07\uFE0F \u2B07\uFE0F \u2B07\uFE0F", reply_markup=builder.as_markup())


# ТРЕТЯ КОМАНДА "ЗВʼЯЗАТИСЯ З НАМИ"
@router.message(F.text == 'Звʼязатися з нами')
async def command_contact_handler(message: Message) -> None:
    await message.answer(text="Контакти адміністраторки:\n@sofiiaboklan / +380663343593. \nРобочі години:\n10:00-20:00")


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
