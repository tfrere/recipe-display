#!/bin/bash
set -e

# Se placer dans le répertoire où se trouve le script
cd "$(dirname "$0")"

# Vérifier si Git LFS est installé
if ! command -v git-lfs &> /dev/null; then
    echo "Git LFS n'est pas installé. Installation en cours..."
    # Pour Ubuntu/Debian
    curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
    sudo apt-get install -y git-lfs
    git lfs install
fi

# S'assurer que tous les fichiers LFS sont extraits
echo "Extraction des fichiers Git LFS..."
git lfs pull

# Construire l'image Docker
echo "Construction de l'image Docker..."
docker build -t recipe-display-server .

# Arrêter le conteneur existant s'il est en cours d'exécution
echo "Arrêt du conteneur existant (s'il est en cours d'exécution)..."
docker stop recipe-display-server || true
docker rm recipe-display-server || true

# Démarrer le nouveau conteneur
echo "Démarrage du nouveau conteneur..."
docker run -d \
    --name recipe-display-server \
    -p 3001:3001 \
    -e PORT=3001 \
    --restart unless-stopped \
    recipe-display-server

echo "Déploiement terminé avec succès!" 