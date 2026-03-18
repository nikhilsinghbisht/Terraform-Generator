import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

MODEL = "deepseek-chat"
MAX_TOKENS = 8000