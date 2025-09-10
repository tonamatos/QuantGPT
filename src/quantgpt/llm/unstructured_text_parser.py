from quantgpt.security_properties import SecurityPropertiesModel
from quantgpt.llm.prompt_eng import create_unstructured_text_prompt
from quantgpt.unstructured_text_extractor import extract_text_from_pdf, chunk_text
from quantgpt.chunk_consolidation import combine_outputs_validated
from quantgpt.llm.client import LLMClient  
import asyncio


llm_client = LLMClient(cfg={})


async def parse_chunk_async(chunk):
    try:
        system_msg, user_msg = create_unstructured_text_prompt(chunk)

        # Call the async method from your LLMClient
        raw = await llm_client.achat(
            prompt=user_msg,
            system=system_msg,
            json_mode=True,  # since you want JSON output
            context_messages=None  # optional, only if you have extra messages
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