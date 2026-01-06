import pytest
import respx
from httpx import Response
import time
import uuid

from rakutenai_py import core

# A fixed timestamp and nonce for deterministic signature generation
FIXED_TIMESTAMP = 1678886400
FIXED_NONCE = "fixed-nonce-uuid"
DEVICE_ID = "test-device-id"
ACCESS_TOKEN = "test-access-token"

@pytest.fixture
def mock_dependencies(monkeypatch):
    """Mocks time and uuid to produce deterministic signatures."""
    monkeypatch.setattr(time, "time", lambda: FIXED_TIMESTAMP)
    monkeypatch.setattr(uuid, "uuid4", lambda: FIXED_NONCE)

@pytest.mark.asyncio
async def test_generate_signature():
    """Tests the signature generation with a known string."""
    message = f"GET/api/v2/auth/anonymous{FIXED_TIMESTAMP}{FIXED_NONCE}"
    secret = core.SECRET_KEY
    # This expected signature is pre-calculated based on the fixed inputs
    expected_signature = "Ex8AnlVDkXtKC5Xm6BXChaGJB7SgYv7_BwKPGWJ3bB8"
    signature = await core.generate_signature(message, secret)
    assert signature == expected_signature

@pytest.mark.asyncio
async def test_get_signed_headers(mock_dependencies):
    """Tests that signed headers are generated correctly."""
    headers = await core.get_signed_headers("GET", "/api/v2/auth/anonymous")
    assert headers["X-Timestamp"] == str(FIXED_TIMESTAMP)
    assert headers["X-Nonce"] == FIXED_NONCE
    assert "X-Signature" in headers

@pytest.mark.asyncio
@respx.mock
async def test_fetch_anonymous_token_success(mock_dependencies):
    """Tests successful fetching of an anonymous token."""
    route = respx.get(f"{core.BASE_URL}/api/v2/auth/anonymous").mock(
        return_value=Response(
            200,
            json={"code": "0", "message": "Success", "data": {"accessToken": "fake-token"}}
        )
    )
    token_data = await core.fetch_anonymous_token(DEVICE_ID)
    assert route.called
    assert token_data["accessToken"] == "fake-token"

@pytest.mark.asyncio
@respx.mock
async def test_fetch_anonymous_token_api_error(mock_dependencies):
    """Tests handling of an API error when fetching a token."""
    respx.get(f"{core.BASE_URL}/api/v2/auth/anonymous").mock(
        return_value=Response(
            200,
            json={"code": "E00101", "message": "Authentication Failed"}
        )
    )
    with pytest.raises(Exception, match="Authentication Failed"):
        await core.fetch_anonymous_token(DEVICE_ID)

@pytest.mark.asyncio
async def test_get_signed_ws_url(mock_dependencies):
    """Tests generation of a signed WebSocket URL."""
    ws_path = f"/ws/v1/chat?deviceId={DEVICE_ID}"
    url = await core.get_signed_ws_url(ws_path, ACCESS_TOKEN)
    
    assert url.startswith(core.WS_BASE_URL)
    assert f"deviceId={DEVICE_ID}" in url
    assert f"accessToken={ACCESS_TOKEN}" in url
    assert f"x-timestamp={FIXED_TIMESTAMP}" in url
    assert f"x-nonce={FIXED_NONCE}" in url
    assert "x-signature=" in url

@pytest.mark.asyncio
@respx.mock
async def test_create_chat_thread_success(mock_dependencies):
    """Tests successful creation of a chat thread."""
    route = respx.post(f"{core.BASE_URL}/api/v1/thread").mock(
        return_value=Response(
            200,
            json={"code": "0", "data": {"id": "thread-123"}}
        )
    )
    thread_data = await core.create_chat_thread(
        DEVICE_ID, ACCESS_TOKEN, "agent-id", "Test Thread"
    )
    assert route.called
    assert thread_data["id"] == "thread-123"

@pytest.mark.asyncio
@respx.mock
async def test_upload_file_success(mock_dependencies):
    """Tests successful file upload."""
    route = respx.post(f"{core.BASE_URL}/api/v1/files/upload").mock(
        return_value=Response(
            200,
            json={"code": "0", "data": {"fileId": "file-456", "originalFilename": "test.txt"}}
        )
    )
    file_data = await core.upload_file(
        DEVICE_ID, ACCESS_TOKEN, b"content", "test.txt", "text/plain", "thread-123"
    )
    assert route.called
    assert file_data["fileId"] == "file-456"
