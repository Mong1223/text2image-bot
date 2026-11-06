"""Обработчики сообщений бота."""

from __future__ import annotations

import logging

import httpx
from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, Message

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "Отправь текстовое описание изображения, и я сгенерирую картинку с помощью "
    "Stable Diffusion.\n\n"
    "Лучше всего модель понимает английский язык. Пример:\n"
    "<code>Little green dog, high detailed, realistic</code>"
)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "друг"
    await message.answer(f"Привет, {name}! Отправь описание изображения.\n\n/help — подсказка")


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(F.text & ~F.text.startswith("/"))
async def generate_handler(message: Message, service: httpx.AsyncClient) -> None:
    prompt = message.text.strip()
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    try:
        response = await service.post("/generate", json={"prompt": prompt})
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Ошибка запроса к сервису инференса")
        await message.reply("Не удалось сгенерировать изображение, попробуй позже.")
        return
    photo = BufferedInputFile(response.content, filename="image.png")
    await message.reply_photo(photo, caption=prompt[:1024])
