#!/bin/bash

# Script pour réinstaller tous les packages du projet recipe-display
# Ce script force la réinstallation des packages dans server/packages/ ainsi que le serveur principal
# L'ordre d'installation est important en raison des dépendances:
# 1. web_scraper
# 2. recipe_structurer 
# 3. recipe_scraper (dépend de web_scraper et recipe_structurer)
# 4. recipe_importer (dépend de recipe_scraper)
# 5. Serveur (dépend de tous les packages précédents)

echo "🔄 Début de la réinstallation des packages..."
echo ""

# Fonction pour nettoyer et réinstaller un package avec Poetry
reinstall_package() {
    package_dir=$1
    package_name=$(basename "$package_dir")
    
    echo "📦 Réinstallation de $package_name..."
    echo "---------------------------------------"
    
    cd "$package_dir" || { echo "❌ Impossible d'accéder au répertoire $package_dir"; exit 1; }
    
    echo "🧹 Nettoyage complet des installations existantes..."
    # Supprimer tous les fichiers de build, de cache et d'installation
    rm -rf dist/ build/ *.egg-info/ .pytest_cache/ poetry.lock || true
    find . -name "*.pyc" -delete || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

    # Si le package a un src/, nettoyons aussi là-dedans
    if [ -d "src" ]; then
        find src -name "*.pyc" -delete || true
        find src -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    fi
    
    # Nettoyer complètement le cache de Poetry
    poetry cache clear --all -n pypi || true
    
    echo "🔧 Réinstallation complète des dépendances avec Poetry..."
    # Forcer la réinstallation complète
    poetry lock --no-cache
    poetry install --no-root --no-cache
    
    echo "🔨 Installation du package en mode développement..."
    poetry install --no-cache
    
    echo "✅ $package_name réinstallé avec succès!"
    echo ""
    
    cd - > /dev/null || { echo "❌ Impossible de revenir au répertoire précédent"; exit 1; }
}

# Récupérer le chemin absolu du répertoire du projet
PROJECT_DIR=$(pwd)
PACKAGES_DIR="$PROJECT_DIR/server/packages"
SERVER_DIR="$PROJECT_DIR/server"
RECIPE_IMPORTER_DIR="$PROJECT_DIR/recipe_importer"

# Vérifier que le répertoire des packages existe
if [ ! -d "$PACKAGES_DIR" ]; then
    echo "❌ Répertoire des packages non trouvé: $PACKAGES_DIR"
    echo "Ce script doit être exécuté depuis la racine du projet."
    exit 1
fi

# Nettoyer d'abord tous les environnements virtuels Poetry pour les packages
echo "🧹 Nettoyage global des environnements Poetry..."
poetry env remove --all || true

# Nettoyer les fichiers egg-info dans tous les répertoires site-packages
echo "🧹 Nettoyage supplémentaire des installations Python..."
find "$HOME/.local/lib/python"*"/site-packages/" -name "recipe_scraper*" -type d -exec rm -rf {} + 2>/dev/null || true
find "$HOME/.local/lib/python"*"/site-packages/" -name "web_scraper*" -type d -exec rm -rf {} + 2>/dev/null || true
find "$HOME/.local/lib/python"*"/site-packages/" -name "recipe_structurer*" -type d -exec rm -rf {} + 2>/dev/null || true
find "$HOME/.local/lib/python"*"/site-packages/" -name "recipe_importer*" -type d -exec rm -rf {} + 2>/dev/null || true

# Nettoyer les installations des environnements virtuels
find "$HOME/Library/Caches/pypoetry/virtualenvs/" -name "site-packages" -type d -exec find {} -name "recipe_scraper*" -type d -exec rm -rf {} \; \; 2>/dev/null || true
find "$HOME/Library/Caches/pypoetry/virtualenvs/" -name "site-packages" -type d -exec find {} -name "web_scraper*" -type d -exec rm -rf {} \; \; 2>/dev/null || true
find "$HOME/Library/Caches/pypoetry/virtualenvs/" -name "site-packages" -type d -exec find {} -name "recipe_structurer*" -type d -exec rm -rf {} \; \; 2>/dev/null || true
find "$HOME/Library/Caches/pypoetry/virtualenvs/" -name "site-packages" -type d -exec find {} -name "recipe_importer*" -type d -exec rm -rf {} \; \; 2>/dev/null || true

