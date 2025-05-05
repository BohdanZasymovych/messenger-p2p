FROM python:3.10-slim

RUN apt-get update && apt-get install -y openssl

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# prepare a place for certs
RUN mkdir -p /app/certs

# Copy application code
COPY backend/ /app/

# 2) Copy your frontend into exactly the folder your code mounts
RUN mkdir -p /app/backend/frontend
COPY frontend/ /app/backend/frontend

# COPY certs/ /app/certs

# Copy the start script and make it executable
COPY docker/start.sh /app/
RUN chmod +x /app/start.sh

# Change CMD to run the start script
CMD ["/app/start.sh"]