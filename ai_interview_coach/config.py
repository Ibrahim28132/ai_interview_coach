import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DB_PATH = Path(__file__).parent / "data" / "interviews.db"
    QUESTION_BANKS_DIR = Path(__file__).parent / "question_banks"
    VOICE_ENABLED = True
    WEB_INTERFACE = True
    WEBSOCKET_HOST = "localhost"
    WEBSOCKET_PORT = 8765
    STORAGE_DIR = Path("interview_data")  # Directory to store all interviews

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment variables")