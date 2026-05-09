FROM python:3.11-slim

# Install docker CLI and curl
RUN apt-get update && \
    apt-get install -y docker.io curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY main.py .
COPY requirements.txt .
COPY .env.example .

RUN pip install --no-cache-dir -r requirements.txt

# Force Python to run unbuffered so logs appear immediately
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
