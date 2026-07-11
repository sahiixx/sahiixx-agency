FROM python:3.12-slim

WORKDIR /app

# Install system dependencies:
# - git: required for repo discovery/cloning
# - curl: required by Docker healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for production
RUN groupadd -r opa && useradd -r -g opa -d /app -s /bin/false opa

# Install Python package
COPY pyproject.toml README.md ./
COPY sahiixx_agency/ ./sahiixx_agency/
RUN pip install --no-cache-dir .

# Copy runtime assets
COPY config/ ./config/
COPY dashboard/ ./dashboard/

# Set ownership for runtime directories
RUN mkdir -p data repos && chown -R opa:opa /app

ENV PYTHONUNBUFFERED=1
ENV OPA_CONFIG=/app/config/agency.yaml

EXPOSE 8080 8081

USER opa

CMD ["uvicorn", "sahiixx_agency.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
