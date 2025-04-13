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

# Copy Git LFS configuration first
COPY .gitattributes .gitattributes

# Copy the entire repository to have access to Git history
COPY .git .git

# Perform Git LFS pull to retrieve LFS objects
RUN git lfs pull

# Débogage: Vérifier où sont les fichiers LFS
RUN echo "===== Vérification des fichiers LFS =====" && \
    echo "Structure du répertoire de travail:" && \
    ls -la /app/ && \
    echo "Contenu de server/data (s'il existe):" && \
    ls -la /app/server/data/ || echo "Le répertoire n'existe pas encore" && \
    echo "Contenu de server/data/recipes (s'il existe):" && \
    ls -la /app/server/data/recipes/ || echo "Le répertoire n'existe pas encore" && \
    echo "==== Fin de la vérification ===="

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Copy project files (incluant tous les fichiers nécessaires)
COPY . .

# Débogage: Vérifier à nouveau après la copie complète
RUN echo "===== Vérification des fichiers après COPY . . =====" && \
    echo "Structure du répertoire de travail:" && \
    ls -la /app/ && \
    echo "Contenu de server/data:" && \
    ls -la /app/server/data/ && \
    echo "Contenu de server/data/recipes:" && \
    ls -la /app/server/data/recipes/ && \
    echo "Taille d'un fichier JSON exemple (s'il existe):" && \
    ls -lh /app/server/data/recipes/*.recipe.json | head -n 1 && \
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