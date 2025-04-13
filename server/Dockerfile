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
COPY server/pyproject.toml server/poetry.lock ./

# Copy project files
COPY . .

# Débogage: Vérifier les fichiers après la copie
RUN echo "===== Vérification des fichiers après COPY =====" && \
    echo "Structure du répertoire de travail:" && \
    ls -la /app/ && \
    echo "Contenu de server/data (s'il existe):" && \
    ls -la /app/server/data/ || echo "Le répertoire server/data n'existe pas" && \
    echo "Contenu de server/data/recipes (s'il existe):" && \
    ls -la /app/server/data/recipes/ || echo "Le répertoire server/data/recipes n'existe pas" && \
    echo "Taille des fichiers JSON (s'ils existent):" && \
    find /app/server/data/recipes -name "*.recipe.json" -type f -exec ls -lh {} \; | head -n 3 || echo "Pas de fichiers JSON trouvés" && \
    echo "==== Fin de la vérification ===="

# Ensure data directory exists and has correct permissions
RUN mkdir -p /app/data && chmod -R 755 /app/data

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Expose port
EXPOSE $PORT

# Run the application
CMD poetry run uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001}