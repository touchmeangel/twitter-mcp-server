import os

from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("APP_HOST") or "127.0.0.1"
PORT = os.getenv("APP_PORT") or "3000"
