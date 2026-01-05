import asyncio
import sys
import os

# Ensure the rakutenai_py package is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rakutenai_py import User

async def main():
    """
    Tests the image generation capability of the Rakuten AI client.
    """
    prompt = "かわいい猫の絵を描いて"
    print(f"🖼️  Sending image generation prompt: '{prompt}'")
    print("-" * 20)

    try:
        # Use async with for automatic resource management (user login and thread creation)
        async with await User.create() as user:
            async with await user.create_thread(title="Image Generation Test") as thread:
                print(f"✅ Thread created: {thread.id}")

                contents = [{"type": "text", "text": prompt}]

                # Send the message and iterate through the response stream
                async for chunk in thread.send_message("USER_INPUT", contents):
                    chunk_type = chunk.get("type")

                    if chunk_type == "ack":
                        print("✔️  Message acknowledged by server.")
                    elif chunk_type == "reasoning-start":
                        print("🤔 AI is starting to think...")
                    elif chunk_type == "reasoning-delta":
                        print(f"🧠 Thinking: {chunk.get('text', '')}")
                    elif chunk_type == "text-delta":
                        print(f"💬 Text: {chunk.get('text', '')}", end="", flush=True)
                    elif chunk_type == "image-thumbnail":
                        print(f"\n🖼️  Thumbnail generated: {chunk.get('url')}")
                    elif chunk_type == "image":
                        print(f"🎨 Final image generated: {chunk.get('url')}")
                    elif chunk_type == "done":
                        print("\n\n✅ Stream finished.")
                        break
                    elif chunk_type == "disconnected":
                        print("❌ Connection closed unexpectedly.")
                        break
                    elif chunk_type == "error":
                        print(f"🔥 An error occurred: {chunk.get('message')}")
                        break
                    else:
                        # Print any other event types for debugging
                        print(f"\n[DEBUG] Event: {chunk}")
    
    except Exception as e:
        print(f"\n🚨 An exception occurred during the test: {e}")

if __name__ == "__main__":
    # To run this test, you need to have the dependencies installed.
    # From the root directory of the `rakutenai` project, run:
    # pip install -e ./rakutenai_py
    # Then run this script:
    # python rakutenai_py/image_generation_test.py
    
    asyncio.run(main())
