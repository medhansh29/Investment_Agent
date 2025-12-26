import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    @classmethod
    def validate(cls):
        """Validates that necessary environment variables are set."""
        missing = []
        if not cls.ALPACA_API_KEY:
            missing.append("ALPACA_API_KEY")
        if not cls.ALPACA_SECRET_KEY:
            missing.append("ALPACA_SECRET_KEY")
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.SMTP_EMAIL:
            missing.append("SMTP_EMAIL")
        if not cls.SMTP_PASSWORD:
            missing.append("SMTP_PASSWORD")
            
        if missing:
            print(f"Warning: The following environment variables are missing: {', '.join(missing)}")
            print("Please create a .env file based on .env.example")
            return False
        return True
