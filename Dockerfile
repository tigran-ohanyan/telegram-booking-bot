FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY bot ./bot
RUN pip install --no-cache-dir .

VOLUME ["/app/data"]
CMD ["python", "-m", "bot"]
