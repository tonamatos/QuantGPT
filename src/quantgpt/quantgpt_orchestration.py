"""
QuantGPT Orchestration with Proper Semantic Kernel Integration
==============================================================
This version properly uses Semantic Kernel's function calling and orchestration.

Authors: Dr. Aaron Crighton, Dr. David Jaramillo-Martinez, 
         Tonatiuh Matos-Wiederhold, Dr. Ethan Ross
Developed at: Fields Institute for Research in Mathematical Sciences
In partnership with: Scotiabank
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional, Union, Annotated
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

# Semantic Kernel imports
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.functions import kernel_function, KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.prompt_template import PromptTemplateConfig
# from semantic_kernel.planners import FunctionCallingStepwisePlanner  # Not available in this version
# from semantic_kernel.planners.function_calling_stepwise_planner import FunctionCallingStepwisePlannerOptions  # Not available in this version

# QuantGPT imports
from quantgpt.pdf_parser import extract_components_from_pdf, extract_text_with_links
from quantgpt.doc_crawler import link_explorer
from quantgpt.knowledge_graph import KnowledgeGraph, build_graph_from_sqlite
from quantgpt.config import load_config
from quantgpt.utils.env import load_env
from quantgpt.lir_helper import get_lir_scores

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# OPENROUTER CONNECTOR FOR SEMANTIC KERNEL
# ============================================================================

class OpenRouterChatCompletion(ChatCompletionClientBase):
    """
    OpenRouter connector that properly integrates with Semantic Kernel.
    Implements the ChatCompletionClientBase interface.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        ai_model_id: str = "openai/gpt-4",
        service_id: Optional[str] = None,
    ):
        """Initialize OpenRouter connector."""
        super().__init__(
            ai_model_id=ai_model_id,
            service_id=service_id or "openrouter"
        )
        object.__setattr__(self, 'api_key', api_key or os.getenv("OPENROUTER_API_KEY"))
        if not self.api_key:
            raise ValueError("OpenRouter API key required")
        
        # Use OpenAI client with OpenRouter base URL
        import openai
        object.__setattr__(self, 'client', openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/quantgpt",
                "X-Title": "QuantGPT"
            }
        ))
    
    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs
    ):
        """Get chat completions from OpenRouter."""
        messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in chat_history.messages
        ]
        
        response = await self.client.chat.completions.create(
            model=self.ai_model_id,
            messages=messages,
            temperature=settings.temperature if settings else 0.7,
            max_tokens=settings.max_tokens if settings else 2048,
            **kwargs
        )
        
        from semantic_kernel.contents import ChatMessageContent, AuthorRole
        return [ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content=response.choices[0].message.content
        )]

# ============================================================================
# SEMANTIC KERNEL PLUGINS WITH PROPER FUNCTION CALLING
# ============================================================================

