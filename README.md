# Recipe Display

Une application web pour afficher et gérer des recettes de cuisine, avec support pour l'importation automatique depuis divers sites web.

## Fonctionnalités

- **Importation automatique** de recettes depuis divers sites web
- Support de l'authentification pour les sites protégés (ex: Ottolenghi)
- Gestion des notes de recettes
- Métadonnées complètes (portions, difficulté, temps, etc.)
- Gestion des images et conversion automatique en WebP
- Interface responsive et moderne

## Prérequis

- Go 1.21+
- Node.js 18+
- npm ou yarn

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/votre-username/recipe-display.git
cd recipe-display
```

2. Installez les dépendances du serveur :
```bash
cd server
go mod download
```

3. Installez les dépendances du client :
```bash
cd client
npm install
```

4. Configurez les variables d'environnement :
```bash
# Dans server/.env
OPENAI_API_KEY=votre-clé-api
```

## Lancement

1. Démarrez le serveur :
```bash
cd server
go run main.go
```

2. Démarrez le client :
```bash
cd client
npm start
```

L'application sera accessible sur `http://localhost:3000`

## Importation de Recettes

### Configuration des Credentials

Pour importer des recettes depuis des sites protégés, configurez vos credentials dans `server/data/auth_presets.json` :

```json
{
  "books.ottolenghi.co.uk": {
    "id": "ottolenghi",
    "domain": ".books.ottolenghi.co.uk",
    "type": "cookie",
    "values": {
      "SSESSdcfc4c6f51fcab09b2179daf0e4cc999": "votre-cookie-de-session"
    },
    "description": "Ottolenghi",
    "lastUsed": 0
  }
}
```

### Import Unitaire

Utilisez l'interface web pour importer une recette :
1. Ouvrez l'application dans votre navigateur
2. Cliquez sur "Ajouter une recette"
3. Collez l'URL de la recette
4. Cliquez sur "Importer"

### Import en Masse

1. Créez un fichier JSON contenant les URLs des recettes :
```json
[
  "https://ottolenghi.co.uk/recipes/recipe1",
  "https://ottolenghi.co.uk/recipes/recipe2"
]
```

2. Utilisez l'outil d'importation :
```bash
cd server/cmd/tools
go run recipe_importer.go -file path/to/your/urls.json -limit 10
```

Options disponibles :
- `-file` : Chemin vers votre fichier JSON d'URLs (obligatoire)
- `-limit` : Nombre maximum de recettes à importer (optionnel)

## Structure des Données

### Format des Recettes

Les recettes sont stockées au format JSON avec la structure suivante :

```json
{
  "metadata": {
    "title": "Nom de la recette",
    "description": "Description",
    "servings": 4,
    "difficulty": "easy|medium|hard",
    "totalTime": "1h30",
    "image": "image.webp",
    "imageUrl": "url-originale",
    "sourceUrl": "url-source",
    "diet": "vegetarian|vegan|normal",
    "season": "spring|summer|fall|winter",
    "recipeType": "main|dessert|appetizer",
    "quick": false,
    "notes": ["Note 1", "Note 2"],
    "nationality": "Italian",
    "author": "Chef",
    "bookTitle": "Livre"
  },
  "ingredientsList": [
    {
      "id": "section-1",
      "title": "Pour la sauce",
      "ingredients": [...]
    }
  ],
  "instructions": [
    {
      "id": "section-1",
      "title": "Préparation",
      "steps": [...]
    }
  ]
}
```

## Outils de Développement

### Nettoyage de la Base

Pour nettoyer la base de données des recettes :
```bash
cd server/cmd/tools
go run db_cleanup.go
```

### Liste des Recettes

Pour lister toutes les recettes :
```bash
cd server/cmd/tools
go run list_recipes.go
```

## Contribution

1. Fork le projet
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push sur la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.