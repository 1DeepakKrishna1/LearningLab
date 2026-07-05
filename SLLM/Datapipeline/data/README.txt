Drop your source documents in this folder (or any folder you point the
pipeline at with --folder / SLLM_DOCS_FOLDER).

Supported file types:
  - PDF                .pdf
  - Images (OCR)       .png .jpg .jpeg .tif .tiff .bmp .webp
  - Spreadsheets       .csv .xls .xlsx
  - Plain text         .txt .md

Then run, from the Datapipeline folder:
  python ingest.py

Subfolders are scanned recursively. This README.txt is harmless to leave here.
