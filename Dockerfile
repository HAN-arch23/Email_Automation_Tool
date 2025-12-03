# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create instance directory for SQLite (if using SQLite)
RUN mkdir -p instance

# Expose port
EXPOSE 8080

# Run database migrations and start the app
CMD flask db upgrade && gunicorn --bind 0.0.0.0:$PORT app:app
