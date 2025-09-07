import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import html

import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("strawberry_bot")

bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- Order model ---
@dataclass
class Order:
    user_id: int
    username: Optional[str]
    size_kg: float = 0.0
    qty: int = 0
    delivery_type: Optional[str] = None  # 'delivery' or 'pickup'
    address: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    time_slot: Optional[str] = None
    comment: Optional[str] = None

    def total_kg(self) -> float:
        return round(self.size_kg * self.qty, 2)

    def items_sum(self) -> float:
        price = config.PRICES.get(self.size_kg, 0.0)
        if config.PRICE_MODE == "per_kg":
            return round(price * self.size_kg * self.qty, 2)
        return round(price * self.qty, 2)

    def delivery_fee(self) -> float:
        return 0.0 if self.items_sum() >= config.FREE_DELIVERY_FROM or self.delivery_type == "pickup" else config.DELIVERY_FEE

    def total_sum(self) -> float:
        return round(self.items_sum() + self.delivery_fee(), 2)

    def as_text(self) -> str:
        lines = [
            f"🍓 <b>Заказ клубники</b> ({html.quote(config.CITY)})",
            f"Размер коробки: <b>{self.size_kg} кг</b> × <b>{self.qty}</b> шт",
            f"Итого вес: <b>{self.total_kg()} кг</b>",
            f"Сумма товаров: <b>{self.items_sum():.2f}</b>",
        ]
        if self.delivery_type == "delivery":
            lines.append("Способ: <b>Доставка</b>")
            lines.append(f"Адрес: {html.quote(self.address or '-')}")
            lines.append(f"Окно доставки: {html.quote(self.time_slot or '-')}")
            fee = self.delivery_fee()
            if fee > 0:
                lines.append(f"Доставка: <b>{fee:.2f}</b> (бесплатно от {config.FREE_DELIVERY_FROM})")
            else:
                lines.append("Доставка: <b>БЕСПЛАТНО</b>")
        else:
            lines.append("Способ: <b>Самовывоз</b>")
            lines.append(f"{html.quote(config.PICKUP_ADDRESS)}")
        lines += [
            f"Имя: {html.quote(self.name or '-')}",
            f"Телефон: {html.quote(self.phone or '-')}",
        ]
        if self.comment:
            lines.append(f"Комментарий: {html.quote(self.comment)}")
        lines.append(f"Итого к оплате: <b>{self.total_sum():.2f}</b>")
        return "\n".join(lines)

# --- Simple in-memory storage ---
user_orders: Dict[int, Order] = {}
last_order_ts: Dict[int, float] = {}

# --- FSM ---
class Form(StatesGroup):
    choosing_size = State()
    choosing_qty = State()
    choosing_delivery = State()
    entering_address = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    entering_comment = State()
    confirming = State()

# --- Keyboards ---
def sizes_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for size in sorted(config.PRICES.keys()):
        kb.button(text=f"{size} кг — {config.PRICES[size]:.2f}", callback_data=f"size:{size}")
    kb.adjust(1)
    return kb

def qty_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for q in [1,2,3,4,5,6]:
        kb.button(text=f"{q} шт", callback_data=f"qty:{q}")
    kb.button(text="⬅️ Назад", callback_data="back:size")
    kb.adjust(3)
    return kb

def delivery_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚚 Доставка", callback_data="delivery:delivery")
    kb.button(text="🏬 Самовывоз", callback_data="delivery:pickup")
    kb.button(text="⬅️ Назад", callback_data="back:qty")
    kb.adjust(2,1)
    return kb

def time_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for slot in config.TIME_SLOTS:
        kb.button(text=slot, callback_data=f"time:{slot}")
    kb.button(text="⬅️ Назад", callback_data="back:address")
    kb.adjust(2)
    return kb

def confirm_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить заказ", callback_data="confirm:yes")
    kb.button(text="✍️ Добавить комментарий", callback_data="comment:add")
    kb.button(text="⬅️ Назад", callback_data="back:phone")
    kb.adjust(1,1,1)
    return kb

# --- Handlers ---
@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    text = (
        "🍓 <b>Клубника с доставкой</b> по городу "
        f"{html.quote(config.CITY)}\n\n"
        "Выберите фасовку:"
    )
    await m.answer(text, reply_markup=sizes_kb().as_markup())
    await state.set_state(Form.choosing_size)

@router.message(Command("menu"))
async def menu(m: Message, state: FSMContext):
    await start(m, state)

@router.callback_query(F.data.startswith("size:"))
async def choose_size(c: CallbackQuery, state: FSMContext):
    size = float(c.data.split(":")[1])
    order = user_orders.get(c.from_user.id) or Order(user_id=c.from_user.id, username=c.from_user.username)
    order.size_kg = size
    user_orders[c.from_user.id] = order
    await c.message.edit_text(
        f"Выбрана фасовка: <b>{size} кг</b>\nВыберите количество коробок:",
        reply_markup=qty_kb().as_markup()
    )
    await state.set_state(Form.choosing_qty)
    await c.answer()

