FROM python:3.12-slim

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
        gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Git LFS
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash \
    && apt-get update \
    && apt-get install -y git-lfs \
    && git lfs install

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy all server files
COPY . .

# Ensure data directory exists and has correct permissions
RUN mkdir -p /app/data/recipes && chmod -R 755 /app/data

# Debug: Check files after copy
RUN echo "===== Checking files after COPY =====" && \
    echo "Working directory structure:" && \
    ls -la /app/ && \
    echo "Data directory content:" && \
    ls -la /app/data/ || echo "Data directory does not exist" && \
    echo "Recipes directory content:" && \
    ls -la /app/data/recipes/ || echo "Recipes directory does not exist" && \
    echo "Checking LFS files:" && \
    git lfs ls-files || echo "No LFS files found" && \
    echo "==== End of verification ===="

# Expose port
EXPOSE $PORT

# Start script that runs debugging then launches the application
CMD python debug_startup.py && poetry run uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001}