class PDFAnalysisPlugin:
    """
    PDF Analysis Plugin that properly works with Semantic Kernel's function calling.
    Each function is decorated with @kernel_function and has proper type hints.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._cache = {}
    
    @kernel_function(
        name="extract_pdf_components",
        description="Extracts technical components from a PDF document"
    )
    def extract_pdf_components(
        self,
        pdf_path: Annotated[str, "Path to the PDF file"]
    ) -> Annotated[str, "JSON string of extracted components"]:
        """Extract components from PDF."""
        try:
            components = extract_components_from_pdf(pdf_path, self.debug)
            return json.dumps(components)
        except Exception as e:
            logger.error(f"Error extracting components: {e}")
            return json.dumps({"error": str(e)})
    
    @kernel_function(
        name="extract_pdf_text",
        description="Extracts text content with embedded hyperlinks from PDF"
    )
    def extract_pdf_text(
        self,
        pdf_path: Annotated[str, "Path to the PDF file"]
    ) -> Annotated[str, "Extracted text with markdown links"]:
        """Extract text with links from PDF."""
        try:
            text = extract_text_with_links(pdf_path)
            return text
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return f"Error: {str(e)}"
    
    @kernel_function(
        name="enrich_components_with_links",
        description="Explores hyperlinks in components to gather additional context"
    )
    def enrich_components_with_links(
        self,
        components_json: Annotated[str, "JSON string of components"]
    ) -> Annotated[str, "Enriched components JSON"]:
        """Enrich components by exploring their links."""
        try:
            components = json.loads(components_json)
            link_explorer(components)  # Updates in place
            return json.dumps(components)
        except Exception as e:
            logger.error(f"Error exploring links: {e}")
            return json.dumps({"error": str(e)})

class RiskAssessmentPlugin:
    """
    Risk Assessment Plugin for Semantic Kernel with proper function signatures.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(__file__).parents[1] / "databases" / "pq_risk.db")
        self.graph = build_graph_from_sqlite(self.db_path)
    
    @kernel_function(
        name="map_to_knowledge_graph",
        description="Maps components to entities in the quantum vulnerability knowledge graph"
    )
    def map_to_knowledge_graph(
        self,
        components_json: Annotated[str, "JSON string of components"],
        context: Annotated[str, "Additional context for mapping"] = ""
    ) -> Annotated[str, "JSON mapping of components to entities"]:
        """Map components to knowledge graph entities."""
        try:
            components = json.loads(components_json)
            
            # Get available entities
            entity_names = [
                data["props"]["entity_name"]
                for _, data in self.graph.nodes.items()
                if data["label"] == "Entity"
            ]
            
            # Create mapping (simplified for SK integration)
            mapping = {}
            for comp_name in components.keys():
                # Find best match (simplified logic)
                for entity in entity_names:
                    if any(word.lower() in entity.lower() 
                           for word in comp_name.split()):
                        mapping[comp_name] = entity
                        break
                if comp_name not in mapping:
                    mapping[comp_name] = "Unknown"
            
            return json.dumps(mapping)
        except Exception as e:
            logger.error(f"Error mapping components: {e}")
            return json.dumps({"error": str(e)})
    
    @kernel_function(
        name="assess_quantum_risks",
        description="Assesses quantum computing risks for mapped components"
    )
    def assess_quantum_risks(
        self,
        mapping_json: Annotated[str, "JSON mapping of components to entities"]
    ) -> Annotated[str, "Risk assessment results in JSON"]:
        """Assess quantum risks for components."""
        try:
            mapping = json.loads(mapping_json)
            assessments = []
            
            for comp, entity in mapping.items():
                vulns = self.graph.get_vulnerabilities(entity)
                risks = self.graph.get_risk_assessments(entity)
                
                risk_level = "low"
                if any('Shor' in str(v.get('vuln_type', '')) for v in vulns):
                    risk_level = "high"
                elif vulns:
                    risk_level = "medium"
                
                assessments.append({
                    'component': comp,
                    'entity': entity,
                    'risk_level': risk_level,
                    'vulnerabilities': len(vulns),
                    'assessments': len(risks)
                })
            
            return json.dumps(assessments)
        except Exception as e:
            logger.error(f"Error assessing risks: {e}")
            return json.dumps({"error": str(e)})
    
    @kernel_function(
        name="generate_risk_report",
        description="Generates a markdown risk assessment report"
    )
    def generate_risk_report(
        self,
        assessments_json: Annotated[str, "JSON risk assessments"],
        mapping_json: Annotated[str, "JSON mapping of components to entities"],
        output_path: Annotated[str, "Path for the report file"] = "risk_report.md"
    ) -> Annotated[str, "Path to generated report"]:
        """Generate markdown risk report with table format matching mapper.py."""
        try:
            assessments = json.loads(assessments_json)
            mapping = json.loads(mapping_json)
            
            lines = ["# Risk Assessment Report\n"]
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            lines.append("This report summarizes vulnerabilities and risk assessments for identified components.\n")
            
            # Summary section
            high_risk = [a for a in assessments if a['risk_level'] == 'high']
            medium_risk = [a for a in assessments if a['risk_level'] == 'medium']
            low_risk = [a for a in assessments if a['risk_level'] == 'low']
            
            lines.append("## Summary\n")
            lines.append(f"- High Risk: {len(high_risk)} components")
            lines.append(f"- Medium Risk: {len(medium_risk)} components")
            lines.append(f"- Low Risk: {len(low_risk)} components\n")
            
            # Table header matching mapper.py format
            lines.append("## Component Details\n")
            lines.append("| Component (Entity) | Vulnerabilities | L | I | R | Risk Assessments |")
            lines.append("|---------------------|-----------------|---|---|---|------------------|")
            
            # Process each component
            for comp, entity in mapping.items():
                vulns = self.graph.get_vulnerabilities(entity)
                risks = self.graph.get_risk_assessments(entity)
                
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
                                normalized = raw.replace(""", '"').replace(""", '"').replace("'", "'").replace("'", "'")
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
                    
                    vuln_str = "<br><br>".join(vuln_lines)
                else:
                    vuln_str = "—"
                
                # Obtaining LIR scores and formatting risk assessments
                risk_lines = []
                likelihood = impact = overall = "—"
                
                for r in risks:
                    # Get LIR scores
                    assessment_id = r.get("assessment_id")
                    if assessment_id:
                        try:
                            lir_scores = get_lir_scores(assessment_id, self.db_path)
                            if isinstance(lir_scores, tuple) and len(lir_scores) == 3:
                                likelihood, impact, overall = lir_scores
                        except Exception as e:
                            logger.debug(f"Could not get LIR scores: {e}")
                    
                    # STRIDE text formatting
                    stride_json = r.get("quant_stride")
                    if stride_json:
                        try:
                            stride_dict = json.loads(stride_json)
                            for category, text in stride_dict.items():
                                risk_lines.append(f"**{category}**: {text}")
                        except Exception:
                            risk_lines.append(str(stride_json))
                
                risk_column = "<br><br>".join(risk_lines) if risk_lines else "—"
                
                # Add row to table
                lines.append(f"| {comp} ({entity}) | {vuln_str} | {likelihood} | {impact} | {overall} | {risk_column} |")
            
            # Save report
            report_path = Path(output_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("\n".join(lines), encoding="utf-8")
            
            return str(report_path.absolute())
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Error: {str(e)}"

class OrchestrationPlugin:
    """
    Orchestration plugin that coordinates the analysis workflow.
    """
    
    @kernel_function(
        name="orchestrate_pdf_analysis",
        description="Orchestrates the complete PDF analysis workflow"
    )
    def orchestrate_pdf_analysis(
        self,
        pdf_path: Annotated[str, "Path to PDF file"]
    ) -> Annotated[str, "Orchestration status"]:
        """Orchestrate the analysis workflow."""
        return f"Ready to analyze: {pdf_path}"
    
    @kernel_function(
        name="validate_results",
        description="Validates analysis results for completeness and accuracy"
    )
    def validate_results(
        self,
        results_json: Annotated[str, "JSON results to validate"]
    ) -> Annotated[str, "Validation status"]:
        """Validate analysis results."""
        try:
            results = json.loads(results_json)
            if 'error' in results:
                return "INVALID: Error in results"
            if not results:
                return "INVALID: Empty results"
            return "VALID"
        except:
            return "INVALID: Malformed JSON"

# ============================================================================
# SEMANTIC KERNEL ORCHESTRATOR
# ============================================================================

class QuantGPTSKOrchestrator:
    """
    QuantGPT Orchestrator using Semantic Kernel's native capabilities.
    """
    
    def __init__(self, debug: bool = False):
        """Initialize the Semantic Kernel orchestrator."""
        self.debug = debug
        self.kernel = Kernel()
        
        # Load configuration
        self._setup_environment()
        
        # Add AI service
        self._setup_ai_service()
        
        # Register plugins
        self._register_plugins()
        
        # Create planner for orchestration
        self._setup_planner()
    
    def _setup_environment(self):
        """Setup environment and configuration."""
        base_path = Path(__file__).resolve().parents[2]
        env_path = base_path / ".env"
        if env_path.exists():
            load_env(dotenv_path=env_path)
        
        self.config = load_config()
    
    def _setup_ai_service(self):
        """Setup the AI service for the kernel."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            # Use OpenRouter
            service = OpenRouterChatCompletion(
                api_key=api_key,
                ai_model_id=os.getenv("OPENROUTER_MODEL", "openai/gpt-4"),
                service_id="main"
            )
        else:
            # Fallback to OpenAI
            service = OpenAIChatCompletion(
                ai_model_id="gpt-4",
                service_id="main"
            )
        
        self.kernel.add_service(service)
        logger.info("AI service configured")
    
    def _register_plugins(self):
        """Register all plugins with the kernel."""
        # Register PDF analysis plugin
        self.pdf_plugin = PDFAnalysisPlugin(debug=self.debug)
        self.kernel.add_plugin(self.pdf_plugin, "PDFAnalysis")
        
        # Register risk assessment plugin
        self.risk_plugin = RiskAssessmentPlugin()
        self.kernel.add_plugin(self.risk_plugin, "RiskAssessment")
        
        # Register orchestration plugin
        self.orch_plugin = OrchestrationPlugin()
        self.kernel.add_plugin(self.orch_plugin, "Orchestration")
        
        logger.info("Plugins registered with kernel")
    
    def _setup_planner(self):
        """Setup the function calling planner."""
        # Planner not available in this version of semantic-kernel
        # options = FunctionCallingStepwisePlannerOptions(
        #     max_iterations=10,
        #     max_tokens=4000
        # )
        
        # Create planner
        # self.planner = FunctionCallingStepwisePlanner(
        #     service_id="main",
        #     options=options
        # )
        self.planner = None  # No planner available
        logger.info("Planner not available in this version")
    
    async def analyze_pdf_with_planning(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze PDF using Semantic Kernel's planning capabilities.
        The kernel will automatically select and call appropriate functions.
        """
        # Define the goal for the planner
        goal = f"""
        Analyze the PDF document at {pdf_path} for quantum computing vulnerabilities:
        1. Extract all technical components from the PDF
        2. Extract the full text with links for context
        3. Enrich components by exploring their links
        4. Map components to the knowledge graph entities
        5. Assess quantum risks for all mapped components
        6. Generate a comprehensive risk report
        7. Validate the results
        
        Return the path to the generated risk report.
        """
        
        try:
            # Execute the plan
            result = await self.planner.invoke(self.kernel, goal)
            
            return {
                "status": "success",
                "result": result.value,
                "metadata": result.metadata if hasattr(result, 'metadata') else {}
            }
        except Exception as e:
            logger.error(f"Planning execution failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def analyze_pdf_with_agent(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze PDF using a Semantic Kernel agent with function calling.
        """
        # Create agent with specific instructions
        agent = ChatCompletionAgent(
            kernel=self.kernel,
            service_id="main",
            name="QuantumRiskAnalyst",
            instructions="""
            You are a quantum risk assessment specialist. Your task is to:
            1. Extract and analyze components from technical documents
            2. Map them to known quantum-vulnerable entities
            3. Assess their risk levels
            4. Generate comprehensive reports
            
            Use the available functions to complete these tasks systematically.
            Always validate your results before finalizing.
            """,
            execution_settings=PromptExecutionSettings(
                service_id="main",
                temperature=0.7,
                max_tokens=2048,
                function_choice_behavior=FunctionChoiceBehavior.Auto(
                    filters={"included_plugins": ["PDFAnalysis", "RiskAssessment", "Orchestration"]}
                )
            )
        )
        
        # Create conversation
        history = ChatHistory()
        history.add_user_message(
            f"Please analyze the PDF at {pdf_path} for quantum vulnerabilities and generate a risk report."
        )
        
        # Get agent response with function calling
        async for message in agent.invoke(history):
            logger.info(f"Agent: {message.content}")
            
            # Check if functions were called
            if hasattr(message, 'function_calls'):
                for fc in message.function_calls:
                    logger.info(f"Function called: {fc.name}")
        
        return {
            "status": "success",
            "conversation": [msg.content for msg in history.messages]
        }
    
    async def analyze_pdf_direct(self, pdf_path: str) -> Dict[str, Any]:
        """
        Direct orchestration using kernel function invocation.
        This demonstrates manual orchestration while still using SK functions.
        """
        results = {}
        
        try:
            # Step 1: Extract components
            logger.info("Extracting PDF components...")
            components = await self.kernel.invoke(
                plugin_name="PDFAnalysis",
                function_name="extract_pdf_components",
                pdf_path=pdf_path
            )
            results['components'] = json.loads(components.value)
            
            # Step 2: Extract text
            logger.info("Extracting PDF text...")
            text = await self.kernel.invoke(
                plugin_name="PDFAnalysis",
                function_name="extract_pdf_text",
                pdf_path=pdf_path
            )
            results['text_length'] = len(text.value)
            
            # Step 3: Enrich components
            logger.info("Enriching components...")
            enriched = await self.kernel.invoke(
                plugin_name="PDFAnalysis",
                function_name="enrich_components_with_links",
                components_json=components.value
            )
            results['enriched_components'] = json.loads(enriched.value)
            
            # Step 4: Map to knowledge graph
            logger.info("Mapping to knowledge graph...")
            mapping = await self.kernel.invoke(
                plugin_name="RiskAssessment",
                function_name="map_to_knowledge_graph",
                components_json=enriched.value,
                context=text.value[:1000]
            )
            results['mapping'] = json.loads(mapping.value)
            
            # Step 5: Assess risks
            logger.info("Assessing quantum risks...")
            assessment = await self.kernel.invoke(
                plugin_name="RiskAssessment",
                function_name="assess_quantum_risks",
                mapping_json=mapping.value
            )
            results['assessment'] = json.loads(assessment.value)
            
            # Step 6: Generate report with table format
            logger.info("Generating risk report...")
            report_path = f"risk_reports/report_{Path(pdf_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            report = await self.kernel.invoke(
                plugin_name="RiskAssessment",
                function_name="generate_risk_report",
                assessments_json=assessment.value,
                mapping_json=mapping.value,  # Pass mapping for table generation
                output_path=report_path
            )
            results['report_path'] = report.value
            
            # Step 7: Validate
            logger.info("Validating results...")
            validation = await self.kernel.invoke(
                plugin_name="Orchestration",
                function_name="validate_results",
                results_json=assessment.value
            )
            results['validation'] = validation.value
            
            return {
                "status": "success",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Direct orchestration failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "partial_results": results
            }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='QuantGPT with Semantic Kernel')
    parser.add_argument('-f', '--file', required=True, help='PDF file to analyze')
    parser.add_argument('--mode', choices=['planner', 'agent', 'direct'], 
                       default='direct', help='Execution mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize orchestrator
    orchestrator = QuantGPTSKOrchestrator(debug=args.debug)
    
    # Run analysis based on mode
    print(f"\n{'='*60}")
    print(f"QuantGPT Analysis - Mode: {args.mode.upper()}")
    print(f"{'='*60}\n")
    
    if args.mode == 'planner':
        print("Using Semantic Kernel Planner for autonomous orchestration...")
        result = await orchestrator.analyze_pdf_with_planning(args.file)
    elif args.mode == 'agent':
        print("Using Semantic Kernel Agent with function calling...")
        result = await orchestrator.analyze_pdf_with_agent(args.file)
    else:
        print("Using direct kernel function invocation...")
        result = await orchestrator.analyze_pdf_direct(args.file)
    
    # Display results
    if result['status'] == 'success':
        print("Analysis completed successfully!")
        if 'report_path' in result.get('results', {}):
            print(f"Report saved to: {result['results']['report_path']}")
        print("\nResults summary:")
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Analysis failed: {result.get('error', 'Unknown error')}")
        if 'partial_results' in result:
            print("\nPartial results:")
            print(json.dumps(result['partial_results'], indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())