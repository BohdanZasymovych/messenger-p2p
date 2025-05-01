FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ /app/

# copy static assets
COPY frontend/ /app/frontend

# Copy the start script and make it executable
COPY docker/start.sh /app/
RUN chmod +x /app/start.sh

# Change CMD to run the start script
CMD ["/app/start.sh"]