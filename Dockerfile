# ============================================================
# Stage 1: Build Next.js frontend
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy frontend source and build static export
COPY frontend/ ./
RUN npm run build

# ============================================================
# Stage 2: Python backend + serve frontend static files
# ============================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
# Install CPU-only PyTorch first to save massive amounts of RAM and disk space on Railway/Render
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy dataset
COPY Dataset/ ./Dataset/

# Copy frontend static build from stage 1
COPY --from=frontend-builder /app/frontend/out /app/static/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATASET_PATH=/app/Dataset
ENV STATIC_DIR=/app/static

# Expose port
EXPOSE 8000

# Change workdir so uvicorn finds the app module natively
WORKDIR /app/backend

# Run the FastAPI server using the PORT environment variable injected by Railway/Render
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
