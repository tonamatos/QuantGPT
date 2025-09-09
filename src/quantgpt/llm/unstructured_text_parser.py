from quantgpt.security_properties import SecurityPropertiesModel
from quantgpt.llm.prompt_eng import create_unstructured_text_prompt
from quantgpt.unstructured_text_extractor import extract_text_from_pdf, chunk_text
from quantgpt.chunk_consolidation import combine_outputs_validated
import openai
from openai import AsyncOpenAI
import asyncio


client = AsyncOpenAI(api_key=openai.api_key)

async def parse_chunk_async(chunk, model_name="gpt-5-mini"):
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": create_unstructured_text_prompt(chunk)[0]},
                {"role": "user", "content": create_unstructured_text_prompt(chunk)[1]}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "SecurityPropertiesModel",
                    "schema": SecurityPropertiesModel.model_json_schema()
                }
            }
        )
        
        raw = response.choices[0].message.content
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