# Use lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=webapp.settings

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Directory for SQLite persistence
RUN mkdir -p /data
VOLUME /data

# Expose port for Gunicorn
EXPOSE 8000

# Collect static files at container start and run Gunicorn
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn webapp.wsgi:application --bind 0.0.0.0:8000 --workers 2"]
