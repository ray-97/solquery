import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv

async def direct_gemini_test():
    load_dotenv() # Load .env from the current directory (solquery_project)

    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

    if not api_key or "YOUR_GEMINI_API_KEY_FALLBACK" in api_key:
        print("ERROR: GOOGLE_GEMINI_API_KEY is not set or is using a fallback in your .env file.")
        print("Please ensure it's correctly set to your actual API key.")
        return

    print(f"Attempting to configure Gemini with API key (first 5 chars): {api_key[:5]}...")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest') # Use flash for a quicker test

        print("Attempting to stream content...")
        # The error mentions StreamGenerateContent. Let's try a streaming call.
        response_stream = await model.generate_content_async("Tell me a short story about a friendly robot.", stream=True)

        print("Successfully initiated stream. Receiving content:")
        async for chunk in response_stream:
            print(chunk.text, end="")
        print("\nStreaming test successful!")

    except Exception as e:
        print(f"An error occurred during the direct Gemini SDK test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Make sure your .env file is in the same directory as this script,
    # or adjust the load_dotenv path if needed.
    # If your .env is in the parent directory (solquery_project) when running from agent_client:
    # load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
    asyncio.run(direct_gemini_test())