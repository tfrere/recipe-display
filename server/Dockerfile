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

# Ensure data directory exists and has correct permissions
RUN mkdir -p /app/data/recipes && chmod -R 755 /app/data

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Script de démarrage qui copie les fichiers LFS vers le volume
RUN echo '#!/bin/sh\n\
if [ -d "/server/data/recipes" ]; then\n\
    echo "Volume Railway détecté, copie des fichiers LFS..."\n\
    cp -r /app/server/data/recipes/* /server/data/recipes/\n\
    echo "Copie terminée"\n\
else\n\
    echo "Volume Railway non détecté, utilisation des fichiers locaux"\n\
fi\n\
\n\
# Lancer l\'application\n\
poetry run uvicorn server:app --host 0.0.0.0 --port ${PORT:-3001}' > /app/start.sh && \
chmod +x /app/start.sh

# Expose port
EXPOSE $PORT

# Utiliser le script de démarrage
CMD ["/app/start.sh"]