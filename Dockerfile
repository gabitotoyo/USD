FROM python:3.9-slim-buster

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PORT=8000 
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "app:app"]

