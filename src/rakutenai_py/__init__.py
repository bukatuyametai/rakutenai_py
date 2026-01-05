from .chat import User, Thread, UploadedFile
from typing import AsyncGenerator, Literal, List, Dict, Any

__all__ = ["User", "Thread", "UploadedFile", "stream_text"]

async def stream_text(
    prompt: str,
    mode: Literal["USER_INPUT", "DEEP_THINK"] = "USER_INPUT",
) -> AsyncGenerator[str, None]:
    """
    A simple helper function to stream text responses for a given prompt.

    This function handles user creation, thread creation, and message sending,
    yielding only the text content from the AI's response.

    Usage:
        async for text in stream_text("Hello, Rakuten AI!"):
            print(text, end="")
    """
    user = None
    thread = None
    try:
        user = await User.create()
        thread = await user.create_thread()
        
        contents = [{"type": "text", "text": prompt}]
        
        async for chunk in thread.send_message(mode=mode, contents=contents):
            if chunk["type"] == "text-delta":
                yield chunk["text"]
            elif chunk["type"] == "done":
                break
    finally:
        if thread:
            await thread.close()
