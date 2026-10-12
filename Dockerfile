FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.lock ./
RUN pip install --require-hashes -r requirements.lock \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir /data && chown app:app /data
COPY app ./app

FROM base AS test
COPY requirements-dev.lock ./
RUN pip install --require-hashes -r requirements-dev.lock
COPY pyproject.toml ./
COPY tests ./tests
COPY scripts ./scripts
USER app
ENV COVERAGE_FILE=/tmp/.coverage
CMD ["sh", "-c", "ruff check --no-cache . && ruff format --check --no-cache . && pytest -p no:cacheprovider"]

FROM base AS runtime
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
