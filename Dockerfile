# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY shein_monitor.py .

# Create a non-root user to run the app
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for Render.com health checks
EXPOSE 8080

# Run the monitor
CMD ["python", "shein_monitor.py"]
