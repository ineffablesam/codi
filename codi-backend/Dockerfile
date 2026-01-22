# Multi-stage Dockerfile for Codi Backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Create non-root user
RUN groupadd -g 1000 codi && \
    useradd -u 1000 -g codi -s /bin/bash -m codi

# Install system dependencies including Docker CLI and buildx for container builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    libssl-dev \
    git \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    # Install Docker CLI and buildx for BuildKit support (detect arch)
    && ARCH=$(dpkg --print-architecture) \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=${ARCH} signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce-cli docker-buildx-plugin \
    && rm -rf /var/lib/apt/lists/*

# Create repos directory and set permissions
RUN mkdir -p /var/codi/repos && chown 1000:1000 /var/codi/repos

# Development stage
FROM base as development

COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright and Chromium for Computer Use agent
RUN pip install playwright && playwright install chromium --with-deps

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright and Chromium for Computer Use agent
RUN pip install playwright && playwright install chromium --with-deps

COPY --chown=codi:codi . .

USER codi

EXPOSE 8000

# Use multiple workers in production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
