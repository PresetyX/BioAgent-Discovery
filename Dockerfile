# ---- Stage 1: build dependency wheels ----
FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---- Stage 2: slim runtime image ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /wheels /wheels
RUN pip install /wheels/* && rm -rf /wheels

COPY bioagent ./bioagent
COPY main.py .
RUN mkdir -p /app/reports && chown appuser:appuser /app/reports

USER appuser
# Pass OPENAI_API_KEY or ANTHROPIC_API_KEY at runtime and mount ./reports to keep the output:
#   docker run --rm -e OPENAI_API_KEY=... -v "$PWD/reports:/app/reports" bioagent-discovery \
#     --disease "Alzheimer's disease" --output reports/alzheimer.md
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
