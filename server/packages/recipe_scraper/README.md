# Recipe Scraper

Outil pour extraire, structurer et enrichir des recettes de cuisine à partir d'URLs ou de fichiers texte.

## Fonctionnalités

- Extraction de recettes depuis des sites web
- Structuration de recettes à partir de texte brut
- Enrichissement automatique avec des données nutritionnelles et saisonnières
- Génération de fichiers JSON standardisés

## Installation

```bash
# Installation du package
cd server/packages/recipe_scraper
poetry install
```

## Utilisation

### Extraction depuis une URL

```bash
recipe-scraper --mode url --url https://example.com/recipe --output-folder ./recipes
```

Avec authentification :

```bash
recipe-scraper --mode url --url https://example.com/recipe --credentials auth_presets.json --output-folder ./recipes
```

### Structuration depuis un fichier texte

```bash
recipe-scraper --mode text --input-file recipe.txt --output-folder ./recipes
```

### Enrichissement autonome de recettes existantes

Vous pouvez enrichir des recettes déjà structurées en JSON :

```bash
# Depuis le module principal
poetry run python -m recipe_scraper.recipe_enricher --recipes_dir ./recipes

# Ou directement depuis l'outil installé
recipe-enricher --recipes_dir ./recipes --output_dir ./enriched_recipes
```

L'enrichisseur ajoute automatiquement :

- Classification des régimes alimentaires (omnivore, végétarien, etc.)
- Données de saisonnalité des ingrédients
- Calcul des temps de préparation et de cuisson

## Options

```
Extraction de recettes :
--mode {url,text}        Mode d'extraction : 'url' ou 'text'
--url URL                URL à extraire (mode 'url')
--input-file FICHIER     Fichier texte à traiter (mode 'text')
--credentials FICHIER    Fichier JSON d'identifiants d'authentification
--output-folder DOSSIER  Dossier de destination (défaut: ./output)
--verbose, -v            Journalisation détaillée

Enrichissement :
--recipes_dir DIR        Répertoire contenant les recettes à enrichir
--output_dir DIR         Répertoire de sortie (optionnel)
--no-backup              Ne pas créer de sauvegarde des fichiers originaux
```

## Format d'authentification

```json
{
  "example.com": {
    "type": "cookie",
    "values": {
      "cookie_name": "cookie_value"
    },
    "description": "Authentification pour example.com"
  }
}
```

## Résultat

Le processus génère :

- Un fichier JSON structuré (`<slug>.recipe.json`)
- Une image de la recette (si disponible)
- Des métadonnées enrichies (régime, saison, temps de préparation)
