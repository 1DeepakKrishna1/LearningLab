import os
import sys
import logging
from pathlib import Path  
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode, PictureItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

output_dir = Path("output")
image_subdir = Path("images") 

if len(sys.argv) < 2:
    print("Usage: python docling_basic.py <path_to_pdf_file>")
    sys.exit(1)

pdf_file_path = Path(sys.argv[1]).expanduser()

# Ensure output directory exists
output_dir.mkdir(parents=True, exist_ok=True)

pdf_pipeline_options = PdfPipelineOptions(
    do_table_structure=True, 
    images_scale=4.0,       # Increased scale for higher resolution images
    generate_picture_images=True 
)

_log.info("Initializing DocumentConverter...")
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options)
    }
)
_log.info("DocumentConverter initialized.")

if not pdf_file_path.exists():
    _log.error(f"Error: PDF file not found at '{pdf_file_path}'")
    print(f"Error: PDF file not found at '{pdf_file_path}'")
else:
    _log.info(f"Starting conversion for: {pdf_file_path}...")
    try:
        result = converter.convert(pdf_file_path)
        _log.info("Conversion completed.")

        base_filename = pdf_file_path.stem
        markdown_filename = base_filename + ".md"
        output_markdown_path = output_dir / markdown_filename

        _log.info(f"Exporting Markdown with image references to: {output_markdown_path}")
        result.document.save_as_markdown(
            output_markdown_path,
            image_mode=ImageRefMode.REFERENCED
            )
        _log.info("Markdown export finished.")

        # --- Rename Artifacts Directory and Update Links ---
        default_artifact_dir_name = base_filename + '_artifacts'
        desired_image_dir_name = base_filename + '_images' # Use the base filename
        default_artifact_path = output_dir / default_artifact_dir_name
        desired_image_path = output_dir / desired_image_dir_name

        if default_artifact_path.exists() and default_artifact_path.is_dir():
            _log.info(f"Renaming {default_artifact_path} to {desired_image_path}")
            default_artifact_path.rename(desired_image_path)

            # Update links in the markdown file
            _log.info(f"Updating image links in {output_markdown_path}")
            try:
                md_content = output_markdown_path.read_text(encoding='utf-8')
                # Replace the artifact path part in the links
                # Ensure we add the trailing slash for replacement
                updated_md_content = md_content.replace(
                    f"{default_artifact_dir_name}/",
                    f"{desired_image_dir_name}/"
                )
                output_markdown_path.write_text(updated_md_content, encoding='utf-8')
                _log.info("Markdown links updated.")
            except Exception as file_ex:
                _log.error(f"Error updating markdown file {output_markdown_path}: {file_ex}")
        else:
            _log.warning(f"Default artifact directory {default_artifact_path} not found, skipping rename/update.")
        # --- End Rename and Update ---


        print(f"\nSuccessfully converted '{pdf_file_path.name}' to Markdown.")
        print(f"Markdown saved to: {output_markdown_path}")
        print(f"Images saved to: {desired_image_path}") # Print the new path
        print("\nReview the output file for layout, tables, and image references.")

    except Exception as e:
        _log.exception("An error occurred during conversion:") 
        print(f"An error occurred during conversion: {e}")
        print("Ensure you have installed docling correctly and have necessary dependencies.")
