import pdfplumber
from pathlib import Path

def extract_components_from_pdf(pdf_path, debug=False):
  components_data = {}

  with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
      tables = page.extract_tables()

      if debug:
        print(f"Page {page_num} has {len(tables)} tables.")
        # Print a preview of each table's first row (header)
        for idx, table in enumerate(tables):
          if table and len(table) > 0:
            print(f"  Table {idx}: header = {table[0]}")
          else:
            print(f"  Table {idx}: empty or malformed")

      for table_idx, table in enumerate(tables):
        if not table or len(table) < 2:
          if debug:
            print(f"  Skipping table {table_idx} on page {page_num}: too small or empty")
          continue

        # Step 1: Clean header by removing ghost columns
        raw_header = table[0]
        clean_header = [h.strip().lower() for h in raw_header if h and h.strip()]
        if debug:
          print(f"  Table {table_idx} raw header: {raw_header}")
          print(f"  Table {table_idx} clean header: {clean_header}")
        if not clean_header:
          if debug:
            print(f"  Skipping table {table_idx} on page {page_num}: empty clean header")
          continue

        # Step 2: Find the position of "component" or "components" in clean header (not original index)
        try:
          # Accept both 'component' and 'components'
          if "component" in clean_header:
            component_pos = clean_header.index("component")
            if debug:
              print(f"  Found 'component' at position {component_pos} in table {table_idx} on page {page_num}")
          elif "components" in clean_header:
            component_pos = clean_header.index("components")
            if debug:
              print(f"  Found 'components' at position {component_pos} in table {table_idx} on page {page_num}")
          else:
            raise ValueError("No component(s) column found")
        except ValueError:
          if debug:
            print(f"  Table {table_idx} on page {page_num} does not have a 'component' or 'components' column")
          continue  # Skip tables without "Component" header

        # Step 3: Iterate over rows and align by position
        for row_idx, raw_row in enumerate(table[1:], start=1):
          clean_row = [cell.strip() for cell in raw_row if cell and cell.strip()]
          if debug:
            print(f"    Row {row_idx}: raw = {raw_row}")
            print(f"    Row {row_idx}: clean = {clean_row}")
          if len(clean_row) <= component_pos:
            if debug:
              print(f"    Skipping row {row_idx}: not enough columns for 'component'")
            continue

          component = clean_row[component_pos]
          if not component:
            if debug:
              print(f"    Skipping row {row_idx}: empty component value")
            continue

          info = {"page": page_num}
          for i, val in enumerate(clean_row):
            if i == component_pos:
              continue
            label = clean_header[i] if i < len(clean_header) else f"col{i}"
            info[label] = val

          if debug:
            print(f"    Adding component '{component}' with info: {info}")

          components_data[component] = info

  return components_data

# For testing
if __name__ == "__main__":
  import sys
  from pprint import pprint

  # This ensures the script works when called from project root
  base_path = Path(__file__).resolve().parents[2]  # Up from src/quantgpt/
  pdf_path = base_path / "technical_design_docs" / "examples" / "cisco_convergeone.pdf"
  #pdf_path = base_path / "technical_design_docs" / "examples" / "nasa_impala.pdf"

  if not pdf_path.exists():
    print(f"PDF not found at: {pdf_path}")
    sys.exit(1)

  result = extract_components_from_pdf(pdf_path, debug=True)
  pprint(result)
