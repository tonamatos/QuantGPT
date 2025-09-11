from quantgpt.security_properties import SecurityPropertiesModel
from quantgpt.llm.prompt_eng import create_unstructured_text_prompt
from quantgpt.unstructured_text_extractor import extract_text_from_pdf, chunk_text
from quantgpt.chunk_consolidation import combine_outputs_validated
import asyncio
import os


# Lazy initialization to avoid import-time API key requirement
_llm_client = None

def get_llm_client():
    """Get or create LLM client with lazy initialization."""
    global _llm_client
    if _llm_client is None:
        # Always use the original LLMClient to avoid circular imports
        from quantgpt.llm.client import LLMClient
        _llm_client = LLMClient(cfg={})
    return _llm_client


async def parse_chunk_async(chunk):
    try:
        system_msg, user_msg = create_unstructured_text_prompt(chunk)

        # Get LLM client with lazy initialization
        llm_client = get_llm_client()
        
        # Use the original LLMClient interface
        raw = await llm_client.achat(
            prompt=user_msg,
            system=system_msg,
            json_mode=True,
            context_messages=None
        )

        return SecurityPropertiesModel.model_validate_json(raw)

    except Exception as e:
        print(f"Error parsing chunk: {e}")
        return None
    
async def parse_pdf_async(pdf_path, max_concurrency=10):
    raw_text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(raw_text, max_words=500)

    # Semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrency)

    async def sem_task(chunk):
        async with semaphore:
            return await parse_chunk_async(chunk)

    tasks = [sem_task(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    # Filter out any None results
    results = [r for r in results if r is not None]
    return combine_outputs_validated(results)