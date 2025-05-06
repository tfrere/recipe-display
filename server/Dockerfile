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

# Copy dependency files - en assumant que la commande est exécutée depuis le répertoire server/
COPY pyproject.toml poetry.lock ./

# Copy all server files - assumant le build depuis le répertoire server/
COPY . .

# Débogage: Vérifier les fichiers après la copie
RUN echo "===== Vérification des fichiers après COPY =====" && \
    echo "Structure du répertoire de travail:" && \
    ls -la /app/ && \
    echo "Contenu de data (s'il existe):" && \
    ls -la /app/data/ || echo "Le répertoire data n'existe pas" && \
    echo "Contenu de data/recipes (s'il existe):" && \
    ls -la /app/data/recipes/ || echo "Le répertoire data/recipes n'existe pas" && \
    echo "Taille des fichiers JSON (s'ils existent):" && \
    find /app/data/recipes -name "*.recipe.json" -type f -exec ls -lh {} \; | head -n 3 || echo "Pas de fichiers JSON trouvés" && \
    echo "==== Fin de la vérification ===="

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

# Start the application avec des paramètres de timeout augmentés
CMD ["sh", "-c", "poetry run uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001} --timeout-keep-alive 120 --limit-concurrency 100"]