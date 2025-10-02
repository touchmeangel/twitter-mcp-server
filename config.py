from dotenv import load_dotenv
import os

load_dotenv()

HOST = os.getenv("APP_HOST") or "0.0.0.0"
PORT = os.getenv("APP_PORT") or "8080"