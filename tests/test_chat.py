import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from rakutenai_py.chat import User, Thread, UploadedFile

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_core(mocker):
    """Mocks the entire core module."""
    mocked_core = mocker.patch("rakutenai_py.chat.core")

    mocked_core.generate_device_id.return_value = "mock-device-id"
    mocked_core.fetch_anonymous_token = AsyncMock(return_value={"accessToken": "mock-access-token"})
    mocked_core.create_chat_thread = AsyncMock(return_value={"id": "mock-thread-id"})
    mocked_core.upload_file = AsyncMock()

    return mocked_core

@pytest.fixture
def mock_websocket_connect(mocker):
    """Mocks websockets.connect to return a mock WebSocket client."""
    mock_ws = AsyncMock()
    # Configure the mock to be an async iterator
    mock_ws.__aiter__.return_value = [
        # Simulate server responses
        json.dumps({"webSocket": {"type": "ACK"}}),
        json.dumps({
            "webSocket": {
                "type": "CONVERSATION",
                "payload": {
                    "data": {
                        "chatResponseStatus": "APPEND",
                        "contents": [{"contentType": "TEXT", "textData": {"text": "Hello "}}]
                    }
                }
            }
        }),
        json.dumps({
            "webSocket": {
                "type": "CONVERSATION",
                "payload": {
                    "data": {
                        "chatResponseStatus": "APPEND",
                        "contents": [{"contentType": "OUTPUT_IMAGE", "outputImageData": {"imageGens": [{"thumbnail": "thumb.url", "preview": "preview.url"}]}}]
                    }
                }
            }
        }),
        json.dumps({
            "webSocket": {
                "type": "CONVERSATION",
                "payload": {"data": {"chatResponseStatus": "DONE"}}
            }
        }),
    ]

    # Patch the connect function
    mocker.patch("websockets.connect", return_value=mock_ws)
    return mock_ws


async def test_user_create(mock_core):
    """Tests the User.create classmethod."""
    user = await User.create()
    
    mock_core.generate_device_id.assert_called_once()
    mock_core.fetch_anonymous_token.assert_awaited_once_with("mock-device-id")
    
    assert user.device_id == "mock-device-id"
    assert user.access_token == "mock-access-token"

async def test_user_create_thread(mock_core, mock_websocket_connect):
    """Tests the User.create_thread method."""
    user = User("mock-device-id", "mock-access-token")
    
    # We need to patch Thread.connect to avoid real WS connection
    with patch("rakutenai_py.chat.Thread.connect", new_callable=AsyncMock) as mock_thread_connect:
        await user.create_thread(title="My Test")
        
        mock_core.create_chat_thread.assert_awaited_once_with(
            "mock-device-id", "mock-access-token", "6812e64f9dfaf301f7000001", "My Test"
        )
        mock_thread_connect.assert_called_once_with("mock-thread-id", user)


async def test_thread_send_message_parses_chunks(mock_core):
    """Tests that Thread.send_message correctly parses different event types."""
    
    # Setup a mock websocket that yields our predefined chunks
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = [
        json.dumps({"webSocket": {"type": "ACK"}}),
        json.dumps({
            "webSocket": {"type": "CONVERSATION", "payload": {"action": "EVENT", "data": {"chatResponseStatus": "APPEND", "contents": [{"contentType": "TEXT", "textData": {"text": "思考中..."}}]}}}
        }),
        json.dumps({
            "webSocket": {"type": "CONVERSATION", "payload": {"data": {"chatResponseStatus": "APPEND", "contents": [{"contentType": "TEXT", "textData": {"text": "Hello "}}]}}}
        }),
        json.dumps({
            "webSocket": {"type": "CONVERSATION", "payload": {"data": {"chatResponseStatus": "APPEND", "contents": [{"contentType": "SUMMARY_TEXT", "textData": {"text": "World"}}]}}}
        }),
        json.dumps({
            "webSocket": {"type": "CONVERSATION", "payload": {"data": {"chatResponseStatus": "APPEND", "contents": [{"contentType": "OUTPUT_IMAGE", "outputImageData": {"imageGens": [{"thumbnail": "thumb.url", "preview": "preview.url"}]}}]}}}
        }),
        json.dumps({
            "webSocket": {"type": "CONVERSATION", "payload": {"data": {"chatResponseStatus": "DONE"}}}
        }),
    ]

    user = User("dev-id", "token")
    thread = Thread("thread-id", user, mock_ws)
    
    # Collect all yielded chunks
    chunks = [chunk async for chunk in thread.send_message("USER_INPUT", [])]
    
    # Assert that the correct chunks were yielded
    expected_chunks = [
        {"type": "ack"},
        {"type": "reasoning-start"},
        {"type": "text-delta", "text": "Hello "},
        {"type": "reasoning-delta", "text": "World"},
        {"type": "image-thumbnail", "url": "thumb.url"},
        {"type": "image", "url": "preview.url"},
        {"type": "done"},
    ]
    
    assert chunks == expected_chunks
    
    # Check that the websocket was sent a message
    mock_ws.send.assert_called_once()
    sent_data = json.loads(mock_ws.send.call_args[0][0])
    assert sent_data["message"]["payload"]["data"]["threadId"] == "thread-id"

async def test_thread_upload_file(mock_core):
    """Tests the thread's upload_file method."""
    mock_core.upload_file.return_value = {
        "fileId": "file-123",
        "fileUrl": "http://example.com/file.txt",
        "originalFilename": "test.txt"
    }

    user = User("dev-id", "token")
    thread = Thread("thread-id", user, AsyncMock())  # WS not used in this test

    try:
        with open("test.txt", "wb") as f:
            f.write(b"dummy content")

        with open("test.txt", "rb") as f:
            uploaded_file = await thread.upload_file(f, "test.txt", "text/plain")

        mock_core.upload_file.assert_awaited_once()
        # Check some args passed to the core function
        call_args = mock_core.upload_file.call_args[0]
        assert call_args[0] == "dev-id"
        assert call_args[2] == b"dummy content"
        assert call_args[4] == "text/plain"

        assert isinstance(uploaded_file, UploadedFile)
        assert uploaded_file.file_id == "file-123"
        assert uploaded_file.file_name == "test.txt"
    finally:
        if os.path.exists("test.txt"):
            os.remove("test.txt")

