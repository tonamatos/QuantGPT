import streamlit as st
from pathlib import Path
from quantgpt.pdf_parser import extract_components_from_pdf
from quantgpt.llm.mapper import map_components_to_entities, create_risk_report
from quantgpt.knowledge_graph import build_graph_from_sqlite
from quantgpt.llm.client import LLMClient
from quantgpt.config import load_config
from quantgpt.utils.env import load_env
from quantgpt.doc_crawler import link_explorer
from PIL import Image
import time

# Setup
base_path = Path(__file__).resolve().parent
env_path = base_path / ".env"
load_env(dotenv_path=env_path)

st.set_page_config(page_title="QuantGPT Risk Analyzer", layout="wide")

st.title("QuantGPT Risk Analyzer")

# Sidebar
st.sidebar.header("Upload & Settings")
uploaded_pdf = st.sidebar.file_uploader("Upload a PDF", type=["pdf"])
run_crawler = st.sidebar.checkbox("Explore links inside components", value=True)
debug = st.sidebar.checkbox("Debug mode", value=False)
logo = Image.open("images/logo.png")
st.image(logo, width=200)  # centered automatically

gif_runner = st.image("images/loading.gif", width=100)
time.sleep(1)  # to ensure the gif is shown
gif_runner.empty()

if uploaded_pdf:
    # Save uploaded file temporarily
    pdf_path = base_path / "uploaded.pdf"
    with open(pdf_path, "wb") as f:
        f.write(uploaded_pdf.getbuffer())

    with st.spinner("1️⃣ Extracting Components from PDF..."):
        components_data = extract_components_from_pdf(pdf_path, debug=debug)
    
    st.json(components_data)

    # Optional link crawling
    if run_crawler:
        with st.spinner("2️⃣ Exploring Links..."):
            link_explorer(components_data)
            st.json(components_data)

    with st.spinner("3️⃣ Loading Knowledge Graph..."):
        db_path = base_path / "src" / "databases" / "pq_risk.db"
        G = build_graph_from_sqlite(str(db_path))

    with st.spinner("4️⃣ Running LLM Mapping..."):
        cfg = load_config()
        llm = LLMClient(cfg)
        mapping = map_components_to_entities(components_data, G, llm)
        st.json(mapping)

    with st.spinner("5️⃣ Generating Risk Report..."):
        report_path = base_path / "risk_reports" / "risk_report.md"
        create_risk_report(mapping, G, str(report_path))

    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    st.download_button(
        label="Download Risk Report",
        data=report_text,
        file_name="risk_report.md",
        mime="text/markdown"
    )
    st.markdown("### Report Preview")
    st.markdown(report_text)
