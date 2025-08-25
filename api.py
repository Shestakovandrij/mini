from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import logging
from telegram_init_data import validate
from pydantic import BaseModel
from typing import List
from database import Database

BOT_TOKEN = '8252312259:AAH0BKm3oD7ws5da02kEhaj4-W1UrdrFq70'

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.DEBUG)

db = Database()

app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

@app.get("/")
async def index(request: Request):
    init_data = request.query_params.get('tgWebAppData', '')
    try:
        if init_data and not validate(BOT_TOKEN, init_data):
            logging.error("Невалідний init_data")
            raise HTTPException(403, "Невалідний init_data")
        return FileResponse("mini_app/dist/index.html")
    except Exception as e:
        logging.error(f"Помилка в index: {e}")
        raise HTTPException(500, "Внутрішня помилка сервера")

@app.get("/categories")
async def categories():
    try:
        cats = db.get_categories()
        return [{"id": id, "name": name} for id, name in cats]
    except Exception as e:
        logging.error(f"Помилка в categories: {e}")
        raise HTTPException(500, str(e))

@app.get("/products/{cat_id}")
async def products(cat_id: int):
    try:
        prods = db.get_products(cat_id)
        return [{"id": id, "name": name, "desc": description, "price": price, "stock": stock, "photo": photo} for id, name, description, price, stock, photo in prods]
    except Exception as e:
        logging.error(f"Помилка в products: {e}")
        raise HTTPException(500, str(e))

@app.get("/cart")
async def get_cart(user_id: int):
    try:
        cart = db.get_cart(user_id)
        return [{"id": id, "name": name, "price": price, "quantity": qty, "photo": photo} for id, name, price, qty, photo in cart]
    except Exception as e:
        logging.error(f"Помилка в cart: {e}")
        raise HTTPException(500, str(e))

class AddToCart(BaseModel):
    user_id: int
    product_id: int
    quantity: int = 1

@app.post("/add_to_cart")
async def add_to_cart(item: AddToCart):
    try:
        db.add_to_cart(item.user_id, item.product_id, item.quantity)
        return {"success": True}
    except Exception as e:
        logging.error(f"Помилка в add_to_cart: {e}")
        raise HTTPException(500, str(e))

class RemoveFromCart(BaseModel):
    user_id: int
    product_id: int

@app.post("/remove_from_cart")
async def remove_from_cart(item: RemoveFromCart):
    try:
        db.remove_from_cart(item.user_id, item.product_id)
        return {"success": True}
    except Exception as e:
        logging.error(f"Помилка в remove_from_cart: {e}")
        raise HTTPException(500, str(e))

class CreateOrder(BaseModel):
    user_id: int
    products: List[List[int]]
    total: float
    delivery: str
    payment: str
    address: str

@app.post("/create_order")
async def create_order(order: CreateOrder):
    try:
        products_str = ','.join([f"{pid}:{qty}" for pid, qty in order.products])
        order_id = db.create_order(order.user_id, products_str, order.total, order.delivery, order.payment, order.address)
        for pid, qty in order.products:
            db.update_product_stock(pid, qty)
        db.clear_cart(order.user_id)
        return {"order_id": order_id}
    except Exception as e:
        logging.error(f"Помилка в create_order: {e}")
        raise HTTPException(500, str(e))