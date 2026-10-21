FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY main.py .

RUN mkdir -p /app/data

CMD ["python", "main.py"]
