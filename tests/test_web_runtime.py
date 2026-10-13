"""Guard the actual HTTP middleware protocol, beyond Streamlit's script runner."""
import asyncio
import pytest
from streamlit.web.server.starlette.starlette_gzip_middleware import MediaAwareGZipMiddleware


@pytest.mark.parametrize("encoding", [b"gzip", b"identity"])
def test_media_response_sends_headers_before_body(encoding):
    messages = []
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"image/png")]})
        await send({"type": "http.response.body", "body": b"fixture-media", "more_body": False})
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
    async def send(message):
        messages.append(message)
    middleware = MediaAwareGZipMiddleware(app)
    asyncio.run(middleware({"type": "http", "path": "/media/fixture", "headers": [(b"accept-encoding", encoding)]}, receive, send))
    assert [m["type"] for m in messages] == ["http.response.start", "http.response.body"]
    assert messages[1]["body"] == b"fixture-media"
    assert not any(name == b"content-encoding" for name, value in messages[0]["headers"])
