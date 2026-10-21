FROM python:3.14-slim-bookworm

RUN pip install --no-cache-dir uv

WORKDIR /listinglens

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

RUN uv sync --frozen

EXPOSE 8000

ENTRYPOINT ["/listinglens/docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "listinglens.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]