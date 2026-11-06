"""HTTP API сервиса инференса."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from text2image_bot import __version__
from text2image_bot.config import ServiceSettings, get_service_settings
from text2image_bot.service.backends import (
    Automatic1111Backend,
    BackendError,
    DummyBackend,
    GenerationParams,
    ImageBackend,
)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000, description="Описание изображения")
    negative_prompt: str = Field("", max_length=1000)
    steps: int | None = Field(None, ge=1, le=150)
    width: int = Field(512, ge=64, le=1024, multiple_of=8)
    height: int = Field(512, ge=64, le=1024, multiple_of=8)
    cfg_scale: float = Field(7.0, ge=1.0, le=30.0)
    seed: int = -1


def build_backend(settings: ServiceSettings) -> ImageBackend:
    if settings.backend == "dummy":
        return DummyBackend()
    return Automatic1111Backend(settings.a1111_url, timeout=settings.a1111_timeout)


def create_app(
    backend: ImageBackend | None = None, settings: ServiceSettings | None = None
) -> FastAPI:
    settings = settings or get_service_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.backend = backend or build_backend(settings)
        yield
        await app.state.backend.aclose()

    app = FastAPI(title="Text2Image service", version=__version__, lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "backend": settings.backend}

    @app.post(
        "/generate",
        response_class=Response,
        responses={200: {"content": {"image/png": {}}}},
    )
    async def generate(body: GenerateRequest, request: Request) -> Response:
        params = GenerationParams(
            prompt=body.prompt.strip(),
            negative_prompt=body.negative_prompt,
            steps=body.steps or settings.default_steps,
            width=body.width,
            height=body.height,
            cfg_scale=body.cfg_scale,
            seed=body.seed,
            sampler=settings.default_sampler,
        )
        try:
            image = await request.app.state.backend.generate(params)
        except BackendError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return Response(content=image, media_type="image/png")

    return app
