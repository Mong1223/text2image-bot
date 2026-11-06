"""Запуск бота: ``python -m text2image_bot.bot``."""

import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from text2image_bot.bot.handlers import router
from text2image_bot.config import get_bot_settings


async def run() -> None:
    settings = get_bot_settings()
    bot = Bot(
        token=settings.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)
    async with httpx.AsyncClient(
        base_url=settings.service_url, timeout=settings.request_timeout
    ) as service:
        # Клиент сервиса передаётся в обработчики как зависимость
        await dp.start_polling(bot, service=service)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
