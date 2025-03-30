# Recipe Scraper

Utilitaire en ligne de commande pour extraire des recettes à partir d'URLs ou de fichiers texte, les structurer et les enregistrer au format JSON.

## Installation

```bash
cd server/packages/recipe_scraper
poetry install
```

## Utilisation

Le scraper peut être utilisé de deux façons :

### Mode URL

Pour extraire une recette à partir d'une URL :

```bash
recipe-scraper --mode url --url https://example.com/recipe --output-folder ./recipes
```

Si le site nécessite une authentification, vous pouvez fournir un fichier de paramètres d'authentification :

```bash
recipe-scraper --mode url --url https://example.com/recipe --credentials auth_presets.json --output-folder ./recipes
```

### Mode Texte

Pour structurer une recette à partir d'un fichier texte :

```bash
recipe-scraper --mode text --input-file recipe.txt --output-folder ./recipes
```

## Options

```
--mode {url,text}        Mode d'extraction : 'url' pour extraction web, 'text' pour traitement de fichiers texte
--url URL                URL à extraire (requis en mode 'url')
--input-file FICHIER     Fichier texte à traiter (requis en mode 'text')
--credentials FICHIER    Chemin vers un fichier JSON contenant les identifiants d'authentification
--output-folder DOSSIER  Dossier pour enregistrer les recettes extraites (par défaut: ./output)
--verbose, -v            Activer la journalisation détaillée
```

## Format des identifiants

Le fichier de paramètres d'authentification doit suivre le format suivant :

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

Le scraper créera un fichier JSON avec les données structurées de la recette et téléchargera une image (si disponible) dans le dossier de sortie spécifié. Le fichier JSON sera nommé en utilisant le slug de la recette : `<slug>.recipe.json`.
