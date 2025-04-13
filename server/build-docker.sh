#!/bin/bash
set -e

# Se placer dans le répertoire où se trouve le Dockerfile (le dossier server)
cd "$(dirname "$0")"

# S'assurer que tous les fichiers LFS sont extraits
echo "Extracting Git LFS files..."
git lfs pull

# Construire l'image Docker
echo "Building Docker image..."
docker build -t recipe-display-server .

echo "Docker image built successfully!" 