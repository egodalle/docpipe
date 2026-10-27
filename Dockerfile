FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md config.yaml ./
COPY src ./src
COPY sql ./sql
COPY data/licenses.csv ./data/licenses.csv

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
CMD ["docpipe", "sync"]
