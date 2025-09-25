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

# Create necessary directories
RUN mkdir -p /app/FastAPI/core/charts
RUN mkdir -p /app/FastAPI/reports_and_graphs
RUN mkdir -p /app/FastAPI/core/streamlit_data

# Expose port for FastAPI
EXPOSE 8000

# Command to run the document generator
CMD ["python", "FastAPI/core/document_generator.py"]