# Réinstaller chaque package dans server/packages/
echo "🔄 Réinstallation des packages dans server/packages/..."
echo ""

# 1. Web Scraper (aucune dépendance interne)
reinstall_package "$PACKAGES_DIR/web_scraper"

# 2. Recipe Structurer (aucune dépendance interne)
reinstall_package "$PACKAGES_DIR/recipe_structurer"

# 3. Recipe Scraper (dépend de web_scraper et recipe_structurer)
reinstall_package "$PACKAGES_DIR/recipe_scraper"

# 4. Recipe Importer (dépend de recipe_scraper)
echo "📦 Réinstallation du recipe_importer..."
echo "---------------------------------------"

cd "$RECIPE_IMPORTER_DIR" || { echo "❌ Impossible d'accéder au répertoire $RECIPE_IMPORTER_DIR"; exit 1; }

echo "🧹 Nettoyage complet des installations existantes..."
rm -rf dist/ build/ *.egg-info/ .pytest_cache/ poetry.lock || true
find . -name "*.pyc" -delete || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Nettoyer complètement le cache de Poetry
poetry cache clear --all -n pypi || true

echo "🔧 Réinstallation complète des dépendances avec Poetry..."
poetry lock --no-cache
poetry install --no-root --no-cache

echo "🔨 Installation du package en mode développement..."
poetry install --no-cache

echo "✅ recipe_importer réinstallé avec succès!"
echo ""

cd "$PROJECT_DIR" || { echo "❌ Impossible de revenir au répertoire initial"; exit 1; }

# 5. Serveur principal (dépend de tous les packages)
echo "📦 Réinstallation du serveur principal..."
echo "---------------------------------------"

cd "$SERVER_DIR" || { echo "❌ Impossible d'accéder au répertoire $SERVER_DIR"; exit 1; }

echo "🧹 Nettoyage complet des installations existantes..."
rm -rf .pytest_cache/ poetry.lock || true
find . -name "*.pyc" -delete || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Nettoyer complètement le cache de Poetry
poetry cache clear --all -n pypi || true

echo "🔧 Réinstallation complète des dépendances avec Poetry..."
poetry lock --no-cache
poetry install --no-root --no-cache

echo "🔨 Installation en mode développement..."
poetry install --no-cache

echo "✅ Serveur principal réinstallé avec succès!"

# Forcer la mise à jour globale du module recipe_scraper installé dans l'environnement Python
echo "🔄 Installation globale du recipe_scraper dans l'environnement server..."
cd "$SERVER_DIR" || { echo "❌ Impossible de revenir au répertoire initial"; exit 1; }
poetry run pip uninstall -y recipe-scraper web-scraper recipe-structurer || true
cd "$PACKAGES_DIR/recipe_scraper" || { echo "❌ Impossible d'accéder au répertoire recipe_scraper"; exit 1; }
cd "$SERVER_DIR" || { echo "❌ Impossible de revenir au répertoire server"; exit 1; }
poetry run pip install -e "$PACKAGES_DIR/web_scraper"
poetry run pip install -e "$PACKAGES_DIR/recipe_structurer"
poetry run pip install -e "$PACKAGES_DIR/recipe_scraper"

# Revenir au répertoire initial
cd "$PROJECT_DIR" || { echo "❌ Impossible de revenir au répertoire initial"; exit 1; }

echo ""
echo "🎉 Tous les packages ont été réinstallés avec succès!"
echo "Les packages ont également été installés directement dans l'environnement Poetry du serveur"
echo "Vous pouvez maintenant démarrer le serveur avec 'cd server && poetry run python -m server'" 