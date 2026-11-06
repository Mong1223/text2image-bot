"""Бэкенды генерации изображений.

Сервис не привязан к конкретной модели: любой класс с методом ``generate``,
возвращающим PNG-байты, может использоваться как бэкенд.
"""

from __future__ import annotations

import base64
import hashlib
import io
import textwrap
from dataclasses import dataclass
from typing import Protocol

import httpx
from PIL import Image, ImageDraw


@dataclass(frozen=True)
class GenerationParams:
    prompt: str
    negative_prompt: str = ""
    steps: int = 20
    width: int = 512
    height: int = 512
    cfg_scale: float = 7.0
    seed: int = -1
    sampler: str = "Euler a"


class BackendError(RuntimeError):
    """Ошибка на стороне модели (недоступна, вернула некорректный ответ и т.п.)."""


class ImageBackend(Protocol):
    async def generate(self, params: GenerationParams) -> bytes: ...

    async def aclose(self) -> None: ...


class Automatic1111Backend:
    """Stable Diffusion через API Stable Diffusion web UI (AUTOMATIC1111).

    web UI нужно запускать с флагом ``--api``:
    https://github.com/AUTOMATIC1111/stable-diffusion-webui
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 300.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)

    async def generate(self, params: GenerationParams) -> bytes:
        payload = {
            "prompt": params.prompt,
            "negative_prompt": params.negative_prompt,
            "steps": params.steps,
            "width": params.width,
            "height": params.height,
            "cfg_scale": params.cfg_scale,
            "seed": params.seed,
            "sampler_name": params.sampler,
            "batch_size": 1,
        }
        try:
            response = await self._client.post("/sdapi/v1/txt2img", json=payload)
            response.raise_for_status()
            images = response.json()["images"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise BackendError(f"Stable Diffusion web UI вернул ошибку: {exc}") from exc
        if not images:
            raise BackendError("Stable Diffusion web UI не вернул ни одного изображения")
        # Изображение приходит в base64, иногда с префиксом data:image/png;base64,
        return base64.b64decode(images[0].split(",", 1)[-1])

    async def aclose(self) -> None:
        await self._client.aclose()


class DummyBackend:
    """Заглушка без нейросети: рисует градиент с текстом запроса.

    Нужна для разработки бота и тестов на машине без GPU.
    """

    async def generate(self, params: GenerationParams) -> bytes:
        digest = hashlib.sha256(params.prompt.encode("utf-8")).digest()
        start, end = digest[:3], digest[3:6]
        image = Image.new("RGB", (params.width, params.height))
        draw = ImageDraw.Draw(image)
        for y in range(params.height):
            t = y / max(params.height - 1, 1)
            color = tuple(int(s + (e - s) * t) for s, e in zip(start, end, strict=True))
            draw.line([(0, y), (params.width, y)], fill=color)
        text = "\n".join(textwrap.wrap(params.prompt, width=40)[:10])
        draw.multiline_text((16, 16), text, fill=(255, 255, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    async def aclose(self) -> None:
        return None
