FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY assets ./assets

RUN pip install --no-cache-dir . \
    && mkdir -p /app/data

CMD ["python", "-m", "issuebot"]
