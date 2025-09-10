# src/quantgpt/interface.py

from pathlib import Path
import os
from quantgpt.utils.env import load_env

# Load environment variables first
base_path = Path(__file__).resolve().parents[2]
load_env(dotenv_path=base_path / ".env")

print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))  # sanity check

# Now you can safely import modules that use LLMClient
import gradio as gr
import asyncio
from pprint import pprint
from quantgpt.config import load_config
from quantgpt.llm.client import LLMClient
from quantgpt.pdf_parser import extract_components_from_pdf, extract_text_with_links
from quantgpt.knowledge_graph import build_graph_from_sqlite
from quantgpt.llm.unstructured_text_parser import parse_pdf_async
from quantgpt.llm.mapper import map_components_to_entities, create_risk_report
from quantgpt.doc_crawler import link_explorer


# Initialize config, LLM client, and knowledge graph
cfg = load_config()
llm = LLMClient(cfg)
db_path = base_path / "src" / "databases" / "pq_risk.db"
G = build_graph_from_sqlite(str(db_path))


async def run_quantgpt(pdf_file_path: str, ask_additional_context: str = "") -> str:
    """
    Runs the QuantGPT pipeline on the uploaded PDF and optional user-provided context.
    Returns a human-readable Markdown string.
    """
    pdf_path = Path(pdf_file_path)
    components_data = extract_components_from_pdf(pdf_path)
    raw_text_with_links = extract_text_with_links(pdf_path)

    # Parse unstructured text
    pdf_context_model = await parse_pdf_async(pdf_path)
    additional_context = pdf_context_model.model_dump()

    # Merge user-provided context if any
    if ask_additional_context.strip():
        additional_context["user_input"] = ask_additional_context

    # Explore links to enrich context
    link_explorer(components_data)  # updates in place

    # Map components to entities
    mapping = map_components_to_entities(components_data, additional_context, G, llm)

    # Create risk report in Markdown
    report_path = base_path / "risk_reports" / f"risk_report_{pdf_path.stem}.md"
    create_risk_report(mapping, G, str(report_path))

    # Optionally, return the Markdown content as a string for display in Gradio
    with open(report_path, "r") as f:
        report_md = f.read()

    return report_md


def launch_interface():
    """
    Launch a Gradio web interface for QuantGPT.
    """
    with gr.Blocks() as demo:
        gr.Markdown("# QuantGPT: Quantum Risk Assessment")
        with gr.Row():
            pdf_input = gr.File(label="Upload TDD PDF", file_types=[".pdf"])
        context_input = gr.Textbox(
            label="Optional Additional Context",
            placeholder="Add any context about deployment, crypto usage, etc."
        )
        output_md = gr.Textbox(
            label="Risk Report (Markdown)",
            placeholder="The output risk assessment will appear here.",
            lines=30
        )
        run_button = gr.Button("Run QuantGPT")

        # Define the action
        run_button.click(
            fn=lambda pdf, ctx: asyncio.run(run_quantgpt(pdf.name, ctx)),
            inputs=[pdf_input, context_input],
            outputs=[output_md]
        )

    demo.launch()


if __name__ == "__main__":
    launch_interface()
