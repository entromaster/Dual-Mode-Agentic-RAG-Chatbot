# ============================================================
# Python backend (frontend is not part of this repository)
# ============================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy dataset
COPY Dataset/ ./Dataset/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATASET_PATH=/app/Dataset
ENV STATIC_DIR=/app/static

# Run the FastAPI server (bind to Railway's $PORT)
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
