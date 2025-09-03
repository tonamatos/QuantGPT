import pdfplumber
import fitz
from pathlib import Path

def extract_text_with_links(pdf_path):
    """Extracts visible text from a PDF while preserving hyperlinks. Ignores tables.
    Args:
        pdf_path (str or Path): Path to the PDF file.
    Returns:
        str: Extracted text with hyperlinks in markdown format.
    """
    # First pass: extract visible text without tables
    text_blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # extract_text() already excludes most tables if layout is correct
            page_text = page.filter(lambda obj: obj["object_type"] != "char" or obj.get("non_table", True))
            text_blocks.append(page.extract_text())

    plain_text = "\n\n".join(filter(None, text_blocks))

    # Second pass: overlay links using PyMuPDF
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, start=1):
        links = page.get_links()
        for link in links:
            if "uri" in link:  # it's a URL
                # Get text near the rectangle (anchor text)
                rect = fitz.Rect(link["from"])
                words = page.get_text("words")  # list of (x0, y0, x1, y1, word, block_no, line_no, word_no)
                anchor_words = [w[4] for w in words if rect.intersects(fitz.Rect(w[:4]))]
                anchor_text = " ".join(anchor_words) if anchor_words else link["uri"]

                # Replace anchor text in plain_text with markdown-style link
                plain_text = plain_text.replace(anchor_text, f"[{anchor_text}]({link['uri']})")

    return plain_text

def extract_components_from_pdf(pdf_path, debug=False):
  """Extracts components and their associated information from tables in a PDF.
  Args:
      pdf_path (str or Path): Path to the PDF file.
      debug (bool): If True, prints debug information.  
  Returns:
      dict: A dictionary mapping component names to their associated information.
  """
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

    print("\n\nExtracted Text with Links:\n")

    pprint(extract_text_with_links(pdf_path))