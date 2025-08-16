from llm.prompt_eng import create_threat_modeling_prompt
from pdf_parser import extract_components_from_pdf
from llm.client import LLMClient
from config import load_config
from utils.env import load_env
from pprint import pprint
from pathlib import Path

base_path = Path(__file__).resolve().parents[2]  # Up from src/quantgpt/
env_path = base_path / ".env"
print(f"Loading .env from: {env_path}")
import os
print("OPENAI_API_KEY loaded:", os.getenv("OPENAI_API_KEY"))
pdf_path = base_path / "technical_design_docs" / "examples" / "cisco_convergeone.pdf"

components_data = extract_components_from_pdf(pdf_path)

prompt = create_threat_modeling_prompt(components_data)

# Load environment and config for OpenAI client
load_env(dotenv_path=env_path)
cfg = load_config()
llm = LLMClient(cfg)

response = llm.chat(prompt)
print("\n--- Assistant Response ---")
pprint(response)

