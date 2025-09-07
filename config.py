import os
import json

# Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

# Admin chat ID (your Telegram numeric ID) to receive new orders
# Tip: send /id to the bot after start; you'll get your chat id in logs/admin once implemented.
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # set to your ID

# City name for messages
CITY = os.getenv("CITY", "Ваш город")

# Price config: sizes (kg) -> price per kg or per package depending on 'PRICE_MODE'
# Use JSON in env PRICES_JSON='{"0.5": 4.0, "1": 7.5, "2": 14.0}'
PRICES = {
    0.5: 4.0,
    1.0: 7.5,
    2.0: 14.0,
}
try:
    _env_prices = os.getenv("PRICES_JSON")
    if _env_prices:
        data = json.loads(_env_prices)
        PRICES = {float(k): float(v) for k, v in data.items()}
except Exception as e:
    # Fallback to defaults if parsing fails
    pass

# 'per_pack' means the prices above are per chosen package (0.5kg box has that price)
# 'per_kg' means prices are per kg, total = size_kg * price * qty
PRICE_MODE = os.getenv("PRICE_MODE", "per_pack")  # 'per_pack' or 'per_kg'

# Minimum order kg (sum of all items). For example 1 kg.
MIN_ORDER_KG = float(os.getenv("MIN_ORDER_KG", "0.5"))

# Free delivery threshold in currency units
FREE_DELIVERY_FROM = float(os.getenv("FREE_DELIVERY_FROM", "20"))

# Delivery fee if below threshold
DELIVERY_FEE = float(os.getenv("DELIVERY_FEE", "3"))

# Payment instructions (shown to user after confirm)
PAYMENT_TEXT = os.getenv(
    "PAYMENT_TEXT",
    "Оплата переводом по номеру/QR после подтверждения. Курьер выдаст чек."
)

# Optional static address for pickup (if user selects pickup)
PICKUP_ADDRESS = os.getenv("PICKUP_ADDRESS", "Пункт самовывоза: ул. Примерная, 1")

# Time window text to show as quick options
TIME_SLOTS = os.getenv("TIME_SLOTS", "В течение часа,12:00–14:00,14:00–16:00,18:00–20:00").split(",")

# Enable simple rate-limiting (seconds between orders from same user)
ORDER_COOLDOWN_SEC = int(os.getenv("ORDER_COOLDOWN_SEC", "60"))
