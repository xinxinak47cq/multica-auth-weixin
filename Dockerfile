FROM python:3.11-slim

# Install docker CLI and curl
RUN apt-get update && \
    apt-get install -y docker.io curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY main.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
