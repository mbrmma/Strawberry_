import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_БОТА")

ADMIN_CHAT_ID = 2107362512

CITY = "Красноярск"

PICKUP_ADDRESS = "Адрес самовывоза уточнит оператор"

PRICES = {
    0.5: 500,
    1: 1000,
    1.5: 1500,
    2: 2000,
}

PRICE_MODE = "per_box"

MIN_ORDER_KG = 0.5

DELIVERY_FEE = 200

FREE_DELIVERY_FROM = 2000

TIME_SLOTS = [
    "10:00–12:00",
    "12:00–14:00",
    "14:00–16:00",
    "16:00–18:00",
    "18:00–20:00",
]

PAYMENT_TEXT = "Оплата при получении наличными или переводом."

ORDER_COOLDOWN_SEC = 60