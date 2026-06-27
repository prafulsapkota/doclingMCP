# Use a standard Python 3.12 slim base image
FROM python:3.12-slim

# Install system dependencies required by Docling, PyTorch, and general builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /uvx /bin/

# Set up working directory
WORKDIR /app

# Copy dependency requirements
COPY pyproject.toml* uv.lock* ./

# Install python dependencies using uv (no-cache and system-level installation in container)
RUN uv pip install --system fastmcp "docling[vlm]" pypdfium2

# Copy application source code
COPY server.py ./

# Create directory for temp files
RUN mkdir -p temp_files && chmod 777 temp_files

# Expose standard port for FastMCP streamable HTTP transport (if used)
EXPOSE 8000

# Set Hugging Face cache directory environment variable
ENV HF_HOME=/root/.cache/huggingface

# Run the server via python
CMD ["python", "server.py"]
