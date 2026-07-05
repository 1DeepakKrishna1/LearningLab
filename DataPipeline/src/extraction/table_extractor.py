"""Table extraction from PDFs using pdfplumber (primary) with camelot/tabula fallback."""

from __future__ import annotations

from typing import Any

from src.models.schemas import TableData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TableExtractor:
    """Extracts tables from PDFs and returns structured TableData objects."""

    def __init__(self, backend: str = "pdfplumber", extract_as_markdown: bool = True) -> None:
        self.backend = backend
        self.as_markdown = extract_as_markdown

    def extract(self, pdf_path: str) -> list[TableData]:
        if self.backend == "pdfplumber":
            return self._extract_pdfplumber(pdf_path)
        elif self.backend == "camelot":
            return self._extract_camelot(pdf_path)
        elif self.backend == "tabula":
            return self._extract_tabula(pdf_path)
        return []

    def _extract_pdfplumber(self, pdf_path: str) -> list[TableData]:
        try:
            import pdfplumber
        except ImportError as e:
            raise ImportError("pdfplumber not installed.") from e

        results: list[TableData] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for idx, table in enumerate(tables):
                    if not table or not table[0]:
                        continue
                    headers = [str(h or "") for h in table[0]]
                    rows = [[str(cell or "") for cell in row] for row in table[1:]]
                    md = self._to_markdown(headers, rows) if self.as_markdown else None
                    results.append(
                        TableData(page=page_num, index=idx, headers=headers, rows=rows, markdown=md)
                    )

        logger.debug("tables_extracted", path=pdf_path, count=len(results))
        return results

    def _extract_camelot(self, pdf_path: str) -> list[TableData]:
        try:
            import camelot
        except ImportError as e:
            raise ImportError("camelot-py not installed. Run: pip install camelot-py[cv]") from e

        results: list[TableData] = []
        try:
            tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
            for idx, table in enumerate(tables):
                df = table.df
                headers = df.iloc[0].tolist()
                rows = df.iloc[1:].values.tolist()
                md = self._to_markdown(headers, rows) if self.as_markdown else None
                results.append(
                    TableData(
                        page=table.page, index=idx, headers=headers, rows=rows, markdown=md
                    )
                )
        except Exception as exc:
            logger.warning("camelot_extraction_failed", error=str(exc), path=pdf_path)

        return results

    def _extract_tabula(self, pdf_path: str) -> list[TableData]:
        try:
            import tabula
        except ImportError as e:
            raise ImportError("tabula-py not installed. Run: pip install tabula-py") from e

        results: list[TableData] = []
        try:
            dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True, silent=True)
            for idx, df in enumerate(dfs):
                headers = df.columns.tolist()
                rows = df.values.tolist()
                md = self._to_markdown(headers, rows) if self.as_markdown else None
                results.append(TableData(page=idx + 1, index=idx, headers=headers, rows=rows, markdown=md))
        except Exception as exc:
            logger.warning("tabula_extraction_failed", error=str(exc))

        return results

    @staticmethod
    def _to_markdown(headers: list[Any], rows: list[list[Any]]) -> str:
        """Convert table data to GitHub-flavored Markdown."""
        h = " | ".join(str(c) for c in headers)
        sep = " | ".join(["---"] * len(headers))
        body = "\n".join(" | ".join(str(c) for c in row) for row in rows)
        return f"| {h} |\n| {sep} |\n" + "\n".join(f"| {r} |" for r in body.split("\n") if r)
