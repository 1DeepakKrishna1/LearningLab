"""Extract plain text from each supported file type.

Every loader returns a single string. Tabular files (CSV/XLS) are flattened to
one readable line per row so the embedding model sees self-describing facts like
`region=APAC; revenue=120000` instead of opaque grids.
"""
from pathlib import Path

import pandas as pd


def _dataframe_to_text(df: pd.DataFrame) -> str:
    df = df.fillna("")
    cols = [str(c) for c in df.columns]
    lines = [f"Columns: {', '.join(cols)}"]
    for _, row in df.iterrows():
        cells = [f"{col}={row[col]}" for col in df.columns]
        lines.append("; ".join(cells))
    return "\n".join(lines)


def load_pdf(path: Path) -> str:
    # pdfplumber gives better layout-aware text; fall back to pypdf if it chokes.
    try:
        import pdfplumber

        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception as exc:  # noqa: BLE001
        print(f"    [warn] pdfplumber failed on {path.name} ({exc}); trying pypdf")

    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def load_image(path: Path) -> str:
    """OCR an image. Requires the Tesseract binary installed on the OS."""
    try:
        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception as exc:  # noqa: BLE001
        print(f"    [warn] OCR skipped for {path.name}: {exc}")
        print("           (install Tesseract OCR and `pip install pytesseract pillow`)")
        return ""


def load_csv(path: Path) -> str:
    return _dataframe_to_text(pd.read_csv(path))


def load_excel(path: Path) -> str:
    # sheet_name=None -> dict of {sheet: DataFrame}, so we keep every sheet.
    sheets = pd.read_excel(path, sheet_name=None)
    parts = []
    for name, df in sheets.items():
        parts.append(f"# Sheet: {name}\n{_dataframe_to_text(df)}")
    return "\n\n".join(parts)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_file(path: Path) -> str:
    """Dispatch a file to the right loader based on its extension."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        return load_image(path)
    if suffix == ".csv":
        return load_csv(path)
    if suffix in {".xls", ".xlsx"}:
        return load_excel(path)
    if suffix in {".txt", ".md"}:
        return load_text(path)
    return ""
