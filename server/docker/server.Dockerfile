FROM python:3.11-slim AS builder
WORKDIR /app

# install build tools for bcrypt/cryptography, etc.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libffi-dev \
      libssl-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# copy just the global site‑packages from builder
COPY --from=builder /usr/local /usr/local

# copy your app
COPY backend/ /app/

ENV PATH="/root/.local/bin:$PATH"
CMD ["python", "-u", "server.py"]