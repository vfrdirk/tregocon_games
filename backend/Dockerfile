FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app/ ./app/

# Run with hot reload in dev; gunicorn in prod (set CMD accordingly)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
