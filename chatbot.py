# pip install python-dotenv openai
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # loads .env into the process env

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Set OPENAI_API_KEY in your environment")

client = OpenAI(api_key=api_key)  # or rely on env-only: client = OpenAI()
