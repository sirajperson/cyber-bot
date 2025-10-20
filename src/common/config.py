import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
import sys
load_dotenv(".env")

class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    BASE_URL = "https://cyberskyline.com/competition/dashboard"
