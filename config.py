# config.py (Updated)
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Gemini API key
GEMINI_API_KEY = "AIzaSyAbslAPa6hOH6caH6lLqbkOap0v_Ktf1co"

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please set it in the .env file.")