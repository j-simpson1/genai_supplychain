FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire FastAPI directory structure
COPY . /app/

# Set environment variables
ENV PYTHONPATH=/app
ENV MATPLOTLIB_BACKEND=Agg

# Create necessary directories for runtime outputs
RUN mkdir -p /app/output

# Expose port for FastAPI
EXPOSE 8000

# Command to run the FastAPI application
CMD ["python", "-m", "uvicorn", "FastAPI.main:app", "--host", "0.0.0.0", "--port", "8000"]