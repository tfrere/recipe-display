# Recipe Importer

Outil d'importation de recettes pour recipe-display.

## Installation

```bash
poetry install
```

## Utilisation

### Import depuis URLs

```bash
poetry run recipe-importer url -f urls.json
```

Format du fichier `urls.json` :

```json
["https://www.site1.com/recipe1", "https://www.site2.com/recipe2"]
```

### Import depuis fichiers texte

```bash
poetry run recipe-importer text -d ./mes-recettes
```

Structure du dossier :

```
mes-recettes/
  ├── recette1.txt    # Contenu de la recette
  ├── recette1.jpg    # Image optionnelle (même nom que le .txt)
  ├── recette2.txt    # Contenu de la recette
  └── recette2.png    # Image optionnelle (même nom que le .txt)
```

### Options communes

- `-c/--concurrent N` : Nombre d'imports simultanés (défaut: 5)
- `-a/--api-url URL` : URL de l'API (défaut: http://localhost:3001)
- `--auth FILE` : Fichier de configuration auth (défaut: auth_presets.json)
- `--list-recipes` : Liste les recettes après import
- `--clear` : Nettoie les dossiers de sortie avant import
