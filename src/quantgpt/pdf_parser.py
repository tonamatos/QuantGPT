import pdfplumber
from pathlib import Path

def extract_components_from_pdf(pdf_path):
  components_data = {}

  with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
      tables = page.extract_tables()

      for table in tables:
        if not table or len(table) < 2:
          continue

        # Step 1: Clean header by removing ghost columns
        raw_header = table[0]
        clean_header = [h.strip().lower() for h in raw_header if h and h.strip()]
        if not clean_header:
          continue

        # Step 2: Find the position of "component" in clean header (not original index)
        try:
          component_pos = clean_header.index("component")
        except ValueError:
          continue  # Skip tables without "Component" header

        # Step 3: Iterate over rows and align by position
        for raw_row in table[1:]:
          clean_row = [cell.strip() for cell in raw_row if cell and cell.strip()]
          if len(clean_row) <= component_pos:
            continue

          component = clean_row[component_pos]
          if not component:
            continue

          info = {"page": page_num}
          for i, val in enumerate(clean_row):
            if i == component_pos:
              continue
            label = clean_header[i] if i < len(clean_header) else f"col{i}"
            info[label] = val

          components_data[component] = info

  return components_data

# For testing: run this directly from within the project root
if __name__ == "__main__":
  import sys
  from pprint import pprint

  # This ensures the script works when called from project root
  base_path = Path(__file__).resolve().parents[2]  # Up from src/quantgpt/
  pdf_path = base_path / "technical_design_docs" / "examples" / "cisco_convergeone.pdf"
  pdf_path = base_path / "technical_design_docs" / "examples" / "nasa_impala.pdf"

  if not pdf_path.exists():
    print(f"PDF not found at: {pdf_path}")
    sys.exit(1)

  result = extract_components_from_pdf(pdf_path)
  pprint(result)
