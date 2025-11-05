from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

# Project root = directory containing run.py
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
ENV_PATH = PROJECT_ROOT / ".env"
NLTK_PATH = PROJECT_ROOT/"nltk_data"
load_dotenv(dotenv_path=ENV_PATH)

#importing mongo
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME=os.getenv("DB_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


client = AsyncIOMotorClient(MONGO_URI,server_api = ServerApi("1"))
db=  client[DB_NAME]