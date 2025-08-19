# src/quantgpt/main.py

from quantgpt.llm.prompt_eng import create_threat_modeling_prompt
from quantgpt.pdf_parser import extract_components_from_pdf
from quantgpt.llm.client import LLMClient
from quantgpt.config import load_config
from quantgpt.utils.env import load_env
from quantgpt.llm.mapper import map_components_to_entities, create_risk_report
from quantgpt.knowledge_graph import build_graph_from_sqlite
from pprint import pprint
from pathlib import Path
import os

def run(filename: str, debug: bool = False):
  """Run the QuantGPT pipeline on the given PDF filename (relative to technical_design_docs)."""
  base_path = Path(__file__).resolve().parents[2]  # Up from src/quantgpt/
  env_path = base_path / ".env"
  if debug: print(f"Loading .env from: {env_path}")
  load_env(dotenv_path=env_path)
  if debug: print("OPENAI_API_KEY loaded:", os.getenv("OPENAI_API_KEY"))

  pdf_path = base_path / "technical_design_docs" / filename
  print(f"Processing PDF: {pdf_path}")

  components_data = extract_components_from_pdf(pdf_path, debug=debug)

  print("\n--- Extracted Components ---")
  if debug: pprint(components_data)

  # Load the knowledge graph
  db_path = base_path / "src" / "databases" / "pq_risk.db"
  if debug: print("Loading knowledge graph from:", db_path)
  G = build_graph_from_sqlite(str(db_path))

  # Load config and initialize LLM client
  cfg = load_config()
  llm = LLMClient(cfg)

  # Map components to entities
  mapping = map_components_to_entities(components_data, G, llm)
  print("\n--- Component to Entity Mapping ---")
  pprint(mapping)

  # Create risk report
  report_path = base_path / "risk_reports" / f"risk_report_{filename}.md"
  create_risk_report(mapping, G, str(report_path))
  print(f"Risk report saved to: {report_path}")
