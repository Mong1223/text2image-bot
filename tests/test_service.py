import base64
import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from text2image_bot.config import ServiceSettings
from text2image_bot.service.app import create_app
from text2image_bot.service.backends import (
    Automatic1111Backend,
    BackendError,
    DummyBackend,
    GenerationParams,
)


@pytest.fixture
def client():
    settings = ServiceSettings(backend="dummy")
    with TestClient(create_app(DummyBackend(), settings)) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "backend": "dummy"}


def test_generate_returns_png(client):
    response = client.post("/generate", json={"prompt": "cat", "width": 256, "height": 128})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(response.content)).size == (256, 128)


@pytest.mark.parametrize("body", [{"prompt": ""}, {"prompt": "cat", "width": 100}, {}])
def test_generate_validation(client, body):
    assert client.post("/generate", json=body).status_code == 422


def _png_b64() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


async def test_a1111_backend_sends_payload_and_decodes_image():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"images": [_png_b64()]})

    backend = Automatic1111Backend("http://sd", transport=httpx.MockTransport(handler))
    image = await backend.generate(GenerationParams(prompt="little green dog", steps=10))
    await backend.aclose()

    assert seen["path"] == "/sdapi/v1/txt2img"
    assert seen["payload"]["prompt"] == "little green dog"
    assert seen["payload"]["steps"] == 10
    assert Image.open(io.BytesIO(image)).size == (8, 8)


async def test_a1111_backend_error_maps_to_502():
    backend = Automatic1111Backend(
        "http://sd", transport=httpx.MockTransport(lambda r: httpx.Response(500))
    )
    with pytest.raises(BackendError):
        await backend.generate(GenerationParams(prompt="cat"))

    with TestClient(create_app(backend, ServiceSettings())) as c:
        assert c.post("/generate", json={"prompt": "cat"}).status_code == 502
