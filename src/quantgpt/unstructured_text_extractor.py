import fitz

# Use fitz to pull all unstructured text from the pdf
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# Break the text into smaller pieces
def chunk_text(text, max_words=500):
    paragraphs = text.split("\n\n")
    chunks, current_chunk = [], []
    current_len = 0

    for para in paragraphs:
        words = para.split()
        if current_len + len(words) > max_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_len = 0
        current_chunk.append(para)
        current_len += len(words)

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks