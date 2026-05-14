"""
File Parser Utility
Supports text extraction from PDF, Markdown, TXT files
"""

import os
from pathlib import Path
from typing import List, Optional


def _read_text_with_fallback(file_path: str) -> str:
    """
    Read text file with automatic encoding detection if UTF-8 fails.

    Uses multi-level fallback strategy:
    1. First try UTF-8 decoding
    2. Use charset_normalizer for encoding detection
    3. Fall back to chardet for encoding detection
    4. Finally use UTF-8 + errors='replace' as fallback

    Args:
        file_path: File path

    Returns:
        Decoded text content
    """
    data = Path(file_path).read_bytes()
    
    # First try UTF-8
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass

    # Try charset_normalizer for encoding detection
    encoding = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            encoding = best.encoding
    except Exception:
        pass

    # Fall back to chardet
    if not encoding:
        try:
            import chardet
            result = chardet.detect(data)
            encoding = result.get('encoding') if result else None
        except Exception:
            pass

    # Final fallback: use UTF-8 + replace
    if not encoding:
        encoding = 'utf-8'

    return data.decode(encoding, errors='replace')


class FileParser:
    """File Parser"""

    SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.markdown', '.txt'}

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """
        Extract text from file

        Args:
            file_path: File path

        Returns:
            Extracted text content
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")

        suffix = path.suffix.lower()

        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {suffix}")

        if suffix == '.pdf':
            return cls._extract_from_pdf(file_path)
        elif suffix in {'.md', '.markdown'}:
            return cls._extract_from_md(file_path)
        elif suffix == '.txt':
            return cls._extract_from_txt(file_path)

        raise ValueError(f"Cannot handle file format: {suffix}")

    # Minimum non-whitespace chars per page before we treat the page as a scan
    # and fall back to OCR. PDFs that are pure images return only stray newlines
    # from `page.get_text()` (we've seen ~4 chars/page for whitespace-only pages),
    # so anything under this threshold is almost certainly an image-only page.
    _OCR_FALLBACK_THRESHOLD = 20

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """Extract text from PDF.

        Tries the native text layer first (fast, lossless). For scanned/image-only
        pages PyMuPDF returns near-empty strings, so we fall back to OCR via
        Tesseract when available. If OCR is needed but unavailable, raises a
        ValueError so the API can surface a clear "PDF is a scan; OCR not
        configured" message instead of silently building an empty graph.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF required: pip install PyMuPDF")

        text_parts: List[str] = []
        ocr_needed_pages: List[int] = []

        with fitz.open(file_path) as doc:
            for page_index, page in enumerate(doc):
                text = page.get_text() or ""
                meaningful_len = len(text.strip())
                if meaningful_len >= FileParser._OCR_FALLBACK_THRESHOLD:
                    text_parts.append(text)
                else:
                    ocr_needed_pages.append(page_index)

            if ocr_needed_pages:
                ocr_results = FileParser._ocr_pages(doc, ocr_needed_pages)
                # Insert OCR'd text in original page order
                if ocr_results:
                    indexed = {p: t for p, t in ocr_results}
                    # Rebuild in page order: native + OCR
                    final = []
                    for page_index, page in enumerate(doc):
                        if page_index in indexed:
                            final.append(indexed[page_index])
                        else:
                            native = page.get_text() or ""
                            if native.strip():
                                final.append(native)
                    text_parts = final

        joined = "\n\n".join(t for t in text_parts if t and t.strip())

        if not joined.strip() and ocr_needed_pages:
            raise ValueError(
                "PDF appears to be a scan (no extractable text). "
                "Install Tesseract (`apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng`) "
                "and `pip install pytesseract`, or upload a text-based PDF / .txt / .md instead."
            )

        return joined

    @staticmethod
    def _ocr_pages(doc, page_indices: List[int]) -> List[tuple]:
        """Run Tesseract OCR on the listed pages of an open fitz document.

        Returns a list of (page_index, ocr_text). Returns [] if OCR is not
        available; the caller surfaces a clearer error in that case.
        """
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # noqa: F401  (pytesseract requires PIL)
        except ImportError:
            return []

        import io
        from PIL import Image

        # Russian + English covers the common Pitchy upload mix; if a language
        # pack is missing Tesseract raises, which we swallow per-page so a
        # partial scan still yields some text.
        lang = "rus+eng"
        results: List[tuple] = []

        for idx in page_indices:
            try:
                page = doc[idx]
                # 200 DPI is a good balance of quality vs. speed for typed scans
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img, lang=lang)
                if text and text.strip():
                    results.append((idx, text))
            except Exception:
                # Skip the page rather than aborting the whole document
                continue

        return results

    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        """Extract text from Markdown with automatic encoding detection"""
        return _read_text_with_fallback(file_path)

    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """Extract text from TXT with automatic encoding detection"""
        return _read_text_with_fallback(file_path)

    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        """
        Extract text from multiple files and merge

        Args:
            file_paths: List of file paths

        Returns:
            Merged text
        """
        all_texts = []

        for i, file_path in enumerate(file_paths, 1):
            try:
                text = cls.extract_text(file_path)
                filename = Path(file_path).name
                all_texts.append(f"=== Document {i}: {filename} ===\n{text}")
            except Exception as e:
                all_texts.append(f"=== Document {i}: {file_path} (extraction failed: {str(e)}) ===")

        return "\n\n".join(all_texts)


def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> List[str]:
    """
    Split text into chunks

    Args:
        text: Original text
        chunk_size: Characters per chunk
        overlap: Overlapping characters

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to split at sentence boundaries
        if end < len(text):
            # Find nearest sentence ending
            for sep in ['。', '！', '？', '.\n', '!\n', '?\n', '\n\n', '. ', '! ', '? ']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.3:
                    end = start + last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Next chunk starts at overlap position
        start = end - overlap if end < len(text) else len(text)

    return chunks

