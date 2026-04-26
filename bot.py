import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Добавь BOT_TOKEN в Railway Variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Открыть магазин 🍓",
                    web_app=WebAppInfo(url="https://ТВОЯ-ССЫЛКА-НА-САЙТ")
                )
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🍓 Добро пожаловать!\n\n"
        "Нажмите кнопку ниже, чтобы открыть магазин клубники.",
        reply_markup=kb
    )


@dp.message(F.web_app_data)
async def web_app_order(message: Message):
    order = message.web_app_data.data

    text = f"🍓 Новый заказ из Mini App:\n\n{order}"

    await message.answer("✅ Заказ принят! Мы скоро свяжемся с вами.")

    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, text)


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())