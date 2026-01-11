# Stage 1: Build stage with development dependencies
FROM python:3.11-slim AS builder

# Install build dependencies for pillow-heif
RUN apt-get update && apt-get install -y \
    libheif-dev \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libheif1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user
RUN useradd -m -u 1000 appuser

# Create directories
RUN mkdir -p /photos /tmp/picture-frame-cache /app

# Set working directory
WORKDIR /app

# Copy application files
COPY app ./app

# Set permissions
RUN chown -R appuser:appuser /app /photos /tmp/picture-frame-cache

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:create_app()"]
