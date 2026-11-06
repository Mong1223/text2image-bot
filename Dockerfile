FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Команда переопределяется в docker-compose.yml (t2i-service или t2i-bot)
CMD ["t2i-service"]
