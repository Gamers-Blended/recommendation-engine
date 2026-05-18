# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final Run
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user for security
RUN groupadd -g 999 python && \
    useradd -r -u 999 -g python python

# Copy installed packages from builder
COPY --from=builder /root/.local /home/python/.local
COPY ./app ./app

# Set environment variables
ENV PATH=/home/python/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN chown -R python:python /app
USER python

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]