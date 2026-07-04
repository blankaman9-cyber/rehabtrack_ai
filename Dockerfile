# Use a lightweight python image
FROM python:3.10-slim

# Install system dependencies (needed for MediaPipe, OpenCV, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend source files
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose the Flask port
EXPOSE 5000

# Set environment variable for production
ENV FLASK_ENV=production

# Run the Flask server via Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--chdir", "backend", "server:app"]
