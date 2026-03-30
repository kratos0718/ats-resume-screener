import streamlit as st


@st.cache_data
def extract_text_from_pdf(uploaded_file) -> str:
    """Try pdfplumber first, fall back to PyPDF2. Returns clean text string."""
    file_bytes = uploaded_file.read()

    # Attempt 1: pdfplumber (better at complex layouts)
    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages).strip()
            if len(text) >= 100:
                return text
    except Exception:
        pass

    # Attempt 2: PyPDF2 fallback
    try:
        import PyPDF2
        import io
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        pages = [reader.pages[i].extract_text() or "" for i in range(len(reader.pages))]
        text = "\n".join(pages).strip()
        if len(text) >= 100:
            return text
    except Exception:
        pass

    return ""
