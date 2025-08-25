import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from database import Database

BOT_TOKEN = '8252312259:AAH0BKm3oD7ws5da02kEhaj4-W1UrdrFq70'
ADMIN_ID = 420620196
PAYMENT_PROVIDER_TOKEN = 'TEST:YOUR_PAYMENT_TOKEN'
ADMIN_PASSWORD = 'admin123'  # Зміни на свій

logging.basicConfig(level=logging.DEBUG)  # Більше логів для помилок

db = Database()

class AdminLogin(StatesGroup):
    password = State()

class AdminAddCategory(StatesGroup):
    name = State()

class AdminAddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    category_id = State()
    stock = State()
    photo = State()

class OrderProcess(StatesGroup):
    delivery = State()
    address = State()
    payment = State()
    confirm = State()

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="Каталог 📋"), KeyboardButton(text="Кошик 🛒")],
        [KeyboardButton(text="Мої замовлення 📦"), KeyboardButton(text="Допомога ❓")],
        [KeyboardButton(text="Адмін-панель 🔧"), KeyboardButton(text="Mini App 🛍️", web_app=WebAppInfo(url="http://localhost:8000/"))]  # Заміни на ngrok URL
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    db.add_user(user_id)
    await message.answer("Вітаю в магазині! Оберіть опцію:", reply_markup=get_main_keyboard())

@dp.message(F.text == "Адмін-панель 🔧")
async def admin_panel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if db.is_admin(user_id) or user_id == ADMIN_ID:
        inline_kb = [
            [InlineKeyboardButton(text="Додати товар ➕", callback_data="admin_add_product")],
            [InlineKeyboardButton(text="Видалити товар ❌", callback_data="admin_delete_product")],
            [InlineKeyboardButton(text="Додати категорію 📁", callback_data="admin_add_category")],
            [InlineKeyboardButton(text="Показати категорії з ID 👀", callback_data="admin_show_categories")],
            [InlineKeyboardButton(text="Перегляд замовлень 📋", callback_data="admin_orders")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
        await message.answer("Адмін-панель готова!", reply_markup=keyboard)
    else:
        await state.set_state(AdminLogin.password)
        await message.answer("Введіть пароль для адмін-доступу:")

@dp.message(AdminLogin.password)
async def process_password(message: types.Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        db.set_admin(message.from_user.id)
        await message.answer("Ви тепер адмін! 🔥")
        await state.clear()
    else:
        await message.answer("Неправильний пароль. Спробуйте ще.")
        await state.clear()

@dp.callback_query(F.data == "admin_add_category")
async def add_category_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminAddCategory.name)
    await callback.message.answer("Введіть назву категорії:")

@dp.message(AdminAddCategory.name)
async def process_category_name(message: types.Message, state: FSMContext):
    try:
        db.add_category(message.text)
        await message.answer("Категорію додано! 📁")
    except Exception as e:
        logging.error(f"Помилка додавання категорії: {e}")
        await message.answer("Помилка додавання. Спробуйте ще.")
    await state.clear()

@dp.callback_query(F.data == "admin_add_product")
async def add_product_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminAddProduct.name)
    await callback.message.answer("Введіть назву товару:")

@dp.message(AdminAddProduct.name)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminAddProduct.description)
    await message.answer("Введіть опис:")

@dp.message(AdminAddProduct.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AdminAddProduct.price)
    await message.answer("Введіть ціну (число):")

