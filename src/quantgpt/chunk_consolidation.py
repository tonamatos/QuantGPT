from quantgpt.security_properties import SecurityPropertiesModel
from typing import List
from pydantic import ValidationError

def combine_outputs_validated(outputs: List[SecurityPropertiesModel]) -> SecurityPropertiesModel:
    """
    Combine multiple per-chunk outputs (SecurityPropertiesModel instances)
    into a single validated SecurityPropertiesModel, deduping only identical 
    (name, context) or (topic, reference) pairs.
    """
    # initialize container
    combined = {
        "encryption_algorithms": [],
        "protocols": [],
        "certificates": [],
        "key_lifetimes": [],
        "key_distribution": [],
        "authorization": [],
        "further_references": []
    }

    # seen sets for deduplication
    seen = {key: set() for key in combined}

    for out in outputs:
        data = out.model_dump()

        for key in combined:
            items = data.get(key, []) or []
            for item in items:
                item_dict = item.model_dump() if hasattr(item, "model_dump") else dict(item)

                # Create dedupe key
                if key == "further_references":
                    dedupe_key = (item_dict.get("topic"), item_dict.get("reference"))
                else:
                    dedupe_key = (item_dict.get("name"), item_dict.get("context"))

                if dedupe_key not in seen[key]:
                    seen[key].add(dedupe_key)
                    combined[key].append(item_dict)

    # Validate combined result against Pydantic model
    try:
        return SecurityPropertiesModel.model_validate(combined)
    except ValidationError as e:
        print("Validation failed on combined outputs:", e)
        # fallback to empty model if needed
        return SecurityPropertiesModel(
            encryption_algorithms=[],
            protocols=[],
            certificates=[],
            key_lifetimes=[],
            key_distribution=[],
            authorization=[],
            further_references=[]
        )