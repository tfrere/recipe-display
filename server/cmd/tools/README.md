# Recipe Display Tools

Ce package contient des utilitaires pour gérer la base de données des recettes.

## Commandes disponibles

### Effacer la base de données

Supprime toutes les recettes et images de la base de données :

```bash
go run main.go clear
```

### Importer les recettes

Importe les recettes listées dans un fichier JSON contenant des URLs :

```bash
# Importer toutes les recettes depuis le fichier par défaut
go run main.go import

# Importer depuis un fichier spécifique (chemin relatif au PWD)
go run main.go import -file data/experiments/mon_fichier.json

# Importer seulement les 5 premières recettes
go run main.go import -limit 5

# Combiner les options
go run main.go import -file data/experiments/mon_fichier.json -limit 5
```

Le fichier JSON doit contenir un tableau d'URLs au format :
```json
[
  "http://recipes.tfrere.com/recipes/recipe-1",
  "http://recipes.tfrere.com/recipes/recipe-2"
]
```

## Ajouter une nouvelle commande

1. Créer une nouvelle fonction pour votre commande
2. Ajouter un nouveau flag dans la fonction `main()`
3. Ajouter votre commande dans le switch case
