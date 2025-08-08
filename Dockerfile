# Dockerfile

# Start with a specific Python version for reproducibility
FROM python:3.12.1-slim

WORKDIR /app

# Copy and install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

ENV PYTHONPATH=/app

# This command uses Gunicorn to start the server
# It automatically uses the $PORT variable from Cloud Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
