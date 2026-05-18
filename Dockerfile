FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml ./
COPY README.md ./
RUN pip install --no-cache-dir -e "."

# Copy app
COPY sahiixx_agency/ ./sahiixx_agency/
COPY config/ ./config/
COPY dashboard/ ./dashboard/

ENV PYTHONUNBUFFERED=1
ENV OPA_CONFIG=/app/config/agency.yaml

EXPOSE 8080 8081

CMD ["uvicorn", "sahiixx_agency.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
