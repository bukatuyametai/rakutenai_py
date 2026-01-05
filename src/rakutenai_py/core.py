import asyncio
import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, urlunparse

import httpx

# Constants
BASE_URL = "https://ai.rakuten.co.jp"
WS_BASE_URL = "wss://companion.ai.rakuten.co.jp"
SECRET_KEY = "4f0465bfea7761a510dda451ff86a935bf0c8ed6fb37f80441509c64328788c8"
DEFAULT_AGENT_ID = "6812e64f9dfaf301f7000001"


def generate_device_id() -> str:
    """Generates a random device ID."""
    random_part = "".join(
        str(uuid.uuid4()).split("-")[0:2]
    )  # A bit different from JS but should be fine
    return f"{uuid.uuid4()}-{random_part[:6]}"


def generate_nonce() -> str:
    """Generates a random nonce."""
    return str(uuid.uuid4())


async def generate_signature(message: str, secret: str) -> str:
    """Generates HMAC-SHA256 signature."""
    key_bytes = secret.encode("utf-8")
    message_bytes = message.encode("utf-8")
    signature_bytes = hmac.new(key_bytes, message_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature_bytes).rstrip(b"=").decode("utf-8")


async def get_signed_headers(
    method: str, url_path: str, params: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Assembles signed headers for an HTTP request."""
    params = params or {}
    timestamp = str(int(time.time()))
    nonce = generate_nonce()

    sorted_params = "".join(
        f"{key}={value}" for key, value in sorted(params.items())
    )

    raw_string = f"{method.upper()}{url_path}{sorted_params}{timestamp}{nonce}"
    signature = await generate_signature(raw_string, SECRET_KEY)

    return {
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }


async def fetch_anonymous_token(device_id: str) -> Dict[str, Any]:
    """Fetches an anonymous authentication token."""
    endpoint = "/api/v2/auth/anonymous"
    url = f"{BASE_URL}{endpoint}"
    signed_headers = await get_signed_headers("GET", endpoint)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={
                "Content-Type": "application/json",
                "X-Platform": "WEB",
                "X-Country-Code": "JP",
                "Device-ID": device_id,
                **signed_headers,
            },
        )
        response.raise_for_status()
        result = response.json()

    if result.get("code") != "0":
        raise Exception(result.get("message", "Authentication Failed"))

    return result["data"]


async def get_signed_ws_url(path: str, access_token: str) -> str:
    """Generates a signed URL for WebSocket connection."""
    timestamp = str(int(time.time()))
    nonce = generate_nonce()
    method = "GET"

    parsed_url = urlparse(f"{WS_BASE_URL}{path}")
    
    query_params = {
        "accessToken": access_token,
        "platform": "WEB",
    }
    
    # Sort params for signature
    sorted_param_string = "".join(
        f"{key}={value}" for key, value in sorted(query_params.items())
    )

    raw_string = f"{method}{parsed_url.path}{sorted_param_string}{timestamp}{nonce}"
    signature = await generate_signature(raw_string, SECRET_KEY)

    # Add signature params to the final URL
    query_params.update({
        "x-timestamp": timestamp,
        "x-nonce": nonce,
        "x-signature": signature,
    })

    return urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            "",
            urlencode(query_params),
            "",
        )
    )

async def create_chat_thread(
    device_id: str, token: str, scenario_agent_id: str, title: str
) -> Dict[str, Any]:
    """Creates a new chat thread."""
    endpoint = "/api/v1/thread"
    url = f"{BASE_URL}{endpoint}"
    signed_headers = await get_signed_headers("POST", endpoint)

    request_data = {
        "scenarioAgentId": scenario_agent_id,
        "title": title,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-Platform": "WEB",
                "X-Country-Code": "JP",
                "Device-ID": device_id,
                **signed_headers,
            },
            json=request_data,
        )
        response.raise_for_status()
        result = response.json()

    if result.get("code") != "0":
        raise Exception(result.get("message", "Failed to create thread"))

    return result["data"]

async def upload_file(
    device_id: str, token: str, file: bytes, filename: str, mime_type: str, thread_id: str, is_image: bool = False
) -> Dict[str, Any]:
    """Uploads a file."""
    endpoint = "/api/v1/files/upload"
    url = f"{BASE_URL}{endpoint}"
    signed_headers = await get_signed_headers("POST", endpoint)

    request_json = {
        "type": "VISION_DATA" if is_image else "USER_DATA",
        "agentId": DEFAULT_AGENT_ID,
        "threadId": thread_id,
    }
    
    files = {
        "file": (filename, file, mime_type),
        "request": ("blob", json.dumps(request_json), "application/json"),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Platform": "WEB",
                "X-Country-Code": "JP",
                "Device-ID": device_id,
                **signed_headers,
            },
            files=files,
        )
        response.raise_for_status()
        result = response.json()
        
    if result.get("code") != "0":
        raise Exception(result.get("message", "Failed to upload file"))
        
    return result["data"]
