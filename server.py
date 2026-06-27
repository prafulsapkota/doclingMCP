import os
import time
import base64
import logging
import asyncio
from pathlib import Path
from typing import Optional, AsyncGenerator, Union
import pypdfium2 as pdfium

from fastmcp import FastMCP
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, granite_picture_description
from docling.document_converter import DocumentConverter, PdfFormatOption

# Configure Logging (Logs go to stderr so they don't interfere with stdio transport)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("docling-mcp-server")

# Define MCP server
mcp = FastMCP("Docling Granite MCP Server")

# Setup workspace and temporary directories dynamically
WORKSPACE_DIR = Path(__file__).parent.resolve()
TEMP_DIR = WORKSPACE_DIR / "temp_files"
TEMP_DIR.mkdir(exist_ok=True)

# Helper to lazy-initialize DocumentConverter to speed up server start
_converter_instance = None

def get_converter() -> DocumentConverter:
    global _converter_instance
    if _converter_instance is None:
        logger.info("Initializing Docling DocumentConverter with Granite Picture Description...")
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_picture_description = True
        pipeline_options.picture_description_options = granite_picture_description
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_picture_images = True
        
        _converter_instance = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )
    return _converter_instance

@mcp.tool()
async def convert_pdf(
    file_content_b64: str,
    filename: str,
    stream: bool = False,
    start_page: Optional[int] = 1,
    end_page: Optional[int] = None
) -> Union[str, AsyncGenerator[str, None]]:
    """
    Converts a PDF file to Markdown using Docling and IBM Granite for image explanations.
    
    Args:
        file_content_b64: Base64-encoded string of the PDF file content.
        filename: Original filename of the PDF.
        stream: If True, streams the markdown content in chunks.
        start_page: Starting page number (1-based, inclusive). Defaults to 1.
        end_page: Ending page number (1-based, inclusive). If not specified, processes to the end of the file.
    """
    # Create temp filename using combination of filename and timestamp
    timestamp = int(time.time() * 1000)
    # Clean the filename to prevent directory traversal
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    temp_file_name = f"{timestamp}_{safe_filename}"
    temp_file_path = TEMP_DIR / temp_file_name
    
    logger.info(f"Received conversion request for {filename}. Writing to temporary file {temp_file_path}")
    
    try:
        # Decode and write base64 file content
        try:
            file_bytes = base64.b64decode(file_content_b64)
        except Exception as e:
            return f"Error: Failed to decode base64 file content: {str(e)}"
            
        temp_file_path.write_bytes(file_bytes)
        
        # Determine page range
        page_range = None
        if start_page is not None or end_page is not None:
            try:
                doc = pdfium.PdfDocument(temp_file_path)
                total_pages = len(doc)
                doc.close()
            except Exception as e:
                return f"Error: Failed to parse PDF structure: {str(e)}"
                
            s_idx = max(0, (start_page or 1) - 1)
            e_idx = total_pages if end_page is None else min(total_pages, end_page)
            
            if s_idx >= total_pages:
                return f"Error: start_page ({start_page}) exceeds total page count ({total_pages})"
                
            page_range = (s_idx, e_idx)
            logger.info(f"Processing pages {s_idx + 1} to {e_idx} of {total_pages} total pages")

        # Get docling converter and run conversion
        converter = get_converter()
        
        # Run conversion in a separate thread to keep async server responsive
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: converter.convert(temp_file_path, page_range=page_range)
        )
        
        markdown_output = result.document.export_to_markdown()
        
        if stream:
            # Helper generator to stream the output
            async def chunk_generator() -> AsyncGenerator[str, None]:
                chunk_size = 1024
                for i in range(0, len(markdown_output), chunk_size):
                    yield markdown_output[i:i+chunk_size]
                    await asyncio.sleep(0.01) # Yield control
            return chunk_generator()
        else:
            return markdown_output
            
    except Exception as e:
        logger.exception("Error occurred during document conversion")
        return f"Error during conversion: {str(e)}"
        
    finally:
        # Cleanup temporary files
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.info(f"Successfully cleaned up temporary file {temp_file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temporary file {temp_file_path}: {e}")

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
