FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY backend/ /app/

# Ensure the installed packages are accessible
ENV PATH="/root/.local/bin:$PATH"

# Run the application
CMD ["python", "-u", "server.py"]
