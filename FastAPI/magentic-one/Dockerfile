FROM python:3.10-slim

# 1. Install system dependencies (minimal required for Playwright and ffmpeg)
RUN apt-get update && apt-get install -y \
    curl git wget unzip xvfb \
    ffmpeg \
    libglib2.0-0 libnss3 libgconf-2-4 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libxss1 libasound2 \
    libxcomposite1 libxdamage1 libgbm1 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Create non-root user early
RUN useradd -m agentuser

# 3. Set working directory and copy requirements
WORKDIR /app
COPY requirements.txt .

# 4. Install Python dependencies (as root)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir playwright \
 && playwright install-deps

# 5. Switch to non-root user for safety
USER agentuser

# 6. Install Playwright browsers (as agentuser)
RUN python -m playwright install chromium

# 7. Copy source code
COPY . .

# 8. Default command
CMD ["python", "main.py"]