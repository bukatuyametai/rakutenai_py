import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Union, IO
import websockets
import time

from . import core


@dataclass
class UploadedFile:
    file_id: str
    file_url: str
    file_name: str
    is_image: bool

class Thread:
    def __init__(self, id: str, user: "User", ws: websockets.WebSocketClientProtocol):
        self.id = id
        self._user = user
        self._ws = ws

    @classmethod
    async def _connect_ws(cls, user: "User") -> websockets.WebSocketClientProtocol:
        ws_path = f"/ws/v1/chat?deviceId={user.device_id}"
        url = await core.get_signed_ws_url(ws_path, user.access_token)
        return await websockets.connect(url)

    @classmethod
    async def connect(cls, id: str, user: "User") -> "Thread":
        ws = await cls._connect_ws(user)
        return cls(id, user, ws)

    async def upload_file(self, file: IO[bytes], filename: str, mime_type: str, is_image: bool = False) -> UploadedFile:
        """Uploads a file to the current thread."""
        file_content = file.read()
        res = await core.upload_file(
            self._user.device_id, self._user.access_token, file_content, filename, mime_type, self.id, is_image
        )
        return UploadedFile(
            file_id=res["fileId"],
            file_url=res["fileUrl"],
            file_name=res["originalFilename"],
            is_image=is_image,
        )

    async def send_message(
        self,
        mode: Literal["USER_INPUT", "DEEP_THINK", "AI_READ"],
        contents: List[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Sends a message and yields the response chunks."""
        message_id = str(uuid.uuid4())
        
        # Convert content format
        formatted_contents = []
        for c in contents:
            if c["type"] == "text":
                formatted_contents.append(
                    {"contentType": "TEXT", "textData": {"text": c["text"]}}
                )
            elif c["type"] == "file":
                file_info: UploadedFile = c["file"]
                if file_info.is_image:
                    formatted_contents.append({
                        "contentType": "INPUT_IMAGE",
                        "inputImageData": {
                            "src": file_info.file_url,
                            "resourceId": file_info.file_id,
                        },
                    })
                else:
                    formatted_contents.append({
                        "contentType": "INPUT_FILE",
                        "inputFileData": {
                            "src": file_info.file_url,
                            "resourceId": file_info.file_id,
                            "name": file_info.file_name,
                        },
                    })

        request_message = {
            "message": {
                "type": "CONVERSATION",
                "payload": {
                    "action": mode,
                    "data": {
                        "chatRequestType": mode,
                        "role": "user",
                        "userId": self._user.device_id,
                        "threadId": self.id,
                        "messageId": message_id,
                        "language": "ja",
                        "platform": "WEB",
                        "timestamp": int(time.time() * 1000),
                        "contents": formatted_contents,
                        "retry": False,
                        "debug": False,
                        "timezoneString": "Asia/Tokyo",
                        "countryCode": "JP",
                        "city": "Nerima",
                        "explicitSearch": "AUTO",
                    },
                },
                "metadata": {"messageId": message_id, "timestamp": int(time.time() * 1000)},
            }
        }
        await self._ws.send(json.dumps(request_message))

        while True:
            try:
                raw_chunk = await self._ws.recv()
                chunk = json.loads(raw_chunk)
                
                ws_data = chunk.get("webSocket", {})

                if ws_data.get("type") == "ACK":
                    yield {"type": "ack"}
                elif ws_data.get("type") == "CONVERSATION":
                    payload = ws_data.get("payload", {})
                    data = payload.get("data", {})
                    status = data.get("chatResponseStatus")
                    
                    if status == "APPEND":
                        for content in data.get("contents", []):
                            content_type = content.get("contentType")
                            if content_type == "TEXT":
                                if payload.get("action") == "EVENT":
                                    if content.get("textData", {}).get("text") == "思考中...":
                                        yield {"type": "reasoning-start"}
                                else:
                                    yield {"type": "text-delta", "text": content.get("textData", {}).get("text", "")}
                            elif content_type == "SUMMARY_TEXT":
                                yield {"type": "reasoning-delta", "text": content.get("textData", {}).get("text", "")}
                            elif content_type == "OUTPUT_IMAGE":
                                image_gens = content.get("outputImageData", {}).get("imageGens", [])
                                if image_gens:
                                    img = image_gens[0]
                                    if "thumbnail" in img:
                                        yield {"type": "image-thumbnail", "url": img["thumbnail"]}
                                    if "preview" in img:
                                        yield {"type": "image", "url": img["preview"]}
                    elif status == "DONE":
                        yield {"type": "done"}
                        return
                elif ws_data.get("type") == "NOTIFICATION":
                    yield {"type": "notification", "data": ws_data.get("payload", {}).get("data")}
            except websockets.exceptions.ConnectionClosed:
                yield {"type": "disconnected"}
                break
            except Exception as e:
                yield {"type": "error", "message": str(e)}
                break

    async def close(self):
        """Closes the WebSocket connection."""
        if not self._ws.closed:
            await self._ws.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class User:
    def __init__(self, device_id: str, access_token: str):
        self.device_id = device_id
        self.access_token = access_token

    @classmethod
    async def create(cls) -> "User":
        """Creates an anonymous user session."""
        device_id = core.generate_device_id()
        token_data = await core.fetch_anonymous_token(device_id)
        return cls(device_id, token_data["accessToken"])

    async def create_thread(self, title: str = "新しいスレッド", scenario_agent_id: str = core.DEFAULT_AGENT_ID) -> Thread:
        """Creates a new chat thread."""
        thread_data = await core.create_chat_thread(
            self.device_id, self.access_token, scenario_agent_id, title
        )
        return await Thread.connect(thread_data["id"], self)
