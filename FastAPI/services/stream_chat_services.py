import os
from stream_chat import StreamChat
from dotenv import load_dotenv

# Load environment variables once when module is imported
load_dotenv()

def get_chat_client():
    """Return initialized Stream Chat client"""
    return StreamChat(
        api_key=os.getenv("STREAM_API_KEY"),
        api_secret=os.getenv("STREAM_API_SECRET")
    )

# Singleton instance
chat_client = get_chat_client()