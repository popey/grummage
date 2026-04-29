FROM python:3.11-slim
ARG GRYPE_VERSION=0.111.0
ARG TARGETARCH

WORKDIR /app

# Install system dependencies needed for verified grype installation.
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Install a pinned grype release and verify it with the published checksum.
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64|arm64) grype_arch="${TARGETARCH}" ;; \
        *) echo "Unsupported Docker architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    base_url="https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}"; \
    archive="grype_${GRYPE_VERSION}_linux_${grype_arch}.tar.gz"; \
    curl -fsSLO "${base_url}/grype_${GRYPE_VERSION}_checksums.txt"; \
    curl -fsSLO "${base_url}/${archive}"; \
    grep " ${archive}$" "grype_${GRYPE_VERSION}_checksums.txt" | sha256sum -c -; \
    tar -xzf "${archive}" grype; \
    install -m 0755 grype /usr/local/bin/grype; \
    rm -f "${archive}" "grype_${GRYPE_VERSION}_checksums.txt" grype

# Copy project files
COPY pyproject.toml .
COPY grummage.py .
COPY README.md .
COPY LICENSE .

# Install the package
RUN pip install --no-cache-dir .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash grummage
USER grummage

ENTRYPOINT ["grummage"]
