# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# System deps for git clone + health
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY sahiixx_agency ./sahiixx_agency
COPY config ./config

RUN pip install --no-cache-dir -e ".[api]"

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
VOLUME ["/data"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/health || exit 1

CMD ["uvicorn", "sahiixx_agency.api.asgi:app", "--host", "0.0.0.0", "--port", "8080"]