@router.callback_query(F.data.startswith("qty:"))
async def choose_qty(c: CallbackQuery, state: FSMContext):
    qty = int(c.data.split(":")[1])
    order = user_orders.get(c.from_user.id)
    if not order:
        await c.answer("Сначала выберите фасовку", show_alert=True)
        return
    order.qty = qty
    # check min kg
    if order.total_kg() < config.MIN_ORDER_KG:
        await c.answer(f"Минимальный заказ: {config.MIN_ORDER_KG} кг", show_alert=True)
    await c.message.edit_text(
        f"Коробок: <b>{qty}</b> (вес {order.total_kg()} кг)\nВыберите способ получения:",
        reply_markup=delivery_kb().as_markup()
    )
    await state.set_state(Form.choosing_delivery)
    await c.answer()

@router.callback_query(F.data.startswith("delivery:"))
async def choose_delivery(c: CallbackQuery, state: FSMContext):
    d = c.data.split(":")[1]
    order = user_orders.get(c.from_user.id)
    if not order:
        await c.answer("Сначала выберите фасовку и количество", show_alert=True)
        return
    order.delivery_type = d
    if d == "delivery":
        await c.message.edit_text("📍 Введите <b>адрес доставки</b> (улица, дом, подъезд/этаж):")
        await state.set_state(Form.entering_address)
    else:
        await c.message.edit_text(
            f"Самовывоз выбран. {html.quote(config.PICKUP_ADDRESS)}\n\n"
            "Введите ваше <b>имя</b>:")
        await state.set_state(Form.entering_name)
    await c.answer()

@router.message(Form.entering_address, F.text.len() > 5)
async def get_address(m: Message, state: FSMContext):
    order = user_orders.get(m.from_user.id)
    order.address = m.text.strip()
    # choose time
    kb = time_kb().as_markup()
    await m.answer("⏰ Выберите удобное <b>время доставки</b>:", reply_markup=kb)
    await state.set_state(Form.choosing_time)

@router.message(Form.entering_address)
async def address_too_short(m: Message):
    await m.answer("Похоже, адрес короткий. Пожалуйста, укажите улицу и дом.")

@router.callback_query(Form.choosing_time, F.data.startswith("time:"))
async def choose_time(c: CallbackQuery, state: FSMContext):
    order = user_orders.get(c.from_user.id)
    order.time_slot = c.data.split(":", 1)[1]
    await c.message.edit_text("Введите ваше <b>имя</b>:")
    await state.set_state(Form.entering_name)
    await c.answer()

@router.message(Form.entering_name, F.text.len() >= 2)
async def get_name(m: Message, state: FSMContext):
    order = user_orders.get(m.from_user.id)
    order.name = m.text.strip()
    await m.answer("📞 Введите ваш <b>номер телефона</b>:")
    await state.set_state(Form.entering_phone)

@router.message(Form.entering_name)
async def name_too_short(m: Message):
    await m.answer("Имя слишком короткое. Повторите.")

@router.message(Form.entering_phone, F.text.regexp(r"^[+\d][\d\s\-()]{7,}$"))
async def get_phone(m: Message, state: FSMContext):
    order = user_orders.get(m.from_user.id)
    order.phone = m.text.strip()
    text = order.as_text() + "\n\n" + html.quote(config.PAYMENT_TEXT)
    await m.answer(text, reply_markup=confirm_kb().as_markup())
    await state.set_state(Form.confirming)

@router.message(Form.entering_phone)
async def phone_invalid(m: Message):
    await m.answer("Похоже, это не телефон. Укажите номер с кодом (например, +34 ...).")

@router.callback_query(Form.confirming, F.data == "comment:add")
async def add_comment(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text("Напишите комментарий к заказу (подъезд, домофон, пожелания):")
    await state.set_state(Form.entering_comment)
    await c.answer()

@router.message(Form.entering_comment, F.text.len() > 0)
async def save_comment(m: Message, state: FSMContext):
    order = user_orders.get(m.from_user.id)
    order.comment = m.text.strip()
    await m.answer(order.as_text() + "\n\n" + html.quote(config.PAYMENT_TEXT), reply_markup=confirm_kb().as_markup())
    await state.set_state(Form.confirming)

@router.callback_query(Form.confirming, F.data == "confirm:yes")
async def confirm_order(c: CallbackQuery, state: FSMContext):
    import time
    now = time.time()
    last = last_order_ts.get(c.from_user.id, 0)
    if now - last < config.ORDER_COOLDOWN_SEC:
        await c.answer("Похоже, вы уже отправили заказ. Немного подождите и попробуйте снова.", show_alert=True)
        return
    last_order_ts[c.from_user.id] = now

    order = user_orders.get(c.from_user.id)
    if not order:
        await c.answer("Заказ не найден. Начните заново: /start", show_alert=True)
        return

    # Notify admin
    admin_text = order.as_text() + f"\n\nПокупатель: @{c.from_user.username or '—'} (ID {c.from_user.id})"
    try:
        if config.ADMIN_CHAT_ID:
            await bot.send_message(chat_id=config.ADMIN_CHAT_ID, text="🔔 <b>Новый заказ</b>\n\n" + admin_text)
    except Exception as e:
        log.exception("Failed to notify admin: %s", e)

    await c.message.edit_text("✅ Заказ принят!\nНаш оператор свяжется с вами для подтверждения. Спасибо!")
    await state.clear()
    await c.answer()

@router.message(Command("id"))
async def my_id(m: Message):
    await m.answer(f"Ваш chat_id: <code>{m.chat.id}</code>")

async def main():
    if config.BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        log.warning("Please set BOT_TOKEN environment variable or config.BOT_TOKEN.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
