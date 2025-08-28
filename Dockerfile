# Dockerfile for FastAPI app
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY app.log .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