@dp.message(AdminAddProduct.price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await state.set_state(AdminAddProduct.category_id)
        await message.answer("Введіть ID категорії (з 'Показати категорії'):")
    except ValueError:
        await message.answer("Неправильна ціна. Введіть число, наприклад 100.50.")

@dp.message(AdminAddProduct.category_id)
async def process_category_id(message: types.Message, state: FSMContext):
    try:
        category_id = int(message.text)
        await state.update_data(category_id=category_id)
        await state.set_state(AdminAddProduct.stock)
        await message.answer("Введіть кількість на складі (число):")
    except ValueError:
        await message.answer("Неправильний ID. Введіть число, наприклад 1.")

@dp.message(AdminAddProduct.stock)
async def process_stock(message: types.Message, state: FSMContext):
    try:
        stock = int(message.text)
        await state.update_data(stock=stock)
        await state.set_state(AdminAddProduct.photo)
        await message.answer("Введіть URL фото (або 'none' для пропуску):")
    except ValueError:
        await message.answer("Неправильна кількість. Введіть число, наприклад 10.")

@dp.message(AdminAddProduct.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo = message.text if message.text != 'none' else None
    try:
        db.add_product(data['name'], data['description'], data['price'], data['category_id'], data['stock'], photo)
        await message.answer("Товар додано! ➕")
    except Exception as e:
        logging.error(f"Помилка додавання товару: {e}")
        await message.answer("Помилка додавання. Перевірте ID категорії.")
    await state.clear()

@dp.callback_query(F.data == "admin_show_categories")
async def show_categories(callback: types.CallbackQuery):
    categories = db.get_categories()
    if not categories:
        await callback.message.answer("Немає категорій. Додайте спочатку.")
        return
    text = "Категорії:\n" + "\n".join([f"ID {id}: {name}" for id, name in categories])
    await callback.message.answer(text)

@dp.message(F.text == "Каталог 📋")
async def catalog(message: types.Message):
    categories = db.get_categories()
    if not categories:
        await message.answer("Немає категорій. Додайте через адмін-панель. 📁")
        return
    inline_kb = [[InlineKeyboardButton(text=name, callback_data=f"cat_{id}")] for id, name in categories]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await message.answer("Оберіть категорію:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("cat_"))
async def show_products(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    products = db.get_products(cat_id)
    if not products:
        await callback.answer("Немає товарів в цій категорії.")
        return
    text = "Товари:\n"
    inline_kb = []
    for pid, name, desc, price, stock, photo in products:
        text += f"{name}: {price} грн, в наявності {stock}\n"
        inline_kb.append([InlineKeyboardButton(text=f"Додати {name} 🛒", callback_data=f"add_{pid}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    try:
        db.add_to_cart(user_id, product_id)
        await callback.answer("Додано в кошик! 🛒")
    except Exception as e:
        logging.error(f"Помилка додавання в кошик: {e}")
        await callback.answer("Помилка. Спробуйте ще.")

@dp.message(F.text == "Кошик 🛒")
async def cart(message: types.Message):
    user_id = message.from_user.id
    cart_items = db.get_cart(user_id)
    if not cart_items:
        await message.answer("Кошик порожній. 😔")
        return
    text = "Кошик:\n"
    total = 0
    for pid, name, price, qty, photo in cart_items:
        subtotal = price * qty
        text += f"{name} x{qty}: {subtotal} грн\n"
        total += subtotal
    text += f"Всього: {total} грн 💰"
    inline_kb = [
        [InlineKeyboardButton(text="Оформити ✅", callback_data="order_start")],
        [InlineKeyboardButton(text="Очистити ❌", callback_data="clear_cart")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    db.clear_cart(user_id)
    await callback.answer("Кошик очищено! 🗑️")

@dp.callback_query(F.data == "order_start")
async def order_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OrderProcess.delivery)
    inline_kb = [
        [InlineKeyboardButton(text="Нова Пошта", callback_data="del_np")],
        [InlineKeyboardButton(text="Укрпошта", callback_data="del_up")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await callback.message.edit_text("Оберіть доставку:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("del_"))
async def choose_delivery(callback: types.CallbackQuery, state: FSMContext):
    delivery = "Нова Пошта" if callback.data == "del_np" else "Укрпошта"
    await state.update_data(delivery_name=delivery)
    await state.set_state(OrderProcess.address)
    await callback.message.edit_text("Введіть адресу доставки:")

@dp.message(OrderProcess.address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderProcess.payment)
    inline_kb = [
        [InlineKeyboardButton(text="Готівкою", callback_data="pay_cash")],
        [InlineKeyboardButton(text="Онлайн", callback_data="pay_online")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await message.answer("Оберіть спосіб оплати:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("pay_"))
async def choose_payment(callback: types.CallbackQuery, state: FSMContext):
    payment = "cash" if callback.data == "pay_cash" else "online"
    await state.update_data(payment=payment)
    data = await state.get_data()
    user_id = callback.from_user.id
    cart = db.get_cart(user_id)
    total = sum(price * qty for _, _, price, qty, _ in cart)
    cart_str = ', '.join([f"{name} x{qty}" for _, name, _, qty, _ in cart])
    text = f"Замовлення: {cart_str}\nДоставка: {data['delivery_name']}\nАдреса: {data['address']}\nОплата: {payment}\nВсього: {total} грн\nПідтвердити?"
    inline_kb = [
        [InlineKeyboardButton(text="Так ✅", callback_data="confirm_order")],
        [InlineKeyboardButton(text="Скасувати ❌", callback_data="cancel_order")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.update_data(total=total, cart=cart_str, cart_items=cart)

@dp.callback_query(F.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    try:
        order_id = db.create_order(user_id, data['cart'], data['total'], data['delivery_name'], data['payment'], data['address'])
        for pid, _, _, qty, _ in data['cart_items']:
            db.update_product_stock(pid, qty)
        db.clear_cart(user_id)
        if data['payment'] == "online":
            prices = [types.LabeledPrice(label="Замовлення", amount=int(data['total'] * 100))]
            await bot.send_invoice(
                chat_id=user_id,
                title="Оплата замовлення",
                description="Оплата за товари",
                payload=f"order_{order_id}",
                provider_token=PAYMENT_PROVIDER_TOKEN,
                currency="UAH",
                prices=prices
            )
        else:
            await callback.message.answer(f"Замовлення #{order_id} створено! Статус: new 🎉")
    except Exception as e:
        logging.error(f"Помилка створення замовлення: {e}")
        await callback.message.answer("Помилка створення замовлення.")
    await state.clear()

@dp.callback_query(F.data == "cancel_order")
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Замовлення скасовано. 😔")

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    order_id = int(payload.split("_")[1])
    db.update_order_status(order_id, "paid")
    await message.answer("Оплата успішна! Замовлення обробляється. 💥")

@dp.message(F.text == "Мої замовлення 📦")
async def my_orders(message: types.Message):
    user_id = message.from_user.id
    orders = db.get_orders(user_id)
    if not orders:
        await message.answer("Замовлень немає. Час купити щось! 🛍️")
        return
    text = "Ваші замовлення:\n"
    for oid, _, products, total, delivery, payment, status, address in orders:
        text += f"#{oid}: {total} грн, {delivery}, {payment}, статус: {status}\n"
    await message.answer(text)

@dp.message(F.text == "Допомога ❓")
async def help(message: types.Message):
    await message.answer("Як купити: Оберіть каталог 📋, додайте товари, перейдіть в кошик 🛒 і оформіть.")

@dp.callback_query(F.data == "admin_delete_product")
async def admin_delete_product(callback: types.CallbackQuery):
    products = db.conn.cursor().execute("SELECT id, name FROM products").fetchall()
    if not products:
        await callback.message.answer("Немає товарів для видалення.")
        return
    inline_kb = [[InlineKeyboardButton(text=f"Видалити {name} ❌", callback_data=f"del_prod_{pid}")] for pid, name in products]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await callback.message.edit_text("Оберіть товар для видалення:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("del_prod_"))
async def confirm_delete(callback: types.CallbackQuery):
    prod_id = int(callback.data.split("_")[2])
    try:
        db.delete_product(prod_id)
        await callback.answer("Товар видалено! ❌")
    except Exception as e:
        logging.error(f"Помилка видалення: {e}")
        await callback.answer("Помилка видалення.")

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: types.CallbackQuery):
    orders = db.get_all_orders()
    text = "Всі замовлення:\n"
    if not orders:
        text += "Немає замовлень. 😔"
    for oid, user_id, products, total, delivery, payment, status, address in orders:
        text += f"#{oid} (user {user_id}): {total} грн, статус: {status} 📦\n"
    inline_kb = [[InlineKeyboardButton(text=f"Змінити статус #{oid} 🔄", callback_data=f"status_{oid}")] for oid, *_ in orders]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("status_"))
async def change_status(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    db.update_order_status(order_id, 'sent')
    await callback.answer("Статус змінено на 'sent'! 🔄")

async def main():
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "pre_checkout_query", "successful_payment"])

if __name__ == '__main__':
    asyncio.run(main())