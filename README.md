# rakutenai_py

## The original project does not have a license, so if there are any issues with releasing this port, I will delete it.

`rakutenai_py` is an asynchronous Python client library designed to interact with the Rakuten AI chat service. It provides a convenient way to create anonymous user sessions, manage chat threads, send various types of messages (text, images, files), and receive streaming AI responses.

## Features

*   **Anonymous User Sessions:** Easily create temporary user sessions without explicit authentication.
*   **Chat Thread Management:** Create and manage distinct chat threads for different conversations.
*   **Rich Messaging:** Send text messages, upload images, and other files to the AI.
*   **Streaming Responses:** Receive AI responses in real-time as they are generated.
*   **Simplified Interface:** A high-level `stream_text` function for quick text-based interactions.

## Installation

You can install `rakutenai_py` using `pip`:

```bash
pip install rakutenai_py
```

It is recommended to use `uv` for dependency management for a faster and more reliable experience:

```bash
uv pip install rakutenai_py
```

## Usage

### Basic Text Chat

The simplest way to interact with the AI is using the `stream_text` helper function:

```python
import asyncio
from rakutenai_py import stream_text

async def main():
    print("Starting chat...")
    async for chunk in stream_text("Hello, Rakuten AI! How are you today?"):
        print(chunk, end="", flush=True)
    print("\nChat finished.")

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Usage (with Files and Threads)

For more control, including uploading files or images, you can directly use the `User` and `Thread` classes.

```python
import asyncio
from rakutenai_py import User, Thread, UploadedFile
import os

async def advanced_chat_example():
    # 1. Create an anonymous user
    user = await User.create()
    print(f"User created with device ID: {user.device_id}")

    # 2. Create a new chat thread
    thread = await user.create_thread(title="My Advanced Chat")
    print(f"Thread created with ID: {thread.id}")

    try:
        # 3. Send a text message
        print("\nSending first message (text only):")
        text_contents = [{"type": "text", "text": "What is the capital of France?"}]
        async for chunk in thread.send_message(mode="USER_INPUT", contents=text_contents):
            if chunk["type"] == "text-delta":
                print(chunk["text"], end="", flush=True)
        print("\n")

        # 4. Upload an image (example assumes 'example.jpg' exists in the same directory)
        # For a real scenario, replace with actual image data and filename.
        # Make sure to handle the file path correctly.
        
        # You can create a dummy image for testing if you don't have one:
        # with open("example.jpg", "wb") as f:
        #     f.write(b"dummy image data") # Replace with actual image bytes
        
        image_path = "example.jpg"
        if not os.path.exists(image_path):
             print(f"'{image_path}' not found. Skipping image upload example.")
        else:
            print(f"\nUploading image: {image_path}")
            with open(image_path, "rb") as f:
                uploaded_image = await thread.upload_file(
                    file=f,
                    filename=os.path.basename(image_path),
                    mime_type="image/jpeg", # Adjust MIME type based on your file
                    is_image=True
                )
            print(f"Image uploaded: {uploaded_image.file_url}")

            # 5. Send a message with the uploaded image
            print("\nSending message with image:")
            image_contents = [
                {"type": "text", "text": "What do you see in this image?"},
                {"type": "file", "file": uploaded_image}
            ]
            async for chunk in thread.send_message(mode="USER_INPUT", contents=image_contents):
                if chunk["type"] == "text-delta":
                    print(chunk["text"], end="", flush=True)
                elif chunk["type"] == "image":
                    print(f"\nAI generated image URL: {chunk['url']}")
            print("\n")

    finally:
        # Ensure the thread connection is closed
        await thread.close()
        print("Thread closed.")

if __name__ == "__main__":
    # Create a dummy example.jpg for the advanced example if it doesn't exist
    if not os.path.exists("example.jpg"):
        try:
            from PIL import Image
            img = Image.new('RGB', (60, 30), color = 'red')
            img.save("example.jpg")
            print("Created a dummy example.jpg for advanced usage example.")
        except ImportError:
            print("Pillow not installed. Cannot create dummy image. Please install with `pip install Pillow` to test image upload example.")
            print("Skipping dummy image creation. Please provide your own 'example.jpg' for the advanced usage example.")


    asyncio.run(advanced_chat_example())
```

## Requirements

*   Python 3.8+

## Development

To set up a development environment:

1.  Clone the repository.
2.  Install dependencies: `uv pip install -e .`
3.  Run tests: `pytest`

## Credits
This project is a **Python port** of [rakutenai](https://github.com/evex-dev/rakutenai/tree/main), originally developed in TypeScript. Special thanks to the original authors and all contributors for their great work.
