FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for grype installation
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install grype
RUN curl -sSfL https://get.anchore.io/grype | sh -s -- -b /usr/local/bin

# Copy project files
COPY pyproject.toml .
COPY grummage.py .
COPY README.md .
COPY LICENSE .

# Install the package
RUN pip install --no-cache-dir -e .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash grummage
USER grummage

ENTRYPOINT ["python", "grummage.py"]