import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Finance Dashboard API"
APP_VERSION = "1.0.0"

SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-32chars!!")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finance.db")
