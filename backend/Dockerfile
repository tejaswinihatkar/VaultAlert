FROM python:3.12-slim

LABEL maintainer="VaultAlert Engineering <engineering@vaultalert.io>"
LABEL version="1.0.0"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create non-root user for security
RUN groupadd -r vaultalert && useradd -r -g vaultalert -d /app -s /sbin/nologin vaultalert
RUN chown -R vaultalert:vaultalert /app
USER vaultalert

EXPOSE 8000

# Run with uvicorn in production mode
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "h11"]
