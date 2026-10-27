FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md config.yaml ./
COPY src ./src
COPY sql ./sql
COPY data/licenses.csv ./data/licenses.csv

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1 PORT=8080 DOCS_ROOT=/app DOCS_CONFIG=/app/config.yaml
EXPOSE 8080
CMD ["docpipe", "serve", "--host", "0.0.0.0", "--port", "8080"]
