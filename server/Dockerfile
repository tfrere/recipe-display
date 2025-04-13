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

# Copy project files (incluant tous les fichiers nécessaires)
COPY . .

# Create startup script to handle Git LFS files
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Check if recipe files are Git LFS pointers\n\
if grep -q "git-lfs.github.com" /app/data/recipes/*.recipe.json 2>/dev/null; then\n\
    echo "Detected Git LFS pointers, trying to convert them to actual content..."\n\
    # Create repo structure to use git lfs\n\
    mkdir -p /tmp/recipes\n\
    cd /tmp/recipes\n\
    git init\n\
    git lfs install\n\
    \n\
    # Copy LFS pointers to a temp location\n\
    cp /app/data/recipes/*.recipe.json .\n\
    \n\
    # Create git attributes file\n\
    echo "*.recipe.json filter=lfs diff=lfs merge=lfs -text" > .gitattributes\n\
    \n\
    # Add files to git\n\
    git add .\n\
    git commit -m "Add recipe files"\n\
    \n\
    # Try to extract LFS files\n\
    git lfs pull || true\n\
    \n\
    # Copy back the real files if extraction succeeded\n\
    if ! grep -q "git-lfs.github.com" *.recipe.json 2>/dev/null; then\n\
        echo "Successfully converted LFS pointers to actual content"\n\
        cp *.recipe.json /app/data/recipes/\n\
    else\n\
        echo "WARNING: Could not convert LFS pointers to actual content"\n\
    fi\n\
    \n\
    # Cleanup\n\
    cd /app\n\
    rm -rf /tmp/recipes\n\
fi\n\
\n\
# Start the application\n\
exec poetry run uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001}\n\
' > /app/start.sh && chmod +x /app/start.sh

# Ensure data directory exists and has correct permissions
RUN mkdir -p /app/data && chmod -R 755 /app/data

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Expose port
EXPOSE $PORT

# Run the application using the startup script
CMD ["/app/start.sh"]