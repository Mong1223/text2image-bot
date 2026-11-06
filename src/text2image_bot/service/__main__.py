"""Запуск сервиса: ``python -m text2image_bot.service``."""

import uvicorn

from text2image_bot.config import get_service_settings
from text2image_bot.service.app import create_app


def main() -> None:
    settings = get_service_settings()
    uvicorn.run(create_app(settings=settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
