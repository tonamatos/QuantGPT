# src/quantgpt/llm/mapper.py

import json
from pprint import pprint
from pathlib import Path
from quantgpt.llm.client import LLMClient
from quantgpt.knowledge_graph import KnowledgeGraph, build_graph_from_sqlite
from quantgpt.utils.env import load_env
from quantgpt.lir_helper import get_lir_scores

def map_components_to_entities(components: dict, additional_context: dict, G: KnowledgeGraph, llm: LLMClient, ) -> dict:
    """
    Use the LLM to map components {name: info} -> {name: entity_name} from knowledge graph.
    """
    # Build entity list
    entity_names = [data["props"]["entity_name"] for _, data in G.nodes.items() if data["label"] == "Entity"]

    # Build prompt
    prompt = f"""
        You are given a set of components (with descriptions) and a list of known entities, and some 
        optional additional context. Map each component to the most likely matching entity name.

        Components:
        {json.dumps(components, indent=2)}

        Entities:
        {json.dumps(entity_names, indent=2)}

        Additional context:
        {json.dumps(additional_context, indent=2)}

        Return only JSON of the form:
        {{ "component_name": "entity_name", ... }}
    """

    resp = llm.chat(prompt, system="You are a precise mapping assistant, expert in computer system security.", json_mode=True)
    try:
        mapping = json.loads(resp)
    except Exception:
        mapping = {}
    return mapping


def create_risk_report(mapping: dict, G: KnowledgeGraph, output_path: str):
    """
    Given a mapping {component: entity_name}, query the graph and create a markdown risk report.
    """
    lines = []
    lines.append("# Risk Assessment Report\n")
    lines.append("This report summarizes vulnerabilities and risk assessments for identified components.\n")

    # Table header
    lines.append("| Component (Entity) | Vulnerabilities | L | I | R | Risk Assessments |")
    lines.append("|---------------------|-----------------|---|---|---|------------------|")

    for comp, entity in mapping.items():
        vulns = G.get_vulnerabilities(entity)
        risks = G.get_risk_assessments(entity)




        # Format vulnerabilities
        if vulns:
            vuln_lines = []
            for v in vulns:
                # Sometimes the DB gives the whole thing as a single JSON string
                raw = v.get("vuln_type") or v.get("description") or str(v)

                # Only try parsing if it looks like JSON
                if isinstance(raw, str) and raw.strip().startswith("{"):
                    try:
                        # Normalize curly quotes to standard quotes
                        normalized = raw.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
                        parsed = json.loads(normalized)

                        # Make sure we got a dictionary
                        if isinstance(parsed, dict):
                            for kind, desc in parsed.items():
                                vuln_lines.append(f"**{kind}:** {desc}")
                        else:
                            vuln_lines.append(raw)
                    except json.JSONDecodeError:
                        vuln_lines.append(raw)  # fallback if parsing fails
                else:
                    vuln_lines.append(str(raw))

            vuln_str = "<br><br>".join(vuln_lines)  # single <br> per line is enough
        else:
            vuln_str = "—"



        #Obtaining LIR scores
        risk_lines = []
        likelihood = impact = overall = "N/A"

        for r in risks:
            # --- LIR ---
            assessment_id = r.get("assessment_id")
            lir_scores = get_lir_scores(assessment_id, 'src/databases/pq_risk.db')
            if isinstance(lir_scores, tuple):
                likelihood, impact, overall = lir_scores

            # --- STRIDE text formatting ---
            stride_json = r.get("quant_stride")
            if stride_json:
                try:
                    stride_dict = json.loads(stride_json)
                    for category, text in stride_dict.items():
                        risk_lines.append(f"**{category}**: {text}")
                except Exception:
                    risk_lines.append(str(stride_json))

        risk_column = "<br><br>".join(risk_lines) if risk_lines else "—"

        lines.append(f"| {comp} ({entity}) | {vuln_str} | {likelihood} | {impact} | {overall} | {risk_column} |")

    # Write file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Risk report saved to {output_path}")


if __name__ == "__main__":
    base_path = Path(__file__).resolve().parents[3]  # Up from src/quantgpt/llm/
    env_path = base_path / ".env"
    print(env_path)
    #load_env(dotenv_path=env_path)
    import os
    pdf_path = base_path / "technical_design_docs" / "examples" / "cisco_convergeone.pdf"

    # Example demo
    db_path = "databases/pq_risk.db"
    G = build_graph_from_sqlite(db_path)
    llm = LLMClient(cfg={})  # will use env variables

    # Dummy components
    components = {
        "TLS Handshake": "secure communication setup",
        "Kyber-768": "a post-quantum key exchange algorithm",
        "X.509 Cert": "certificate used in authentication"
    }

    # Step 1: Map components
    mapping = map_components_to_entities(components, G, llm)
    pprint(mapping)

    # Step 2: Create risk report
    report_path = str(base_path / "risk_reports" / "risk_report.md")
    create_risk_report(mapping, G, report_path)