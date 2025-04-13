FROM python:3.12-slim

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install Git LFS
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash \
    && apt-get install -y git-lfs \
    && git lfs install

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Setup Git LFS and pull files
COPY .gitattributes .gitattributes
COPY .git/lfs .git/lfs
COPY server/data/recipes server/data/recipes

# Copy project files
COPY . .

# Pull LFS files
RUN git lfs pull

# Ensure data directory exists and has correct permissions
RUN mkdir -p /app/data && chmod -R 755 /app/data

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Expose port
EXPOSE $PORT

# Run the application
CMD poetry run uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001}