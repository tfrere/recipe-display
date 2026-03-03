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

# Copy all server files
COPY . .

# Create data directory with correct permissions
RUN mkdir -p /app/data/recipes/images && \
    chown -R nobody:nogroup /app/data && \
    chmod -R 755 /app/data

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --no-interaction --no-ansi

# Expose port
EXPOSE $PORT

# Start the application
CMD ["sh", "-c", "poetry run uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001} --timeout-keep-alive 120 --limit-concurrency 100"]