import requests
from bs4 import BeautifulSoup

def link_explorer(components_data):
    """
    Expects components_data to be a dict mapping component names to their associated information.
    Explores each link stored as component["links"] and updates components_data with any new information found as
    component["info_found_in_link"].
    
    Args:
        components_data (dict): Existing components data to update with new information.
    
    Returns:
        None: Updates components_data in place.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; QuantGPT/1.0)"}
    
    for component in components_data.values():
        if "links" not in component or not component["links"]:
            continue

        link_infos = []
        for link in component["links"]:
            try:
                resp = requests.get(link, headers=headers, timeout=10)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text(separator="\n", strip=True)

                # Keep only a snippet (optional, avoids overwhelming your data)
                snippet = text[:2000]  # first 2000 chars
                link_infos.append({"url": link, "text": snippet})

            except Exception as e:
                link_infos.append({"url": link, "error": str(e)})

        component["info_found_in_link"] = link_infos

if __name__ == "__main__":
    # Example usage
    sample_components = {
        "ComponentA": {
            "description": "This is component A.",
            "links": ["https://example.com", "https://nonexistent.url"]
        },
        "ComponentB": {
            "description": "This is component B with no links.",
        }
    }

    link_explorer(sample_components)
    from pprint import pprint
    pprint(sample_components)