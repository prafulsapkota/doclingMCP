# Docling Granite MCP Server

This is an MCP (Model Context Protocol) server implemented using FastMCP. It processes PDF documents using [Docling](https://docling.ai) and enhances image extractions with description explanations using the [IBM Granite Vision](https://huggingface.co/ibm-granite/granite-vision-3.3-2b) model.

## Features

- **Document Conversion**: Converts PDFs to Markdown format.
- **Granite Vision Descriptions**: Analyzes images/charts in the PDF and generates text explanations using `ibm-granite/granite-vision-3.3-2b` VLM.
- **Streaming & Non-Streaming Options**: Supports streaming the Markdown output in chunks or returning it as a single block.
- **Page Offset Range**: Supports parsing a subset of pages (`start_page` to `end_page`).
- **Secure File Handling**: Receives the file content via base64, saves it to a unique temporary file (`timestamp_filename`) inside the workspace `temp_files/` directory, and clears it immediately after the conversion response is completed.
- **Isolated Venv**: Utilizes `uv` to manage python dependencies locally.

## Setup

1. **Virtual Environment**:
   The project has been configured with an isolated Python virtual environment using `uv` inside this workspace folder.

2. **Dependencies**:
   The virtual environment contains:
   - `fastmcp`
   - `docling[vlm]` (includes PyTorch and IBM Granite vision pipeline components)
   - `pypdfium2` (for determining PDF metadata/page counts)

## How to Run

To run the MCP server with the HTTP SSE transport:

```bash
# Activate virtual environment and run
.venv/bin/python server.py
```
This runs the server at `http://localhost:8000/sse`.

### Configuration for Claude Desktop / Cursor

You can add this server to your Claude Desktop configuration file (typically at `~/.config/Claude/claude_desktop_config.json`) using the SSE transport settings:

```json
{
  "mcpServers": {
    "docling-granite-mcp": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## Running with Docker and Docker Compose

To containerize the MCP server and run it easily:

### 1. Build and Run via Docker Compose

We configure a persistent volume `hf_cache` to store Hugging Face weights so that the Granite Vision model does not need to be downloaded every time the container starts.

To build and start the server:

```bash
docker compose up --build
```
The server will be reachable at `http://localhost:8000/sse` on the host machine.

### 2. Configuration for Claude Desktop / Cursor (via Docker)

Once running via Docker Compose (or `docker run`), configure it in your Client Settings:

```json
{
  "mcpServers": {
    "docling-granite-mcp-docker": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## Tools Provided

### `convert_pdf`
Converts a base64-encoded PDF to Markdown with Granite image descriptions.

- **Arguments**:
  - `file_content_b64` (string, required): Base64-encoded string of the PDF content.
  - `filename` (string, required): Original filename (e.g., `report.pdf`).
  - `stream` (boolean, optional, default: `false`): If `true`, streams the output in chunks.
  - `start_page` (integer, optional, default: `1`): Starting page index (1-based, inclusive).
  - `end_page` (integer, optional): Ending page index (1-based, inclusive).

