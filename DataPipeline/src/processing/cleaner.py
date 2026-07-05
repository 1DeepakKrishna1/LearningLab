"""Text cleaning and normalisation for extracted PDF content."""

from __future__ import annotations

import re
import unicodedata


class TextCleaner:
    """Cleans raw extracted text: removes noise, normalises whitespace, fixes hyphens."""

    # Patterns compiled once at class level for performance
    _MULTI_NEWLINE = re.compile(r"\n{3,}")
    _MULTI_SPACE = re.compile(r"[ \t]{2,}")
    _PAGE_HEADER_FOOTER = re.compile(
        r"(?m)^(Page\s+\d+\s*(of\s*\d+)?|^\d+\s*$|^[-=]{3,}$)", re.IGNORECASE
    )
    _SOFT_HYPHEN = re.compile(r"(\w+)-\s*\n\s*(\w+)")
    _CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _REPEATED_PUNCT = re.compile(r"([.!?,;:]){3,}")

    def clean(self, text: str, fix_hyphenation: bool = True) -> str:
        """Apply the full cleaning pipeline and return cleaned text."""
        text = unicodedata.normalize("NFKC", text)
        text = self._CONTROL_CHARS.sub(" ", text)

        if fix_hyphenation:
            text = self._SOFT_HYPHEN.sub(r"\1\2", text)

        text = self._PAGE_HEADER_FOOTER.sub("", text)
        text = self._MULTI_SPACE.sub(" ", text)
        text = self._MULTI_NEWLINE.sub("\n\n", text)
        text = self._REPEATED_PUNCT.sub(r"\1\1", text)
        return text.strip()

    def clean_page(self, page_text: str) -> str:
        """Lightweight per-page cleaning (preserve paragraph breaks)."""
        page_text = unicodedata.normalize("NFKC", page_text)
        page_text = self._CONTROL_CHARS.sub(" ", page_text)
        page_text = self._SOFT_HYPHEN.sub(r"\1\2", page_text)
        page_text = self._MULTI_SPACE.sub(" ", page_text)
        return page_text.strip()
