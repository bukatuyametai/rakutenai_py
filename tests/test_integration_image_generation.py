import pytest
import asyncio
from rakutenai_py.chat import User

# This test connects to the actual Rakuten AI service.
# It is marked as 'integration' and should be run selectively.
# To run, use: pytest -m integration
@pytest.mark.integration
@pytest.mark.asyncio
async def test_image_generation():
    """
    Tests the image generation capability by connecting to the live service.
    """
    prompt = "かわいい犬の絵を描いて"
    print("\n--- Running Integration Test: Image Generation ---")
    print(f"🖼️  Sending image generation prompt: '{prompt}'")
    
    generated_image_url = None
    
    try:
        user = await User.create()
        async with await user.create_thread(title="Integration Image Test") as thread:
            print(f"✅ Live thread created: {thread.id}")

            contents = [{"type": "text", "text": prompt}]
            
            async for chunk in thread.send_message("USER_INPUT", contents):
                chunk_type = chunk.get("type")
                print(f"  -> Received chunk: {chunk_type}")

                if chunk_type == "image":
                    generated_image_url = chunk.get("url")
                    print(f"🎨 Final image URL found: {generated_image_url}")
                
                if chunk_type == "done":
                    print("✅ Stream finished.")
                    break
        
        assert generated_image_url is not None, "Did not receive a final image URL."
        assert generated_image_url.startswith("https://"), "Image URL does not look valid."

    except Exception as e:
        pytest.fail(f"An exception occurred during the integration test: {e}")

    print("--- Integration Test Finished ---")

if __name__ == "__main__":
    asyncio.run(test_image_generation())